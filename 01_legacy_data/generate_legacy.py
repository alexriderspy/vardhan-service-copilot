"""Chapter 1: build the client's messy legacy system.

Creates (in artifacts/legacy/):
  legacy.db                 one wide `jobs` table, exported from their old MS Access app
  exports/orders_2025.csv   order exports from the web shop, different column names
  exports/orders_2026.csv
  exports/technicians.csv   the HR spreadsheet of field technicians

The mess is on purpose: mixed date formats, free-text status, duplicated
customers with different spellings, amounts stored as text. Chapter 2 cleans it.

The pump manuals and warranty policy are in 01_legacy_data/client_docs/.

Run:  python 01_legacy_data/generate_legacy.py
"""

import csv
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.config import CLIENT_DOCS, LEGACY_DB, LEGACY_EXPORTS  # noqa: E402

random.seed(42)

# --- The customers who appear in the demo inbox and the eval set. ---
# Their facts must stay fixed so the agent's answers can be checked.
HERO_CUSTOMERS = [
    # name, email, phone, city, model, serial, install date
    ("Ramesh Patil", "ramesh.patil@gmail.com", "9822011234", "Pune", "VP-100", "VP100-23117", date(2025, 2, 14)),
    ("Sunita Deshmukh", "sunita.deshmukh@yahoo.co.in", "9850123456", "Nashik", "VS-200", "VS200-22058", date(2024, 1, 10)),
    ("Anil Kulkarni", "anil.k@kulkarniagro.in", "9890456789", "Baramati", "VS-200", "VS200-25211", date(2026, 3, 5)),
    ("Priya Nair", "priya.nair@outlook.com", "9767001122", "Pune", "VB-300", "VB300-24390", date(2025, 11, 20)),
    ("Mohammed Shaikh", "m.shaikh@shaikhconstructions.com", "9823344556", "Pimpri", "VP-100", "VP100-21876", date(2023, 6, 1)),
    ("Kavita Joshi", "kavitajoshi78@gmail.com", "9922113344", "Pune", "VB-300", "VB300-25102", date(2026, 6, 18)),
    ("Rajesh Iyer", "rajesh.iyer@iyerhotels.com", "9819988776", "Lonavala", "VP-100", "VP100-24555", date(2024, 12, 2)),
    ("Deepa Gokhale", "deepa.gokhale@gmail.com", "9881234567", "Satara", "VS-200", "VS200-24777", date(2025, 8, 25)),
    ("Sanjay More", "sanjaymore.farm@gmail.com", "9970012345", "Ahmednagar", "VS-200", "VS200-23940", date(2024, 9, 12)),
    ("Neha Bhosale", "neha.bhosale@techpark.co.in", "9765432109", "Pune", "VB-300", "VB300-23011", date(2024, 5, 30)),
    ("Vikram Rao", "vikram.rao@raoindustries.com", "9890011223", "Chakan", "VP-100", "VP100-25330", date(2026, 1, 15)),
    ("Farida Khan", "farida.khan@gmail.com", "9921445566", "Pune", "VB-300", "VB300-25480", date(2026, 8, 2)),
]

# Orders for hero customers: order no, email, item, amount, status text, order date, expected, courier, awb
HERO_ORDERS = [
    ("50412", "ramesh.patil@gmail.com", "VP-100 mechanical seal kit", 1850, "Dispatched ", date(2026, 10, 15), date(2026, 10, 23), "BlueDart", "7731904412"),
    ("50433", "priya.nair@outlook.com", "VB-300 pressure tank 8L", 4200, "pending - awaiting stock", date(2026, 10, 12), date(2026, 10, 30), "", ""),
    ("50398", "m.shaikh@shaikhconstructions.com", "VP-100 pump (2 units)", 31800, "DELIVERD", date(2026, 9, 28), date(2026, 10, 10), "VRL Logistics", "VRL88231"),
    ("50427", "rajesh.iyer@iyerhotels.com", "VP-100 impeller", 2650, "in transit", date(2026, 10, 14), date(2026, 10, 22), "DTDC", "D40019873"),
    ("50441", "neha.bhosale@techpark.co.in", "VB-300 pressure switch", 1450, "Cancelled by cust", date(2026, 10, 5), None, "", ""),
    ("50450", "vikram.rao@raoindustries.com", "VS-200 control panel", 6900, "dispatched", date(2026, 10, 16), date(2026, 10, 24), "BlueDart", "7731905588"),
    ("50455", "anil.k@kulkarniagro.in", "Stainless steel safety rope 60m", 3100, "on hold - payment", date(2026, 10, 17), None, "", ""),
    ("50460", "kavitajoshi78@gmail.com", "VB-300 inlet strainer", 450, "Delivered", date(2026, 10, 2), date(2026, 10, 7), "India Post", "EP221045678IN"),
]

