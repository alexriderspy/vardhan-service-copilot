"""Chapter 7: the support team's screen.

Inbox: run the agent on an email, see intent + confidence, tools and sources used,
the draft, and Approve / Edit / Reject. Audit log: everything the agent and humans did.

Run:  streamlit run 07_app/app.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "06_agent")]

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from sqlalchemy import text  # noqa: E402

from common.config import GOOGLE_MODE, LLM_MODEL, LLM_PROVIDER, use_chapter  # noqa: E402
from common.db import admin_engine  # noqa: E402
from common.llm import LLMNotConfigured, llm_is_configured  # noqa: E402

use_chapter("05_mcp_servers")
from graph import forget, process_email, resume, saved_state  # noqa: E402
from mcp_client import call_tool  # noqa: E402

st.set_page_config(page_title="Vardhan Service Copilot", layout="wide")

INTENT_LABELS = {"order_status": "Order status", "service_booking": "Service booking", "warranty_claim": "Warranty claim",
                 "technical_question": "Technical question", "complaint": "Complaint", "other": "Other"}

# ---------------- sidebar ----------------
st.sidebar.title("Vardhan Service Copilot")
page = st.sidebar.radio("Page", ["Inbox", "Audit log"])
reviewer = st.sidebar.text_input("Your name (reviewer)", value="Asha")
st.sidebar.caption(f"Gmail/Calendar: **{GOOGLE_MODE}** mode")
st.sidebar.caption(f"LLM: **{LLM_PROVIDER}:{LLM_MODEL}**" + ("" if llm_is_configured() else " (no key set: drafts disabled)"))
if GOOGLE_MODE == "mock" and st.sidebar.button("Reset demo inbox"):
    import seed_mock_data
    seed_mock_data.main()
    for m in call_tool("gmail", "list_unread", {}):
        forget(m["id"])
    st.rerun()


def show_audit_log() -> None:
    st.header("Audit log")
    with admin_engine().connect() as conn:
        df = pd.read_sql(text("SELECT ts, email_id, actor, action, intent, confidence, detail FROM agent_audit_log "
                              "ORDER BY log_id DESC LIMIT 500"), conn)
    st.dataframe(df, use_container_width=True, hide_index=True)


def show_email(email_id: str) -> None:
    email = call_tool("gmail", "get_email", {"email_id": email_id})
    st.subheader(email["subject"])
    st.caption(f"From {email.get('from_name', '')} <{email['from_email']}> · {email.get('received_at', '')}")
    st.text(email["body"])
    st.divider()

    values, waiting = saved_state(email_id)
    if values is None or not values.get("intent"):
        if st.button("Run agent", type="primary"):
            try:
                process_email(email_id)
            except LLMNotConfigured as err:
                st.session_state[f"err_{email_id}"] = str(err)
            st.rerun()
        return

    # What the agent found
    c1, c2 = st.columns(2)
    c1.metric("Intent", INTENT_LABELS[values["intent"]], f"{values['confidence']:.0%} confidence", delta_color="off")
    if values.get("intent_source", "model") != "model":
        c1.caption(f"Overridden by {values['intent_source']}")
    c2.markdown("**Tools called**\n\n" + "\n".join(f"- `{t}`" for t in values.get("tool_calls", [])))
    if values.get("needs_human"):
        st.warning(values["needs_human"])
    if values.get("sources"):
        with st.expander(f"Sources used ({len(values['sources'])})"):
            for s in values["sources"]:
                st.markdown(f"**{s['citation']}** · score {s['score']}")
                st.caption(s["text"])
    if values.get("facts"):
        with st.expander("Facts from company-db"):
            st.json(values["facts"])

    if values.get("result"):
        st.success(f"Done: {json.dumps(values['result'])}")
        return
    if not waiting:
        err = st.session_state.get(f"err_{email_id}", "")
        st.error("The agent stopped at the draft step (it needs an LLM).\n\n" + err)
        if st.button("Try again"):
            st.session_state.pop(f"err_{email_id}", None)
            forget(email_id)
            st.rerun()
        return

    # Human approval
    st.markdown("### Your decision")
    slot_index = None
    if values.get("slots"):
        options = [f"{s['start'].replace('T', ' ')} with {s['technician']}" for s in values["slots"]]
        choice = st.radio("Book this slot on approval", options + ["Don't book yet"])
        slot_index = None if choice == "Don't book yet" else options.index(choice)
    is_complaint = values["intent"] == "complaint"
    body = st.text_area(
        "Reply (edit freely)" if not is_complaint else "Complaints are never answered by the AI. Write your reply:",
        value=values.get("draft", ""), height=260, key=f"body_{email_id}",
    )
    a, r = st.columns(2)
    if a.button("Approve & send" if body.strip() else "Approve (no email)", type="primary"):
        resume(email_id, {"action": "approve", "body": body, "slot_index": slot_index, "reviewer": reviewer})
        st.rerun()
    if r.button("Reject"):
        resume(email_id, {"action": "reject", "reviewer": reviewer})
        st.rerun()


if page == "Audit log":
    show_audit_log()
else:
    st.header("Inbox")
    unread = call_tool("gmail", "list_unread", {})
    if not unread:
        st.info("Inbox zero. Use 'Reset demo inbox' in the sidebar to start over.")
    else:
        left, right = st.columns([1, 2])
        with left:
            labels = {}
            for m in unread:
                values, waiting = saved_state(m["id"])
                tag = f"[{INTENT_LABELS[values['intent']]}] " if values and values.get("intent") else ""
                labels[m["id"]] = f"{tag}{m['subject']} · {m.get('from_name') or m['from_email']}"
            selected = st.radio("Unread emails", list(labels), format_func=labels.get, label_visibility="collapsed")
        with right:
            show_email(selected)
