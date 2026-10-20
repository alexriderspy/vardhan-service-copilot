"""Chapter 3a: make ~2,000 labelled training emails without any API.

In a real project you'd label a few thousand of the client's past emails
(their support team already knows the right answers). Here we generate
realistic ones from templates: many phrasings per intent, random customers,
order numbers, pump models, greetings, typos and Indian-English touches.

Output: artifacts/classifier_data/{train,val,test}.jsonl  ({"text", "label"})

Run:  python 03_classifier/generate_emails.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.config import CLASSIFIER_DATA, INTENTS  # noqa: E402

random.seed(7)
EMAILS_PER_INTENT = 340

MODELS = ["VP-100", "VS-200", "VB-300", "VP100", "submersible pump", "booster pump", "centrifugal pump", "pump"]
PARTS = ["mechanical seal kit", "impeller", "pressure tank", "control panel", "capacitor", "pressure switch", "spare kit", "foot valve"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "tomorrow", "this week", "next week"]
PLACES = ["farm", "factory", "office", "flat", "bungalow", "hotel", "site", "society", "borewell"]
TIMES = ["2 days", "a week", "10 days", "3 weeks", "a month", "since yesterday", "since Monday"]

# Each intent: list of (subject, body) templates. Slots: {order} {model} {part} {day} {place} {time} {serial}
TEMPLATES = {
    "order_status": [
        ("Order status {order}", "Hi, can you tell me the status of my order {order}? I placed it {time} ago."),
        ("Where is my order?", "I ordered a {part} for my {model}, order no {order}. It still hasn't arrived. When will it be delivered?"),
        ("Delivery update", "Please share the tracking details for order {order}. Which courier is it with?"),
        ("{order} not received", "My order {order} shows dispatched but I have not received anything yet. Kindly check."),
        ("Expected delivery date?", "Hello team, what is the expected delivery date for the {part} I ordered? Order {order}."),
        ("Re: your order", "Has my order been shipped? It's been {time}. Order number is {order}."),
        ("tracking number", "pls send AWB / tracking number for {order}"),
        ("When will my pump arrive", "We bought a new {model} for our {place}, order {order}. When will it reach us? We need it before {day}."),
        ("Order dispatched?", "Is order {order} dispatched yet? Payment was done {time} ago."),
        ("Status of spare part order", "I need an update on the {part} order {order}. Our {place} is waiting for it."),
        ("Delay in delivery", "Order {order} was supposed to come by {day}. Any update on where it is right now?"),
        ("Order confirmation", "Did you receive my order for a {part}? I didn't get any confirmation. Ref {order}."),
        ("courier details", "Which courier has my parcel? Order {order}. The courier guy is not picking calls."),
        ("Is my order on hold?", "My order {order} says on hold. Why? What do I need to do to get it moving?"),
        ("Cancelled order?", "Is my order {order} cancelled? I see a message but I didn't cancel it. Please check the status."),
    ],
    "service_booking": [
        ("Book a service visit", "Hi, I would like to book a service visit for my {model} at our {place}. Is {day} possible?"),
        ("Technician visit needed", "Please send a technician to check our {model}. Any day {day} works for us."),
        ("Annual maintenance", "It's been a year since installation of our {model}. We want to schedule the annual maintenance visit."),
        ("Installation appointment", "We have bought a {model}. When can your team come for installation at our {place}?"),
        ("Schedule service", "Can you schedule a service for pump serial {serial}? Morning slots preferred, {day}."),
        ("Need servicing", "Our {model} needs servicing. Please let me know available slots {day}."),
        ("Book appointment", "I want an appointment with a technician for seal replacement on my {model}. What dates are free?"),
        ("Visit request", "Requesting a site visit at our {place} for pump inspection, {day} if possible."),
        ("Preventive maintenance", "We have Vardhan Care. Please book our free preventive maintenance visit for {serial}."),
        ("Reschedule visit", "The technician visit for our {model} needs to be moved to {day}. Please give new slots."),
        ("service call", "pls arrange service call for {model} at {place}. available {day} after 11am"),
        ("Pump shifting", "We are moving our {model} to a new borewell. Need a technician to come and reinstall it {day}."),
        ("Can someone come?", "Can someone come and have a look at the {model}? I'm free {day}."),
        ("Pressure switch calibration", "Please book a technician to recalibrate the pressure switch on our {model}, {day} if a slot is free."),
    ],
    "warranty_claim": [
        ("Warranty claim", "My {model} (serial {serial}) has stopped working. It's only {time} old. Is this covered under warranty?"),
        ("Is this under warranty?", "The motor of my {model} burnt out. Serial {serial}. I want to claim warranty."),
        ("Warranty replacement", "The {part} failed within the warranty period. Please replace it free of cost. Serial {serial}."),
        ("warranty?", "my pump {serial} is leaking from the seal. it is still in warranty right? pls confirm"),
        ("Claim for defective pump", "We received a defective {model}. The impeller is cracked. Requesting replacement under warranty."),
        ("Warranty status", "Can you check if pump serial {serial} is still under warranty? Installed around {time} back."),
        ("Free repair?", "Will the repair of my {model} be free? I think it's within 2 years of installation."),
        ("Warranty period", "What is the warranty period on my {model}, serial {serial}, and is it still valid?"),
        ("Motor failure - warranty", "Motor winding failed on {serial}. We always used a stabiliser. Please process a warranty claim."),
        ("Extended warranty", "My warranty for {serial} is ending soon. Can I buy the extended warranty, and what does it cover?"),
        ("Covered or not?", "The capacitor on my {model} blew. Is a capacitor covered under warranty or do I have to pay?"),
        ("Replacement under guarantee", "Pump {serial} stopped after {time}. Bill attached. Please replace under guarantee."),
        ("Claim rejected?", "Why would my warranty claim for {serial} not be covered? The pump is less than 18 months old."),
    ],
    "technical_question": [
        ("Pump making noise", "My {model} is making a rattling noise since {time}. What could be the reason?"),
        ("Low pressure", "Water pressure from the {model} has dropped. What should I check?"),
        ("Motor keeps tripping", "The motor of my {model} trips after running for some time. How do I fix this?"),
        ("Priming question", "How do I prime the {model}? It is not lifting water after we cleaned the tank."),
        ("Short cycling", "Our {model} keeps switching on and off every few seconds. Is something wrong?"),
        ("Specifications", "What is the maximum head and flow of the {model}? We need to pump to a {place} on the 4th floor."),
        ("Vibration issue", "There is a lot of vibration in the {model} at our {place}. Is this normal?"),
        ("Dry run", "Is it ok if the {model} runs without water for a few minutes? The tank emptied yesterday."),
        ("How often to service", "How often should the mechanical seal on the {model} be replaced?"),
        ("Voltage question", "We get low voltage at our {place}, around 190 V. Can the {model} handle this or do we need a stabiliser?"),
        ("Water leaking", "A little water is dripping near the shaft of the {model}. What does that mean?"),
        ("Pump not starting", "The {model} is not starting and the dry run light is on. What should I do?"),
        ("installation depth", "how deep should the {model} be installed in a 200 ft borewell?"),
        ("Sand in water", "We are getting sand in the water from the borewell. Will it damage the {model}?"),
        ("Humming sound", "The {model} hums but the shaft doesn't turn. Is it the capacitor?"),
    ],
    "complaint": [
        ("Very disappointed", "This is the third time the {model} has failed in {time}. Your service is pathetic. I want a refund."),
        ("Worst service", "Your technician never showed up on {day} even after confirming. Totally unprofessional. I am escalating this."),
        ("Complaint against technician", "The technician who came to our {place} was rude and left without fixing the {model}. Very unhappy."),
        ("Refund demand", "I am fed up. The {model} you sold me is defective and nobody responds. Refund my money immediately."),
        ("Still not resolved!!", "I have been calling for {time} and no one is helping. This is unacceptable. I will post a review everywhere."),
        ("Overcharged", "Your technician charged me Rs 2,500 for a visit that should be free under warranty. This is cheating. I want it returned."),
        ("Pathetic experience", "Ordered {order} and got a damaged {part}. Customer care keeps me on hold. Worst company."),
        ("Legal notice", "If my {model} issue is not fixed by {day}, I will go to the consumer court."),
        ("Escalation", "I want to speak to the manager. My complaint about {serial} has been ignored for {time}."),
        ("Unhappy with repair", "You repaired the {model} last month and it broke again. Poor quality work. I am not paying again."),
        ("No response", "Nobody has replied to my 4 emails. Is anyone even reading these? Disgusting service."),
        ("Damaged in delivery", "The {model} arrived with a broken casing and your team is refusing to take responsibility. Shameful."),
        ("Very angry customer", "Your company wasted my whole {day} waiting. Our {place} had no water all day. Compensate us."),
    ],
    "other": [
        ("Dealership enquiry", "We run a hardware shop in Satara. How can we become a Vardhan pumps dealer?"),
        ("Job application", "I am an ITI electrician with 3 years experience. Are you hiring technicians?"),
        ("Invoice copy", "Please send a GST invoice copy for our purchase last month. Company GSTIN attached."),
        ("Price list", "Can you share the latest price list for all your pumps?"),
        ("Thank you", "Thanks to your team for the quick help last week. Everything is working fine now."),
        ("Change of address", "Please update our billing address. We have shifted our {place} to Hadapsar."),
        ("Vendor registration", "We are a packaging supplier and would like to register as a vendor with Vardhan Pumps."),
        ("Office timings", "What are your office timings on Saturdays? Is the Pune showroom open?"),
        ("Bulk quote", "We need a quotation for 20 units of {model} for a housing society project."),
        ("Newsletter unsubscribe", "Please remove me from your marketing emails."),
        ("Partnership", "We are a solar company and would like to explore a partnership for solar pumps."),
        ("Catalogue request", "Can you email me a brochure/catalogue of your products?"),
        ("Payment confirmation", "We have made the NEFT payment for the quotation you sent. UTR attached for your records."),
        ("Internship", "I am a mechanical engineering student. Do you offer summer internships?"),
    ],
}

GREETINGS = ["Hi,", "Hello,", "Dear Sir/Madam,", "Hi team,", "Respected Sir,", "Good morning,", "", "", "Namaste,"]
SIGNOFFS = ["Thanks", "Regards", "Thank you", "Thanks & regards", "", "Waiting for your reply", "Pls do the needful"]
NAMES = ["Ramesh", "Sunita", "Anil", "Priya", "Mohammed", "Kavita", "Rajesh", "Deepa", "Sanjay", "Neha", "Vikram", "Farida"]


def random_order() -> str:
    number = random.randint(30000, 59999)
    return random.choice([f"ORD-{number}", f"#{number}", f"{number}", f"order no. {number}"])


def random_serial() -> str:
    return f"{random.choice(['VP100', 'VS200', 'VB300'])}-{random.randint(10000, 29999)}"


def add_noise(text: str) -> str:
    """Make it look like a real email typed on a phone."""
    if random.random() < 0.15:
        text = text.lower()
    if random.random() < 0.15:
        words = text.split()
        i = random.randrange(len(words))
        if len(words[i]) > 3:
            w = words[i]
            j = random.randrange(len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]  # swap two letters
        text = " ".join(words)
    if random.random() < 0.1:
        text = text.replace("please", "pls").replace("Please", "Pls")
    return text


def make_email(intent: str) -> str:
    subject, body = random.choice(TEMPLATES[intent])
    slots = {"order": random_order(), "model": random.choice(MODELS), "part": random.choice(PARTS),
             "day": random.choice(DAYS), "place": random.choice(PLACES), "time": random.choice(TIMES),
             "serial": random_serial()}
    subject, body = subject.format(**slots), body.format(**slots)
    parts = [random.choice(GREETINGS), add_noise(body), random.choice(SIGNOFFS), random.choice(NAMES)]
    return f"Subject: {subject}\n\n" + "\n".join(p for p in parts if p)


def main() -> None:
    rows = [{"text": make_email(intent), "label": intent} for intent in INTENTS for _ in range(EMAILS_PER_INTENT)]
    random.shuffle(rows)
    n = len(rows)
    splits = {"train": rows[: int(n * 0.8)], "val": rows[int(n * 0.8): int(n * 0.9)], "test": rows[int(n * 0.9):]}
    CLASSIFIER_DATA.mkdir(parents=True, exist_ok=True)
    for name, data in splits.items():
        with open(CLASSIFIER_DATA / f"{name}.jsonl", "w") as f:
            for row in data:
                f.write(json.dumps(row) + "\n")
        print(f"{name}: {len(data)} emails")
    print("\nExample:\n" + rows[0]["text"] + f"\n-> label: {rows[0]['label']}")


if __name__ == "__main__":
    main()
