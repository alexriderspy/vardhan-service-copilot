"""MCP server: gmail.

Tools: list_unread, get_email, create_draft, send_draft.
GOOGLE_MODE=mock (default): a local JSON inbox in artifacts/mock_gmail.json.
GOOGLE_MODE=real: your real Gmail via the Gmail API (needs credentials.json + google_login.py).

send_draft needs `approved_by` (the human who clicked Approve). The agent graph only
reaches the send step after a human approves in the UI.

Run standalone (stdio):  python 05_mcp_servers/gmail_server.py
"""

import base64
import json
import sys
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import MCPServer  # noqa: E402

from common.config import GOOGLE_MODE, MOCK_GMAIL  # noqa: E402

mcp = MCPServer("gmail", log_level="WARNING")


# ---------------- mock backend: a JSON file ----------------
class MockGmail:
    def _load(self) -> dict:
        if not MOCK_GMAIL.exists():
            raise FileNotFoundError("Mock inbox not found. Run: python 05_mcp_servers/seed_mock_data.py")
        return json.loads(MOCK_GMAIL.read_text())

    def _save(self, data: dict) -> None:
        MOCK_GMAIL.write_text(json.dumps(data, indent=2))

    def list_unread(self, max_results: int) -> list[dict]:
        unread = [m for m in self._load()["messages"] if m["unread"]]
        return [{k: m[k] for k in ("id", "from_email", "from_name", "subject", "received_at")} for m in unread[:max_results]]

    def get_email(self, email_id: str) -> dict:
        for m in self._load()["messages"]:
            if m["id"] == email_id:
                return m
        return {"error": f"No email with id {email_id}"}

    def create_draft(self, email_id: str, body: str) -> dict:
        data = self._load()
        original = next(m for m in data["messages"] if m["id"] == email_id)
        draft = {"draft_id": f"d-{uuid.uuid4().hex[:8]}", "reply_to_id": email_id, "to": original["from_email"],
                 "subject": "Re: " + original["subject"], "body": body, "created_at": datetime.now().isoformat()}
        data["drafts"].append(draft)
        self._save(data)
        return draft

    def send_draft(self, draft_id: str, approved_by: str) -> dict:
        data = self._load()
        draft = next((d for d in data["drafts"] if d["draft_id"] == draft_id), None)
        if draft is None:
            return {"error": f"No draft {draft_id}"}
        data["drafts"].remove(draft)
        data["sent"].append({**draft, "sent_at": datetime.now().isoformat(), "approved_by": approved_by})
        for m in data["messages"]:
            if m["id"] == draft["reply_to_id"]:
                m["unread"] = False  # handled
        self._save(data)
        return {"sent": True, "draft_id": draft_id, "to": draft["to"]}


# ---------------- real backend: Gmail API ----------------
class RealGmail:
    def __init__(self):
        from common.google_auth import google_service
        self.api = google_service("gmail", "v1").users()

    @staticmethod
    def _header(msg: dict, name: str) -> str:
        return next((h["value"] for h in msg["payload"]["headers"] if h["name"].lower() == name.lower()), "")

    @staticmethod
    def _plain_text(payload: dict) -> str:
        """Find the text/plain part of a (possibly multipart) message."""
        if payload.get("mimeType") == "text/plain" and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
        for part in payload.get("parts", []):
            text = RealGmail._plain_text(part)
            if text:
                return text
        return ""

    def list_unread(self, max_results: int) -> list[dict]:
        listing = self.api.messages().list(userId="me", q="is:unread in:inbox", maxResults=max_results).execute()
        out = []
        for ref in listing.get("messages", []):
            msg = self.api.messages().get(userId="me", id=ref["id"], format="metadata").execute()
            sender = self._header(msg, "From")
            out.append({"id": msg["id"], "from_email": sender.split("<")[-1].strip(">"), "from_name": sender.split("<")[0].strip(' "'),
                        "subject": self._header(msg, "Subject"), "received_at": self._header(msg, "Date")})
        return out

    def get_email(self, email_id: str) -> dict:
        msg = self.api.messages().get(userId="me", id=email_id, format="full").execute()
        sender = self._header(msg, "From")
        return {"id": msg["id"], "thread_id": msg["threadId"], "from_email": sender.split("<")[-1].strip(">"),
                "from_name": sender.split("<")[0].strip(' "'), "subject": self._header(msg, "Subject"),
                "body": self._plain_text(msg["payload"]), "received_at": self._header(msg, "Date"),
                "message_id_header": self._header(msg, "Message-ID")}

    def create_draft(self, email_id: str, body: str) -> dict:
        original = self.get_email(email_id)
        mime = MIMEText(body)
        mime["To"] = original["from_email"]
        mime["Subject"] = "Re: " + original["subject"]
        mime["In-Reply-To"] = mime["References"] = original["message_id_header"]
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        draft = self.api.drafts().create(userId="me", body={"message": {"raw": raw, "threadId": original["thread_id"]}}).execute()
        return {"draft_id": draft["id"], "reply_to_id": email_id, "to": original["from_email"], "body": body}

    def send_draft(self, draft_id: str, approved_by: str) -> dict:
        draft = self.api.drafts().get(userId="me", id=draft_id, format="metadata").execute()
        sent = self.api.drafts().send(userId="me", body={"id": draft_id}).execute()
        # Mark the customer's email as read (the thread is handled).
        thread = self.api.threads().get(userId="me", id=draft["message"]["threadId"], format="minimal").execute()
        for m in thread["messages"]:
            self.api.messages().modify(userId="me", id=m["id"], body={"removeLabelIds": ["UNREAD"]}).execute()
        return {"sent": True, "draft_id": draft_id, "message_id": sent["id"], "approved_by": approved_by}


_backend = None


def backend():
    global _backend
    if _backend is None:
        _backend = RealGmail() if GOOGLE_MODE == "real" else MockGmail()
    return _backend


# ---------------- MCP tools ----------------
@mcp.tool()
def list_unread(max_results: int = 30) -> list[dict]:
    """List unread emails in the support inbox (id, sender, subject, time)."""
    return backend().list_unread(max_results)


@mcp.tool()
def get_email(email_id: str) -> dict:
    """Get one email with its full body."""
    return backend().get_email(email_id)


@mcp.tool()
def create_draft(email_id: str, body: str) -> dict:
    """Save a reply as a DRAFT in the email's thread. Nothing is sent."""
    return backend().create_draft(email_id, body)


@mcp.tool()
def send_draft(draft_id: str, approved_by: str) -> dict:
    """Send a draft. Only call this after a human approved it; approved_by = that human's name."""
    if not approved_by.strip():
        return {"sent": False, "error": "Refusing to send: no human approval (approved_by is empty)."}
    return backend().send_draft(draft_id, approved_by)


if __name__ == "__main__":
    mcp.run()
