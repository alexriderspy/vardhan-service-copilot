"""The steps (nodes) of the agent. Each takes the state and returns what it changed.

load_email -> classify -> route -> one of:
    lookup_order        order_status
    search_knowledge    technical_question, warranty_claim
    find_slots          service_booking
    escalate_complaint  complaint   (ticket, no AI reply)
    holding_reply       other
-> draft_reply (LLM) -> human_approval (pause) -> act -> END
"""

import json
import re
from datetime import date, timedelta

from langgraph.types import interrupt

from common.audit import write_audit
from common.config import use_chapter
from common.llm import get_llm

use_chapter("03_classifier")
use_chapter("04_rag")
use_chapter("05_mcp_servers")
from intent_classifier import get_classifier  # noqa: E402
from mcp_client import call_tool  # noqa: E402
from prompts import SYSTEM, TASK_BY_INTENT, USER  # noqa: E402
from retriever import search  # noqa: E402

ORDER_NO = re.compile(r"\b(\d{5})\b")
SERIAL = re.compile(r"\b(V[PSB]\d{3}-\d{5})\b", re.IGNORECASE)
LOW_CONFIDENCE = 0.80   # below this, the UI warns the reviewer to double-check the intent
SKILL_BY_MODEL = {"VP-100": "centrifugal", "VS-200": "submersible", "VB-300": "booster"}

# Which branch handles which intent.
ROUTES = {
    "order_status": "lookup_order",
    "technical_question": "search_knowledge",
    "warranty_claim": "search_knowledge",
    "service_booking": "find_slots",
    "complaint": "escalate_complaint",
    "other": "holding_reply",
}


def email_text(email: dict) -> str:
    return f"Subject: {email['subject']}\n\n{email['body']}"


# ---------------- 1. read + classify ----------------
def load_email(state):
    email = call_tool("gmail", "get_email", {"email_id": state["email_id"]})
    return {"email": email, "tool_calls": ["gmail.get_email"]}


# Safety net on top of the model: angry words always go to a human, whatever the model says.
ESCALATION_WORDS = ["consumer court", "consumer forum", "refund", "unacceptable", "worst", "pathetic",
                    "escalate", "very poor", "cheat", "legal notice"]


def classify(state):
    text = email_text(state["email"])
    intent, confidence = get_classifier().predict(text)
    intent_source = "model"
    rule_hit = next((w for w in ESCALATION_WORDS if w in text.lower()), None)
    if rule_hit and intent != "complaint":
        intent_source = f"rule: '{rule_hit}' (model said {intent})"
        intent = "complaint"
    write_audit(state["email_id"], "classified", intent=intent, confidence=round(confidence, 3),
                detail={"intent_source": intent_source})
    return {"intent": intent, "confidence": confidence, "intent_source": intent_source}


def route(state) -> str:
    """Pick the next node from the intent. Plain Python, no LLM."""
    return ROUTES[state["intent"]]


# ---------------- 2. gather facts (tools + RAG) ----------------
def lookup_order(state):
    email = state["email"]
    numbers = ORDER_NO.findall(email_text(email))
    if numbers:
        result = call_tool("company-db", "get_order_status", {"order_id": numbers[0]})
    else:  # no order number in the email: look up the sender's recent orders
        result = call_tool("company-db", "get_order_status", {"customer_email": email["from_email"]})
    return {"facts": {"orders": result.get("orders", [])}, "sources": [], "slots": [],
            "tool_calls": ["company-db.get_order_status"]}


def search_knowledge(state):
    email, intent = state["email"], state["intent"]
    calls, facts = [], {}
    serials = SERIAL.findall(email_text(email))
    args = {"serial": serials[0].upper()} if serials else {"customer_email": email["from_email"]}
    pumps = call_tool("company-db", "get_pump_history", args)
    calls.append("company-db.get_pump_history")
    facts["pumps"] = pumps.get("pumps", [])
    facts["today"] = date.today().isoformat()

    # Search only the manuals for pumps this email is about (+ the warranty policy):
    # models named in the email, else the customer's own pumps.
    models = sorted(models_mentioned(email_text(email)) or {p["model"] for p in facts["pumps"]})
    files = [f"{m.lower()}-manual.md" for m in models] + ["warranty-policy.md"] if models else None
    query = f"{' '.join(models)} {email['subject']} {email['body']}"
    hits = search(query, k=3, files=files)
    if intent == "warranty_claim":
        hits += search(f"warranty policy coverage {email['body']}", k=2, files=["warranty-policy.md"])
    calls.append("rag.search_manuals")
    unique = {h["citation"]: h for h in hits}  # drop duplicate chunks
    return {"facts": facts, "sources": list(unique.values()), "slots": [], "tool_calls": calls}


MODEL_WORDS = {"VP-100": ["vp-100", "vp100", "centrifugal"], "VS-200": ["vs-200", "vs200", "submersible", "borewell"],
               "VB-300": ["vb-300", "vb300", "booster"]}


def models_mentioned(text: str) -> set[str]:
    text = text.lower()
    return {model for model, words in MODEL_WORDS.items() if any(w in text for w in words)}


def guess_skill(email: dict, pumps: list[dict]) -> str:
    """Which technician skill this visit needs: from the pump named in the email, else the customer's pump."""
    mentioned = sorted(models_mentioned(email_text(email)))
    if mentioned:
        return SKILL_BY_MODEL[mentioned[0]]
    if pumps:
        return SKILL_BY_MODEL.get(pumps[0]["model"], "centrifugal")
    return "centrifugal"


