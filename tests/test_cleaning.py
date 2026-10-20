from datetime import date

from cleaning import add_months, clean_amount, clean_model, clean_name, clean_order_no, clean_phone, clean_status, parse_date


def test_parse_every_legacy_date_format():
    expected = date(2025, 2, 14)
    for text in ["14/02/2025", "2025-02-14", "14-Feb-2025", "February 14 2025", "14-02-25"]:
        assert parse_date(text) == expected
    assert parse_date("") is None
    assert parse_date("not a date") is None


def test_clean_identifiers():
    assert clean_phone("+91-98220-11234") == clean_phone("09822011234") == "9822011234"
    assert clean_name(" ramesh patil ") == "Ramesh Patil"
    assert clean_amount("Rs. 12,500") == clean_amount("INR 12500") == clean_amount("12500.00") == 12500.0
    assert clean_order_no("#50412") == clean_order_no("ord50412") == "ORD-50412"
    assert clean_model("vp100") == clean_model("VP-100") == "VP-100"


def test_free_text_status():
    assert clean_status("DELIVERD") == "delivered"
    assert clean_status("Dispatched ") == "dispatched"
    assert clean_status("In-Transit") == "in_transit"
    assert clean_status("on hold - payment") == "on_hold"
    assert clean_status("Cancelled by cust") == "cancelled"
    assert clean_status("pending - awaiting stock") == "pending"


def test_add_months_keeps_the_day():
    assert add_months(date(2024, 5, 30), 24) == date(2026, 5, 30)   # this was a real bug once
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