# Past service jobs for hero pumps: serial, date, note, technician
HERO_SERVICE = [
    ("VP100-23117", date(2025, 2, 14), "Installation done, foot valve fitted", "Suresh Pawar"),
    ("VP100-23117", date(2026, 4, 3), "Seal leak - mech seal replaced under warranty", "Suresh Pawar"),
    ("VS200-22058", date(2024, 1, 10), "Install in 180ft borewell", "Ganesh Jadhav"),
    ("VS200-22058", date(2025, 5, 22), "Low flow, water level dropped, pump lowered by 20ft", "Ganesh Jadhav"),
    ("VS200-25211", date(2026, 3, 5), "Installation, control panel set", "Ganesh Jadhav"),
    ("VB300-24390", date(2025, 11, 20), "Installed with bypass line", "Amit Shinde"),
    ("VP100-21876", date(2023, 6, 1), "Installation at site office", "Suresh Pawar"),
    ("VP100-21876", date(2024, 11, 18), "Motor rewinding - NOT covered, dry run damage", "Rahul Kale"),
    ("VS200-24777", date(2025, 8, 25), "Installation, 220ft borewell", "Ganesh Jadhav"),
    ("VS200-23940", date(2024, 9, 12), "Installation farm borewell", "Ganesh Jadhav"),
    ("VS200-23940", date(2026, 2, 2), "Sand in stages, cleaned. Sand content high - advised filter", "Ganesh Jadhav"),
    ("VB300-23011", date(2024, 5, 30), "Installation office pantry", "Amit Shinde"),
    ("VB300-25102", date(2026, 6, 18), "Installation", "Amit Shinde"),
    ("VP100-25330", date(2026, 1, 15), "Installation at factory", "Rahul Kale"),
    ("VB300-25480", date(2026, 8, 2), "Installation 3rd floor flat", "Amit Shinde"),
    ("VP100-24555", date(2024, 12, 2), "Installation hotel kitchen line", "Rahul Kale"),
]

TECHNICIANS = [
    ("T01", "Suresh Pawar", "centrifugal;booster", "9822000101"),
    ("T02", "Ganesh Jadhav", "submersible", "9822000102"),
    ("T03", "Amit Shinde", "booster;centrifugal", "9822000103"),
    ("T04", "Rahul Kale", "centrifugal;submersible", "9822000104"),
    ("T05", "Pooja Wagh", "submersible;booster", "9822000105"),
]

FIRST = ["Amit", "Sachin", "Meera", "Rohit", "Snehal", "Prakash", "Asha", "Nitin", "Swati", "Mahesh",
         "Pallavi", "Ajay", "Rupali", "Vinod", "Shubham", "Manisha", "Kiran", "Yogesh", "Sneha", "Tushar"]
LAST = ["Kale", "Pawar", "Jadhav", "Shinde", "Chavan", "Gaikwad", "Salunkhe", "Mane", "Thorat", "Kadam",
        "Deshpande", "Apte", "Bapat", "Sathe", "Ranade", "Mehta", "Shah", "Agarwal", "Reddy", "Menon"]
CITIES = ["Pune", "Pune", "Pune", "Pimpri", "Chakan", "Nashik", "Satara", "Baramati", "Ahmednagar", "Lonavala"]
MODELS = {"VP-100": "VP100", "VS-200": "VS200", "VB-300": "VB300"}
ITEMS = ["{m} pump", "{m} mechanical seal kit", "{m} impeller", "{m} capacitor", "{m} spare kit"]
STATUS_TEXT = ["Dispatched", "dispatched ", "DISPATCHED", "Delivered", "delivered", "DELIVERD", "dlvd",
               "in transit", "In-Transit", "pending", "Pending - awaiting stock", "cancelled", "on hold"]
COURIERS = ["BlueDart", "DTDC", "VRL Logistics", "India Post", "Delhivery"]


