"""Chapter 8: evaluate the whole agent on 50 held-out, hand-written emails.

For every email we check:
  intent accuracy      did we pick the right intent? (model + escalation rule)
  tool routing         did the agent call the right tool?
  context recall       are the must-include facts in what the tools/RAG returned?   (offline)
  groundedness         are those facts in the LLM's draft, and are its citations real? (needs LLM)
  latency + cost       per email

Evals run on a COPY of the database and talk to the MCP servers in-process,
so they never touch real data or the production audit log.

Run:  python 08_evals/run_evals.py            (add --gate to fail CI if below thresholds)
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "06_agent"), str(ROOT / "08_evals")]

# --- isolate evals: in-process MCP + a throwaway copy of the SQLite database ---
os.environ["MCP_TRANSPORT"] = "inprocess"
from common import config  # noqa: E402

if config.DATABASE_URL.startswith("sqlite"):
    eval_db = config.ARTIFACTS / "eval_copy.db"
    shutil.copy(config.SQLITE_DB, eval_db)
    config.DATABASE_URL = config.AGENT_DATABASE_URL = f"sqlite:///{eval_db}"
    import common.db as db  # noqa: E402
    db.DATABASE_URL = db.AGENT_DATABASE_URL = config.DATABASE_URL

import nodes  # noqa: E402
from metrics import facts_found  # noqa: E402

from common.llm import cost_usd, llm_is_configured  # noqa: E402

nodes.write_audit = lambda *args, **kwargs: None   # evals don't write to the audit log

EVAL_FILE = ROOT / "08_evals" / "eval_emails.json"
GATES = {"intent_accuracy": 0.85, "tool_routing_accuracy": 0.85, "context_recall": 0.80, "groundedness": 0.80}
CITATION = re.compile(r"\[([^\[\]]+?) § ([^\[\]]+?)\]")


def pretty(key: str, value) -> str:
    """Format one metric for the terminal."""
    if value is None or not isinstance(value, float):
        return str(value)
    if key.endswith("_ms_per_email"):
        return f"{value:.0f} ms"
    if key.endswith("_usd"):
        return f"${value:.2f}"
    return f"{value:.1%}"


def run_offline(email: dict) -> tuple[dict, float]:
    """classify -> route -> gather facts. No LLM."""
    start = time.perf_counter()
    state = {"email_id": f"eval-{email['id']}", "email": {**email, "from_name": ""}, "tool_calls": []}
    state.update(nodes.classify(state))
    out = getattr(nodes, nodes.route(state))(state)
    out["tool_calls"] = state["tool_calls"] + out.get("tool_calls", [])
    state.update(out)
    return state, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", action="store_true", help="exit with error if a metric is below its threshold")
    parser.add_argument("--limit", type=int, default=0, help="only the first N emails (quick check)")
    args = parser.parse_args()

    emails = json.loads(EVAL_FILE.read_text())[: args.limit or None]
    use_llm = llm_is_configured()
    rows = []
    nodes.get_classifier().predict("warm up")

    for email in emails:
        state, offline_secs = run_offline(email)
        tools = [t.split(".")[-1] for t in state["tool_calls"]]
        expected_tool = email["expected_tool"]
        routed_ok = (not tools) if expected_tool == "none" else expected_tool in tools
        context = json.dumps(state.get("facts", {}), default=str) + json.dumps(state.get("slots", [])) + \
            " ".join(s["text"] for s in state.get("sources", []))
        row = {"id": email["id"], "expected": email["expected_intent"], "predicted": state["intent"],
               "intent_source": state.get("intent_source"), "tools": tools, "routed_ok": routed_ok,
               "context_facts": facts_found(email["must_include"], context), "offline_secs": offline_secs}

        if use_llm and state["intent"] != "complaint":
            start = time.perf_counter()
            state.update(nodes.draft_reply(state))
            row["llm_secs"] = time.perf_counter() - start
            row["draft_facts"] = facts_found(email["must_include"], state["draft"])
            real_citations = {(s["doc"], s["section"]) for s in state.get("sources", [])}
            cited = CITATION.findall(state["draft"])
            row["citations"] = len(cited)
            row["valid_citations"] = sum((d.strip(), s.strip()) in real_citations for d, s in cited)
            usage = state["llm_usage"]
            row["cost_usd"] = cost_usd(usage["input_tokens"], usage["output_tokens"])
            row["draft"] = state["draft"]
        rows.append(row)
        mark = "ok " if row["predicted"] == row["expected"] and routed_ok else "MISS"
        print(f"{mark} {email['id']}  expected {row['expected']:<19} got {row['predicted']:<19} tools={tools}")

    # ---- metrics ----
    def mean(values):
        values = list(values)
        return sum(values) / len(values) if values else None

    all_context = [f for r in rows for f in r["context_facts"]]
    metrics = {
        "emails": len(rows),
        "intent_accuracy": mean(r["predicted"] == r["expected"] for r in rows),
        "tool_routing_accuracy": mean(r["routed_ok"] for r in rows),
        "context_recall": mean(all_context),
        "offline_latency_ms_per_email": 1000 * mean(r["offline_secs"] for r in rows),
        "rule_overrides": sum(r["intent_source"] != "model" for r in rows),
    }
    if use_llm:
        drafted = [r for r in rows if "draft_facts" in r]
        metrics["groundedness"] = mean(f for r in drafted for f in r["draft_facts"])
        metrics["citation_validity"] = mean(r["valid_citations"] / r["citations"] for r in drafted if r["citations"])
        metrics["llm_latency_ms_per_email"] = 1000 * mean(r["llm_secs"] for r in drafted)
        costs = [r["cost_usd"] for r in drafted if r["cost_usd"] is not None]
        metrics["llm_cost_per_1k_emails_usd"] = 1000 * mean(costs) if costs else None
    else:
        metrics["groundedness"] = None
        metrics["note"] = "No LLM key set: groundedness, citation validity and LLM cost were not measured."

    print("\nResults")
    for key, value in metrics.items():
        print(f"  {key:<30} {pretty(key, value)}")

    (config.ARTIFACTS / "eval_report.json").write_text(json.dumps({"metrics": metrics, "rows": rows}, indent=2, default=str))
    print(f"\nSaved {config.ARTIFACTS / 'eval_report.json'}")

    if args.gate:
        failed = [k for k, threshold in GATES.items() if metrics.get(k) is not None and metrics[k] < threshold]
        if failed:
            sys.exit(f"EVAL GATE FAILED: {', '.join(f'{k}={metrics[k]:.1%} < {GATES[k]:.0%}' for k in failed)}")
        print("Eval gate passed.")


if __name__ == "__main__":
    main()
