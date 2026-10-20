"""End-to-end: run the LangGraph agent on mock emails, pause for a human, resume.

Uses copies of the database, inbox and calendar, so nothing real changes.
Needs the pipeline to have run once (make data migrate train rag). Skipped otherwise.
The booking test uses a FAKE chat model: it checks the plumbing, not the LLM's writing.
"""

import json
import shutil

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from common import config

pytestmark = pytest.mark.skipif(
    not (config.SQLITE_DB.exists() and (config.CLASSIFIER_MODEL / "config.json").exists() and config.CHROMA_DIR.exists()),
    reason="run the pipeline first: make data migrate train rag",
)


@pytest.fixture
def agent(tmp_path, monkeypatch):
    import calendar_server
    import gmail_server
    import graph
    import seed_mock_data

    import common.db as db

    # Throwaway copies of everything the agent can change
    shutil.copy(config.SQLITE_DB, tmp_path / "db.sqlite")
    monkeypatch.setattr(db, "AGENT_DATABASE_URL", f"sqlite:///{tmp_path / 'db.sqlite'}")
    db.agent_engine.cache_clear()
    for module, name in [(seed_mock_data, "MOCK_GMAIL"), (gmail_server, "MOCK_GMAIL")]:
        monkeypatch.setattr(module, name, tmp_path / "gmail.json")
    for module, name in [(seed_mock_data, "MOCK_CALENDAR"), (calendar_server, "MOCK_CALENDAR")]:
        monkeypatch.setattr(module, name, tmp_path / "calendar.json")
    monkeypatch.setattr(gmail_server, "_backend", gmail_server.MockGmail())
    monkeypatch.setattr(calendar_server, "_backend", calendar_server.MockCalendar())
    seed_mock_data.main()
    yield graph.build_graph(MemorySaver()), tmp_path
    db.agent_engine.cache_clear()


def run(app, email_id):
    cfg = {"configurable": {"thread_id": email_id}}
    app.invoke({"email_id": email_id, "tool_calls": []}, cfg)
    return cfg, app.get_state(cfg)


def test_complaint_is_escalated_never_auto_replied(agent):
    app, tmp = agent
    cfg, snap = run(app, "m021")
    assert snap.next == ("human_approval",)          # paused for a human
    assert snap.values["intent"] == "complaint"
    assert snap.values["draft"] == ""                # the AI wrote nothing
    assert snap.values["ticket_id"]
    assert "gmail.send_draft" not in snap.values["tool_calls"]

    app.invoke(Command(resume={"action": "approve", "body": "Sorry, our manager will call you.", "reviewer": "Asha"}), cfg)
    sent = json.loads((tmp / "gmail.json").read_text())["sent"]
    assert sent[-1]["approved_by"] == "Asha"


def test_booking_waits_for_approval_then_books(agent, monkeypatch):
    import nodes
    monkeypatch.setattr(nodes, "get_llm", lambda **_: FakeListChatModel(responses=["Here are two slots..."]))
    app, tmp = agent
    cfg, snap = run(app, "m006")
    assert snap.values["intent"] == "service_booking"
    assert len(snap.values["slots"]) == 2
    events_before = len(json.loads((tmp / "calendar.json").read_text())["events"])

    app.invoke(Command(resume={"action": "approve", "body": snap.values["draft"], "slot_index": 0, "reviewer": "Asha"}), cfg)
    result = app.get_state(cfg).values["result"]
    assert result["booked"] and result["sent"]
    assert len(json.loads((tmp / "calendar.json").read_text())["events"]) == events_before + 1


def test_rejected_draft_sends_nothing(agent, monkeypatch):
    import nodes
    monkeypatch.setattr(nodes, "get_llm", lambda **_: FakeListChatModel(responses=["Your order is on the way."]))
    app, tmp = agent
    cfg, _ = run(app, "m001")
    app.invoke(Command(resume={"action": "reject", "reviewer": "Asha"}), cfg)
    assert json.loads((tmp / "gmail.json").read_text())["sent"] == []
