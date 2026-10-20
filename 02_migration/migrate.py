"""Chapter 2: migrate legacy.db + CSV exports into a clean database.

Steps:
  1. read the wide legacy `jobs` table and the shop CSV exports
  2. dedupe customers (same phone number = same person)
  3. clean dates, amounts, order numbers and free-text statuses
  4. load customers, pumps, orders, technicians, service_tickets
  5. create read-only views + the agent role (least privilege)
  6. print a data-quality report

Target: Postgres if DATABASE_URL is set, otherwise SQLite at artifacts/vardhan.db.

Run:  python 02_migration/migrate.py
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, insert

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from cleaning import (  # noqa: E402
    WARRANTY_MONTHS,
    add_months,
    clean_amount,
    clean_model,
    clean_name,
    clean_order_no,
    clean_phone,
    clean_status,
    parse_date,
    ticket_type_from_note,
)
from least_privilege import create_agent_role, create_views  # noqa: E402
from schema import customers, metadata, orders, pumps, service_tickets, technicians  # noqa: E402

from common.config import AGENT_DB_PASSWORD, DATABASE_URL, LEGACY_DB, LEGACY_EXPORTS, SQLITE_DB  # noqa: E402


def load_legacy() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with sqlite3.connect(LEGACY_DB) as con:
        jobs = pd.read_sql("SELECT * FROM jobs", con).fillna("")
    shop = pd.concat([pd.read_csv(p, dtype=str) for p in sorted(LEGACY_EXPORTS.glob("orders_*.csv"))]).fillna("")
    techs = pd.read_csv(LEGACY_EXPORTS / "technicians.csv", dtype=str)
    return jobs, shop, techs


def build_customers(jobs: pd.DataFrame, shop: pd.DataFrame) -> pd.DataFrame:
    """One row per real person. Key = 10-digit phone number."""
    people = pd.concat([
        pd.DataFrame({"phone": jobs.Phone.map(clean_phone), "name": jobs.CustName.map(clean_name),
                      "email": jobs.Email.str.strip().str.lower(), "city": jobs.City.map(clean_name)}),
        pd.DataFrame({"phone": shop.Mobile.map(clean_phone), "name": shop.Customer.map(clean_name),
                      "email": shop["E-mail"].str.strip().str.lower(), "city": ""}),
    ])
    # Prefer the longest name spelling ("Ramesh Patil" over "R. Patil") and any non-empty email/city.
    people["name_len"] = people.name.str.len()
    people = people.sort_values("name_len", ascending=False)
    merged = people.groupby("phone").agg(
        name=("name", "first"),
        email=("email", lambda s: next((e for e in s if e), "")),
        city=("city", lambda s: next((c for c in s if c), "")),
    ).reset_index()
    merged.insert(0, "customer_id", range(1, len(merged) + 1))
    return merged


def main() -> None:
    jobs, shop, techs = load_legacy()
    report = {"legacy job rows": len(jobs), "shop csv rows": len(shop)}

    cust = build_customers(jobs, shop)
    phone_to_id = dict(zip(cust.phone, cust.customer_id))
    report["raw customer rows"] = len(jobs) + len(shop)
    report["unique customers after dedupe"] = len(cust)

    # Pumps: one per serial number
    pump_rows, bad_dates = {}, 0
    for job in jobs.itertuples():
        installed = parse_date(job.InstallDate)
        if job.InstallDate and installed is None:
            bad_dates += 1
        model = clean_model(job.PumpModel)
        pump_rows[job.PumpSerial] = {
            "serial": job.PumpSerial, "model": model, "customer_id": phone_to_id[clean_phone(job.Phone)],
            "install_date": installed,
            "warranty_until": add_months(installed, WARRANTY_MONTHS[model]) if installed else None,
        }

    # Orders: legacy ORDER jobs + shop CSV. Same order number in both = one order (CSV wins, it's newer).
    order_rows = {}
    for job in jobs[jobs.JobType == "ORDER"].itertuples():
        oid = clean_order_no(job.OrderNo)
        order_rows[oid] = {
            "order_id": oid, "customer_id": phone_to_id[clean_phone(job.Phone)], "item": job.Item,
            "amount_inr": clean_amount(job.OrderAmt), "status": clean_status(job.OrderStatus),
            "status_note": job.OrderStatus.strip(),
            "order_date": parse_date(job.OrderDate), "expected_delivery": parse_date(job.ExpectedDelivery),
            "courier": job.Courier or None, "awb": job.AWB or None, "source": "legacy_db",
        }
    duplicates = 0
    for row in shop.itertuples(index=False):
        oid = clean_order_no(row[0])
        duplicates += oid in order_rows
        order_rows[oid] = {
            "order_id": oid, "customer_id": phone_to_id[clean_phone(row.Mobile)], "item": row.Item,
            "amount_inr": clean_amount(row[5]), "status": clean_status(row.Status),
            "status_note": row.Status.strip(),
            "order_date": parse_date(row[7]), "expected_delivery": parse_date(row[8]),
            "courier": row.Courier or None, "awb": row.AWB or None, "source": "shop_csv",
        }
    report["orders"] = len(order_rows)
    report["orders found in both legacy.db and CSV (merged)"] = duplicates

    # Service history becomes closed service tickets
    ticket_rows = []
    for job in jobs[jobs.JobType != "ORDER"].itertuples():
        when = parse_date(job.ServiceDate)
        ticket_rows.append({
            "customer_id": phone_to_id[clean_phone(job.Phone)], "pump_serial": job.PumpSerial,
            "created_at": datetime.combine(when, datetime.min.time()) if when else None,
            "ticket_type": ticket_type_from_note(job.JobType, job.ServiceNote), "priority": "normal",
            "status": "closed", "summary": job.ServiceNote, "technician": job.Technician, "source": "legacy",
        })

    tech_rows = [{"tech_id": t["Tech ID"], "name": t.Name, "skills": t.Skills, "phone": clean_phone(t.Phone)}
                 for _, t in techs.iterrows()]

    # --- Load into the target database ---
    if DATABASE_URL.startswith("sqlite") and SQLITE_DB.exists():
        SQLITE_DB.unlink()  # fresh start every run
    engine = create_engine(DATABASE_URL)
    is_postgres = engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        if is_postgres:
            for name in ["v_customers", "v_pumps", "v_orders", "v_service_history", "v_technicians"]:
                conn.exec_driver_sql(f"DROP VIEW IF EXISTS {name}")
        metadata.drop_all(conn)
        metadata.create_all(conn)
        conn.execute(insert(customers), cust.to_dict("records"))
        conn.execute(insert(pumps), list(pump_rows.values()))
        conn.execute(insert(orders), list(order_rows.values()))
        conn.execute(insert(technicians), tech_rows)
        conn.execute(insert(service_tickets), ticket_rows)
        create_views(conn)
        if is_postgres:
            create_agent_role(conn, AGENT_DB_PASSWORD)

    report["pumps"] = len(pump_rows)
    report["service tickets (history)"] = len(ticket_rows)
    report["unreadable install dates"] = bad_dates
    report["target"] = "Postgres" if is_postgres else f"SQLite fallback ({SQLITE_DB.name})"
    report["agent access"] = ("role copilot_agent: SELECT on v_* views, write service_tickets + agent_audit_log"
                              if is_postgres else "SQLite authorizer in common/db.py: same rules as the Postgres role")

    print("Migration report")
    for key, value in report.items():
        print(f"  {key:<48} {value}")


if __name__ == "__main__":
    main()
