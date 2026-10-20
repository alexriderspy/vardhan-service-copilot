"""Chapter 6 demo: run the agent on emails from the terminal.

  python 06_agent/run_agent.py m021          # one email
  python 06_agent/run_agent.py --all         # whole mock inbox
  python 06_agent/run_agent.py m001 --approve "Asha"   # resume a paused email: approve + send

Without an LLM key the agent still classifies, routes and calls every tool;
it stops at draft_reply with a clear message (complaints need no LLM at all).
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from common.config import use_chapter  # noqa: E402

use_chapter("05_mcp_servers")
from graph import forget, process_email, resume, saved_state  # noqa: E402
from mcp_client import call_tool  # noqa: E402

from common.llm import LLMNotConfigured  # noqa: E402


def show(values: dict) -> None:
    print(f"  intent      {values.get('intent')} ({values.get('confidence', 0):.0%}, {values.get('intent_source', 'model')})")
    print(f"  tools       {' -> '.join(values.get('tool_calls', []))}")
    for s in values.get("sources", []):
        print(f"  source      {s['citation']}  (score {s['score']})")
    for s in values.get("slots", []):
        print(f"  free slot   {s['start']}  {s['technician']}")
    if values.get("ticket_id"):
        print(f"  ticket      #{values['ticket_id']} (high priority)")
    if values.get("needs_human"):
        print(f"  human       {values['needs_human']}")
    if values.get("draft"):
        print("  draft:\n    " + values["draft"].replace("\n", "\n    "))


def run_one(email_id: str, fresh: bool = False) -> None:
    print(f"\n=== {email_id} ===")
    values, waiting = saved_state(email_id)
    if waiting and not fresh:
        show(values)
        print("  status      already PAUSED, waiting for human approval (use --fresh to run again)")
        return
    forget(email_id)
    try:
        values = process_email(email_id)
        show(values)
        print("  status      PAUSED, waiting for human approval")
    except LLMNotConfigured as err:
        values, _ = saved_state(email_id)
        show(values or {})
        print(f"  status      STOPPED at draft_reply (needs an LLM): {str(err).splitlines()[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email_id", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--approve", metavar="REVIEWER")
    parser.add_argument("--reject", action="store_true")
    parser.add_argument("--fresh", action="store_true", help="forget any saved run and start again")
    args = parser.parse_args()

    if args.approve or args.reject:
        values, waiting = saved_state(args.email_id)
        if not waiting:
            sys.exit("That email is not waiting for approval. Run it first.")
        decision = {"action": "reject" if args.reject else "approve", "body": values.get("draft", ""),
                    "slot_index": 0 if values.get("slots") else None, "reviewer": args.approve or ""}
        print(resume(args.email_id, decision).get("result"))
        return

    ids = [m["id"] for m in call_tool("gmail", "list_unread", {})] if args.all else [args.email_id or "m001"]
    for email_id in ids:
        run_one(email_id, args.fresh)


if __name__ == "__main__":
    main()
