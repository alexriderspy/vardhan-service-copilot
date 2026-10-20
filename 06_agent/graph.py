"""Chapter 6: wire the nodes into a LangGraph state machine.

The graph pauses at `human_approval` (LangGraph interrupt). Its state is saved
in a SQLite checkpoint, so the Streamlit UI can resume it minutes later.
"""

import sqlite3
from functools import lru_cache

import nodes
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from state import EmailState

from common.config import CHECKPOINT_DB


def build_graph(checkpointer):
    g = StateGraph(EmailState)
    for name in ["load_email", "classify", "lookup_order", "search_knowledge", "find_slots",
                 "escalate_complaint", "holding_reply", "draft_reply", "human_approval", "act"]:
        g.add_node(name, getattr(nodes, name))

    g.add_edge(START, "load_email")
    g.add_edge("load_email", "classify")
    g.add_conditional_edges("classify", nodes.route, list(set(nodes.ROUTES.values())))
    for gather in ["lookup_order", "search_knowledge", "find_slots", "holding_reply"]:
        g.add_edge(gather, "draft_reply")
    g.add_edge("escalate_complaint", "human_approval")   # complaints skip the AI draft
    g.add_edge("draft_reply", "human_approval")
    g.add_edge("human_approval", "act")
    g.add_edge("act", END)
    return g.compile(checkpointer=checkpointer)


@lru_cache
def get_graph():
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    return build_graph(SqliteSaver(conn))


def _config(email_id: str) -> dict:
    return {"configurable": {"thread_id": email_id}}


def process_email(email_id: str) -> dict:
    """Run the agent on one email until it pauses for a human. Returns the state."""
    graph = get_graph()
    graph.invoke({"email_id": email_id, "tool_calls": []}, _config(email_id))
    return graph.get_state(_config(email_id)).values


def resume(email_id: str, decision: dict) -> dict:
    """Continue after the human decided (approve/edit/reject)."""
    graph = get_graph()
    graph.invoke(Command(resume=decision), _config(email_id))
    return graph.get_state(_config(email_id)).values


def saved_state(email_id: str):
    """(values, waiting_for_human) for an email, or (None, False) if never processed."""
    snapshot = get_graph().get_state(_config(email_id))
    if not snapshot.values:
        return None, False
    return snapshot.values, "human_approval" in snapshot.next


def forget(email_id: str) -> None:
    """Throw away the saved run for an email (to process it again)."""
    get_graph().checkpointer.delete_thread(email_id)
