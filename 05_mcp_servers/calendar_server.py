"""MCP server: calendar. Technician schedules.

Tools: find_free_slots, create_event.
GOOGLE_MODE=mock (default): events in artifacts/mock_calendar.json.
GOOGLE_MODE=real: Google Calendar free/busy + events (one calendar per technician,
mapped in 05_mcp_servers/technician_calendars.json).

Run standalone (stdio):  python 05_mcp_servers/calendar_server.py
"""

import json
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mcp.server import MCPServer  # noqa: E402
from sqlalchemy import text  # noqa: E402

from common.config import GOOGLE_MODE, MOCK_CALENDAR  # noqa: E402
from common.db import agent_engine  # noqa: E402

mcp = MCPServer("calendar", log_level="WARNING")

# Visits are 2 hours. Three possible visits per day, Monday to Saturday.
SLOT_STARTS = ["09:00", "11:30", "14:30"]
VISIT_HOURS = 2
TIMEZONE = "Asia/Kolkata"


def technicians_with_skill(skill: str) -> list[dict]:
    with agent_engine().connect() as conn:
        techs = [dict(r._mapping) for r in conn.execute(text("SELECT tech_id, name, skills FROM v_technicians"))]
    return [t for t in techs if skill.lower() in t["skills"].lower().split(";")]


def candidate_slots(start_date: str, end_date: str):
    """Every possible visit slot between two dates (no Sundays, nothing in the past)."""
    day, last = date.fromisoformat(start_date), date.fromisoformat(end_date)
    now = datetime.now()
    while day <= last:
        if day.weekday() != 6:
            for hhmm in SLOT_STARTS:
                start = datetime.fromisoformat(f"{day}T{hhmm}")
                if start > now:
                    yield start, start + timedelta(hours=VISIT_HOURS)
        day += timedelta(days=1)


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


# ---------------- mock backend ----------------
class MockCalendar:
    def _load(self) -> dict:
        if not MOCK_CALENDAR.exists():
            raise FileNotFoundError("Mock calendar not found. Run: python 05_mcp_servers/seed_mock_data.py")
        return json.loads(MOCK_CALENDAR.read_text())

    def busy(self, tech_id: str, start: datetime, end: datetime) -> list[tuple]:
        return [(datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"]))
                for e in self._load()["events"] if e["tech_id"] == tech_id]

    def create_event(self, tech_id, start, end, title, description) -> dict:
        data = self._load()
        event = {"event_id": f"ev-{uuid.uuid4().hex[:8]}", "tech_id": tech_id, "start": start, "end": end,
                 "title": title, "description": description}
        data["events"].append(event)
        MOCK_CALENDAR.write_text(json.dumps(data, indent=2))
        return event


# ---------------- real backend ----------------
class RealCalendar:
    def __init__(self):
        from common.google_auth import google_service
        self.api = google_service("calendar", "v3")
        self.calendar_ids = json.loads((HERE / "technician_calendars.json").read_text())

    def busy(self, tech_id: str, start: datetime, end: datetime) -> list[tuple]:
        cal_id = self.calendar_ids.get(tech_id, "primary")
        body = {"timeMin": start.isoformat() + "+05:30", "timeMax": end.isoformat() + "+05:30",
                "timeZone": TIMEZONE, "items": [{"id": cal_id}]}
        periods = self.api.freebusy().query(body=body).execute()["calendars"][cal_id]["busy"]
        return [(datetime.fromisoformat(p["start"]).replace(tzinfo=None), datetime.fromisoformat(p["end"]).replace(tzinfo=None))
                for p in periods]

    def create_event(self, tech_id, start, end, title, description) -> dict:
        cal_id = self.calendar_ids.get(tech_id, "primary")
        event = self.api.events().insert(calendarId=cal_id, body={
            "summary": title, "description": description,
            "start": {"dateTime": start, "timeZone": TIMEZONE}, "end": {"dateTime": end, "timeZone": TIMEZONE},
        }).execute()
        return {"event_id": event["id"], "tech_id": tech_id, "start": start, "end": end, "title": title}


_backend = None


def backend():
    global _backend
    if _backend is None:
        _backend = RealCalendar() if GOOGLE_MODE == "real" else MockCalendar()
    return _backend


# ---------------- MCP tools ----------------
@mcp.tool()
def find_free_slots(technician_skill: str, start_date: str, end_date: str, max_slots: int = 5) -> list[dict]:
    """Find free 2-hour visit slots for technicians with a skill (centrifugal / submersible / booster)
    between two dates (YYYY-MM-DD). Earliest first."""
    techs = technicians_with_skill(technician_skill)
    window_start = datetime.fromisoformat(f"{start_date}T00:00")
    window_end = datetime.fromisoformat(f"{end_date}T23:59")
    busy = {t["tech_id"]: backend().busy(t["tech_id"], window_start, window_end) for t in techs}
    free = []
    for start, end in candidate_slots(start_date, end_date):
        for tech in techs:
            if not any(overlaps(start, end, b0, b1) for b0, b1 in busy[tech["tech_id"]]):
                free.append({"tech_id": tech["tech_id"], "technician": tech["name"],
                             "start": start.isoformat(timespec="minutes"), "end": end.isoformat(timespec="minutes")})
                break  # one technician per slot is enough
        if len(free) >= max_slots:
            break
    return free


@mcp.tool()
def create_event(tech_id: str, start: str, end: str, title: str, description: str = "") -> dict:
    """Book a visit on a technician's calendar. Only call after a human approved the booking."""
    return backend().create_event(tech_id, start, end, title, description)


if __name__ == "__main__":
    mcp.run()
