"""Write one row to agent_audit_log. Every step the agent or a human takes is recorded."""

import json
from datetime import datetime

from sqlalchemy import text

from common.db import agent_engine


def write_audit(email_id: str, action: str, actor: str = "agent", intent: str | None = None,
                confidence: float | None = None, detail: dict | None = None) -> None:
    with agent_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO agent_audit_log (ts, email_id, intent, confidence, action, actor, detail)
            VALUES (:ts, :email_id, :intent, :confidence, :action, :actor, :detail)"""), {
            "ts": datetime.now(), "email_id": email_id, "intent": intent, "confidence": confidence,
            "action": action, "actor": actor, "detail": json.dumps(detail or {}, default=str),
        })