def messy_date(d: date | None) -> str:
    """Write a date the way different clerks did over 15 years."""
    if d is None:
        return ""
    style = random.choice(["dmy_slash", "iso", "d_mon_y", "long", "dmy_dash"])
    if style == "dmy_slash":
        return d.strftime("%d/%m/%Y")
    if style == "iso":
        return d.isoformat()
    if style == "d_mon_y":
        return d.strftime("%d-%b-%Y")
    if style == "long":
        return d.strftime("%B %d %Y")
    return d.strftime("%d-%m-%y")


def messy_name(name: str) -> str:
    """The same customer typed differently each time."""
    first, last = name.split(" ", 1)
    return random.choice([name, name.upper(), name.lower() + " ", f"{first[0]}. {last}", f" {name}"])


def messy_phone(phone: str) -> str:
    return random.choice([phone, f"+91 {phone}", f"+91-{phone[:5]}-{phone[5:]}", f"0{phone}"])


def messy_amount(amount: int) -> str:
    return random.choice([str(amount), f"Rs. {amount:,}", f"{amount}.00", f"INR {amount}"])


def messy_order_no(number: str) -> str:
    return random.choice([number, f"ORD-{number}", f"ord{number}", f"#{number}"])


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def build_filler_customers(n: int) -> list[tuple]:
    """Random customers so the database looks like 15 years of business."""
    customers, used = [], set()
    serial_no = 10000
    while len(customers) < n:
        name = f"{random.choice(FIRST)} {random.choice(LAST)}"
        if name in used:
            continue
        used.add(name)
        model = random.choice(list(MODELS))
        serial_no += random.randint(7, 90)
        email = f"{name.lower().replace(' ', '.')}{random.randint(1, 99)}@gmail.com" if random.random() > 0.2 else ""
        phone = f"9{random.randint(100000000, 999999999)}"
        customers.append((name, email, phone, random.choice(CITIES), model,
                          f"{MODELS[model]}-{serial_no}", random_date(date(2011, 1, 1), date(2026, 9, 1))))
    return customers


