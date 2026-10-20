"""Create the mock Gmail inbox and mock technician calendar (for GOOGLE_MODE=mock).

  artifacts/mock_gmail.json     30 unread customer emails (from mock_seed/inbox.json)
  artifacts/mock_calendar.json  technicians' existing visits for the next 14 days

Run again any time to reset the demo.
Run:  python 05_mcp_servers/seed_mock_data.py
"""

import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from common.config import MOCK_CALENDAR, MOCK_GMAIL  # noqa: E402

SLOT_STARTS = ["09:00", "11:30", "14:30"]
TECH_IDS = ["T01", "T02", "T03", "T04", "T05"]
SITES = ["Kothrud", "Baner", "Hinjewadi", "Chakan", "Wakad", "Hadapsar", "Talegaon", "Shirur"]


def main() -> None:
    random.seed(1)
    inbox = json.loads((HERE / "mock_seed" / "inbox.json").read_text())
    for message in inbox:
        message["unread"] = True
    MOCK_GMAIL.write_text(json.dumps({"messages": inbox, "drafts": [], "sent": []}, indent=2))

    events, today = [], date.today()
    for offset in range(1, 15):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:
            continue  # Sunday off
        for tech in TECH_IDS:
            for hhmm in SLOT_STARTS:
                if random.random() < 0.6:  # technicians are busy ~60% of the time
                    start = datetime.fromisoformat(f"{day}T{hhmm}")
                    events.append({"event_id": f"ev-seed-{len(events)}", "tech_id": tech,
                                   "start": start.isoformat(timespec="minutes"),
                                   "end": (start + timedelta(hours=2)).isoformat(timespec="minutes"),
                                   "title": f"Service visit - {random.choice(SITES)}", "description": ""})
    MOCK_CALENDAR.write_text(json.dumps({"events": events}, indent=2))
    print(f"Mock inbox: {len(inbox)} unread emails -> {MOCK_GMAIL}")
    print(f"Mock calendar: {len(events)} existing visits over the next 14 days -> {MOCK_CALENDAR}")


if __name__ == "__main__":
    main()
