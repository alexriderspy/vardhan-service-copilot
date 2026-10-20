"""Small, testable functions that turn messy legacy values into clean ones."""

import calendar
import re
from datetime import date, datetime

DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%B %d %Y", "%d-%m-%y"]


def parse_date(text: str | None) -> date | None:
    """Try every date format the clerks used. Returns None if empty or unreadable."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def clean_phone(text: str) -> str:
    """'+91-98220-11234' / '09822011234' -> '9822011234' (last 10 digits)."""
    digits = re.sub(r"\D", "", text or "")
    return digits[-10:]


def clean_name(text: str) -> str:
    """' ramesh patil ' -> 'Ramesh Patil'."""
    return " ".join(part.capitalize() for part in (text or "").split())


def clean_amount(text) -> float | None:
    """'Rs. 12,500' / 'INR 12500' / '12500.00' -> 12500.0"""
    cleaned = re.sub(r"[^\d.]", "", str(text or "")).strip(".")
    return float(cleaned) if cleaned else None


def clean_order_no(text: str) -> str | None:
    """'#50412' / 'ord50412' / '50412' -> 'ORD-50412'"""
    digits = re.sub(r"\D", "", text or "")
    return f"ORD-{digits}" if digits else None


def clean_model(text: str) -> str:
    """'vp100' / 'VP-100 ' -> 'VP-100'"""
    letters_digits = re.sub(r"[^A-Za-z0-9]", "", text or "").upper()
    return f"{letters_digits[:2]}-{letters_digits[2:]}"


def clean_status(text: str) -> str:
    """Map free-text status to one of our 6 statuses."""
    t = (text or "").strip().lower()
    if t.startswith("deliv") or t == "dlvd":
        return "delivered"
    if "transit" in t:
        return "in_transit"
    if t.startswith("dispatch"):
        return "dispatched"
    if t.startswith("cancel"):
        return "cancelled"
    if "hold" in t:
        return "on_hold"
    return "pending"


def ticket_type_from_note(job_type: str, note: str) -> str:
    if "install" in (job_type or "").lower() or (note or "").lower().startswith("install"):
        return "installation"
    if "maintenance" in (note or "").lower():
        return "maintenance"
    return "repair"


# Warranty months per pump model, from client_docs/warranty-policy.md
WARRANTY_MONTHS = {"VP-100": 24, "VS-200": 18, "VB-300": 24}


def add_months(d: date, months: int) -> date:
    """14 Feb 2025 + 24 months -> 14 Feb 2027. 31 Jan + 1 month -> 28/29 Feb (last day of month)."""
    month_index = d.month - 1 + months
    year, month = d.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))