def find_slots(state):
    email = state["email"]
    customer = call_tool("company-db", "get_customer", {"email": email["from_email"]})
    pumps = customer.get("pumps", []) if customer.get("found") else []
    skill = guess_skill(email, pumps)
    tomorrow = date.today() + timedelta(days=1)
    slots = call_tool("calendar", "find_free_slots", {
        "technician_skill": skill, "start_date": tomorrow.isoformat(),
        "end_date": (tomorrow + timedelta(days=7)).isoformat(), "max_slots": 2,
    })
    return {"facts": {"customer": customer, "skill_needed": skill}, "slots": slots, "sources": [],
            "tool_calls": ["company-db.get_customer", "calendar.find_free_slots"]}


def escalate_complaint(state):
    """Complaints: open a high-priority ticket and hand over to a human. The AI never replies."""
    email = state["email"]
    ticket = call_tool("company-db", "create_service_ticket", {
        "customer_email": email["from_email"], "ticket_type": "complaint", "priority": "high",
        "summary": f"Complaint by email: {email['subject']} - {email['body'][:300]}",
    })
    write_audit(state["email_id"], "escalated", intent="complaint", detail={"ticket_id": ticket["ticket_id"]})
    return {"facts": {}, "sources": [], "slots": [], "ticket_id": ticket["ticket_id"], "draft": "",
            "needs_human": f"Complaint: ticket #{ticket['ticket_id']} opened with HIGH priority. A human must write the reply.",
            "tool_calls": ["company-db.create_service_ticket"]}


def holding_reply(state):
    return {"facts": {}, "sources": [], "slots": []}


# ---------------- 3. draft (the only LLM step) ----------------
def draft_reply(state):
    email, intent = state["email"], state["intent"]
    slots_text = "\n".join(f"- {s['start'].replace('T', ' ')} to {s['end'][-5:]} with {s['technician']}"
                           for s in state.get("slots", [])) or "(none)"
    sources_text = "\n\n".join(f"{s['citation']}\n{s['text']}" for s in state.get("sources", [])) or "(none)"
    messages = [
        ("system", SYSTEM),
        ("user", USER.format(sender=email.get("from_name") or email["from_email"], subject=email["subject"],
                             body=email["body"], intent=intent, task=TASK_BY_INTENT[intent],
                             facts=json.dumps(state.get("facts", {}), indent=2, default=str),
                             slots=slots_text, sources=sources_text)),
    ]
    reply = get_llm().invoke(messages)  # raises LLMNotConfigured with a clear message if no key
    usage = reply.usage_metadata or {}
    write_audit(state["email_id"], "drafted", intent=intent,
                detail={"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")})
    needs_human = "Sending an email needs approval."
    if state["confidence"] < LOW_CONFIDENCE:
        needs_human += f" Low classifier confidence ({state['confidence']:.0%}): check the intent first."
    return {"draft": reply.text.strip(), "needs_human": needs_human,
            "llm_usage": {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}}


# ---------------- 4. human in the loop ----------------
def human_approval(state):
    """Pause the graph. The UI shows the draft and resumes with the human's decision:
    {"action": "approve" | "reject", "body": "...", "slot_index": 0, "reviewer": "Asha"}"""
    decision = interrupt({
        "intent": state["intent"], "confidence": state["confidence"], "draft": state.get("draft", ""),
        "slots": state.get("slots", []), "needs_human": state.get("needs_human", ""),
    })
    return {"decision": decision}


def act(state):
    """Do what the human approved: send the email, book the visit. Then log it."""
    decision, email = state["decision"], state["email"]
    reviewer = decision.get("reviewer") or "support-team"
    result, calls = {"sent": False, "booked": False}, []

    if decision["action"] != "approve":
        write_audit(state["email_id"], "rejected", actor="human", intent=state["intent"], detail={"reviewer": reviewer})
        return {"result": result}

    body = (decision.get("body") or "").strip()
    edited = body != state.get("draft", "").strip()
    if body:
        draft = call_tool("gmail", "create_draft", {"email_id": state["email_id"], "body": body})
        sent = call_tool("gmail", "send_draft", {"draft_id": draft["draft_id"], "approved_by": reviewer})
        result["sent"] = bool(sent.get("sent"))
        calls += ["gmail.create_draft", "gmail.send_draft"]

    slot_index = decision.get("slot_index")
    if state["intent"] == "service_booking" and slot_index is not None and state.get("slots"):
        slot = state["slots"][slot_index]
        event = call_tool("calendar", "create_event", {
            "tech_id": slot["tech_id"], "start": slot["start"], "end": slot["end"],
            "title": f"Service visit - {email.get('from_name') or email['from_email']}",
            "description": email["body"][:500],
        })
        ticket = call_tool("company-db", "create_service_ticket", {
            "customer_email": email["from_email"], "ticket_type": "visit", "priority": "normal",
            "summary": f"Visit booked {slot['start']} - {email['subject']}", "technician": slot["technician"],
        })
        result.update(booked=True, event_id=event["event_id"], visit_ticket_id=ticket["ticket_id"], slot=slot)
        calls += ["calendar.create_event", "company-db.create_service_ticket"]

    write_audit(state["email_id"], "approved_edited" if edited else "approved", actor="human",
                intent=state["intent"], detail={"reviewer": reviewer, **result})
    return {"result": result, "tool_calls": calls}
