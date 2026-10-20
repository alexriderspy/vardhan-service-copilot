"""Mock Gmail + Calendar behave like the real thing, and sending needs approval."""

import json
from datetime import datetime
from pathlib import Path

import calendar_server
import gmail_server
import pytest

SEED = Path(__file__).resolve().parent.parent / "05_mcp_servers" / "mock_seed" / "inbox.json"


@pytest.fixture
def mock_inbox(tmp_path, monkeypatch):
    path = tmp_path / "gmail.json"
    messages = [{**m, "unread": True} for m in json.loads(SEED.read_text())]
    path.write_text(json.dumps({"messages": messages, "drafts": [], "sent": []}))
    monkeypatch.setattr(gmail_server, "MOCK_GMAIL", path)
    monkeypatch.setattr(gmail_server, "_backend", gmail_server.MockGmail())
    return path


def test_inbox_has_30_emails_covering_all_intents(mock_inbox):
    assert len(gmail_server.list_unread()) == 30


def test_send_requires_human_approval(mock_inbox):
    draft = gmail_server.create_draft("m001", "Your order is on the way.")
    refused = gmail_server.send_draft(draft["draft_id"], approved_by="  ")
    assert refused["sent"] is False
    sent = gmail_server.send_draft(draft["draft_id"], approved_by="Asha")
    assert sent["sent"] is True
    assert "m001" not in [m["id"] for m in gmail_server.list_unread()]


def test_slots_skip_sundays_and_busy_times():
    slots = list(calendar_server.candidate_slots("2030-01-05", "2030-01-07"))  # Sat, Sun, Mon
    assert {s.weekday() for s, _ in slots} == {5, 0}
    a = (datetime(2030, 1, 7, 9), datetime(2030, 1, 7, 11))
    assert calendar_server.overlaps(*a, datetime(2030, 1, 7, 10), datetime(2030, 1, 7, 12))
    assert not calendar_server.overlaps(*a, datetime(2030, 1, 7, 11), datetime(2030, 1, 7, 13))


def test_seed_file_is_valid():
    emails = json.loads(SEED.read_text())
    assert len({e["id"] for e in emails}) == 30