def main() -> None:
    LEGACY_EXPORTS.mkdir(parents=True, exist_ok=True)
    if LEGACY_DB.exists():
        LEGACY_DB.unlink()

    con = sqlite3.connect(LEGACY_DB)
    # One wide table, everything as TEXT, like an MS Access export.
    con.execute("""
        CREATE TABLE jobs (
            JobID INTEGER PRIMARY KEY, JobType TEXT, CustName TEXT, Phone TEXT, Email TEXT, City TEXT,
            PumpModel TEXT, PumpSerial TEXT, InstallDate TEXT,
            OrderNo TEXT, OrderDate TEXT, OrderAmt TEXT, OrderStatus TEXT, ExpectedDelivery TEXT,
            Courier TEXT, AWB TEXT, Item TEXT,
            ServiceDate TEXT, ServiceNote TEXT, Technician TEXT
        )""")

    all_customers = HERO_CUSTOMERS + build_filler_customers(150)
    by_email = {c[1]: c for c in HERO_CUSTOMERS}
    rows = []

    def add_row(cust, **fields):
        name, email, phone, city, model, serial, installed = cust
        row = {
            "JobType": fields.get("JobType"), "CustName": messy_name(name), "Phone": messy_phone(phone),
            "Email": email if random.random() > 0.1 or cust in HERO_CUSTOMERS else "",
            "City": random.choice([city, city.upper(), city + " "]),
            "PumpModel": random.choice([model, model.replace("-", ""), model.lower()]),
            "PumpSerial": serial, "InstallDate": messy_date(installed),
        }
        row.update(fields)
        rows.append(row)

    # 1. Installation job for every customer
    for cust in all_customers:
        add_row(cust, JobType=random.choice(["Install", "INSTALLATION", "install"]),
                ServiceDate=messy_date(cust[6]), ServiceNote="Installation",
                Technician=random.choice(TECHNICIANS)[1])

    # 2. Random service jobs and old orders for filler customers
    order_no = 30000
    techs = [t[1] for t in TECHNICIANS]
    for cust in all_customers[len(HERO_CUSTOMERS):]:
        for _ in range(random.randint(0, 3)):
            when = random_date(cust[6], date(2026, 10, 1))
            add_row(cust, JobType="Service", ServiceDate=messy_date(when), Technician=random.choice(techs),
                    ServiceNote=random.choice(["Seal replaced", "Low pressure, strainer cleaned", "Capacitor changed",
                                               "Noise - bolts tightened", "Annual maintenance", "Motor rewinding"]))
        for _ in range(random.randint(0, 2)):
            order_no += random.randint(3, 40)
            when = random_date(date(2015, 1, 1), date(2025, 12, 31))
            add_row(cust, JobType="ORDER", OrderNo=messy_order_no(str(order_no)), OrderDate=messy_date(when),
                    OrderAmt=messy_amount(random.randint(4, 300) * 50), OrderStatus=random.choice(STATUS_TEXT[:7]),
                    Item=random.choice(ITEMS).format(m=cust[4]), Courier=random.choice(COURIERS),
                    ExpectedDelivery=messy_date(when + timedelta(days=6)), AWB=str(random.randint(10**8, 10**9)))

    # 3. Hero service history and hero orders (the facts the demo relies on)
    serial_to_cust = {c[5]: c for c in HERO_CUSTOMERS}
    for serial, when, note, tech in HERO_SERVICE:
        if note.startswith("Install"):
            continue  # already added in step 1
        add_row(serial_to_cust[serial], JobType="Service", ServiceDate=messy_date(when), ServiceNote=note, Technician=tech)
    for number, email, item, amount, status, ordered, expected, courier, awb in HERO_ORDERS[:5]:
        add_row(by_email[email], JobType="ORDER", OrderNo=messy_order_no(number), OrderDate=messy_date(ordered),
                OrderAmt=messy_amount(amount), OrderStatus=status, ExpectedDelivery=messy_date(expected),
                Courier=courier, AWB=awb, Item=item)

    random.shuffle(rows)
    cols = ["JobType", "CustName", "Phone", "Email", "City", "PumpModel", "PumpSerial", "InstallDate", "OrderNo",
            "OrderDate", "OrderAmt", "OrderStatus", "ExpectedDelivery", "Courier", "AWB", "Item",
            "ServiceDate", "ServiceNote", "Technician"]
    con.executemany(f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    [[r.get(c, "") for c in cols] for r in rows])
    con.commit()
    con.close()

    # 4. Web-shop CSV exports: different headers, DD/MM/YYYY dates, some orders duplicated from legacy.db
    header = ["Order Number", "Customer", "Mobile", "E-mail", "Item", "Amount (INR)", "Status", "Order Dt", "Exp. Delivery", "Courier", "AWB"]
    shop_orders_2025, shop_orders_2026 = [], []
    for cust in random.sample(all_customers[len(HERO_CUSTOMERS):], 60):
        order_no += random.randint(3, 40)
        when = random_date(date(2025, 1, 1), date(2026, 10, 10))
        row = [f"ORD-{order_no}", cust[0], cust[2], cust[1], random.choice(ITEMS).format(m=cust[4]),
               random.randint(4, 300) * 50, random.choice(["Delivered", "Dispatched", "Pending"]),
               when.strftime("%d/%m/%Y"), (when + timedelta(days=6)).strftime("%d/%m/%Y"),
               random.choice(COURIERS), str(random.randint(10**8, 10**9))]
        (shop_orders_2025 if when.year == 2025 else shop_orders_2026).append(row)
    # Hero orders: the last 3 exist only in the CSV; two others are duplicated in both places.
    for number, email, item, amount, status, ordered, expected, courier, awb in HERO_ORDERS[3:]:
        cust = by_email[email]
        shop_orders_2026.append([f"ORD-{number}", cust[0], cust[2], email, item, amount, status,
                                 ordered.strftime("%d/%m/%Y"), expected.strftime("%d/%m/%Y") if expected else "",
                                 courier, awb])
    for name, data in [("orders_2025.csv", shop_orders_2025), ("orders_2026.csv", shop_orders_2026)]:
        with open(LEGACY_EXPORTS / name, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)

    with open(LEGACY_EXPORTS / "technicians.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Tech ID", "Name", "Skills", "Phone"])
        writer.writerows(TECHNICIANS)

    print(f"legacy.db: {len(rows)} rows in one wide `jobs` table -> {LEGACY_DB}")
    print(f"CSV exports: {len(shop_orders_2025)} + {len(shop_orders_2026)} shop orders, {len(TECHNICIANS)} technicians -> {LEGACY_EXPORTS}")
    print(f"Client docs (manuals + warranty): {', '.join(p.name for p in sorted(CLIENT_DOCS.glob('*.md')))}")


if __name__ == "__main__":
    main()
