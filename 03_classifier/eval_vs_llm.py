"""Chapter 3c: fine-tuned DistilBERT vs. a zero-shot LLM on 50 hand-written emails.

The 50 emails in 08_evals/eval_emails.json were written by hand, NOT from the
training templates, so this is an honest test.

Reports for each approach: accuracy, average latency per email, cost per 1,000 emails.
The LLM part needs an API key (see .env.example). Without one, only the
fine-tuned model is evaluated and the script says so.

Run:  python 03_classifier/eval_vs_llm.py
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from intent_classifier import IntentClassifier  # noqa: E402

from common.config import ARTIFACTS, INTENTS, LLM_MODEL, LLM_PROVIDER, ROOT  # noqa: E402
from common.llm import LLMNotConfigured, cost_usd, get_llm  # noqa: E402

EVAL_FILE = ROOT / "08_evals" / "eval_emails.json"

ZERO_SHOT_PROMPT = """You classify customer emails for Vardhan Pumps & Services, an industrial pump company.
Pick exactly one intent:
- order_status: asking where an order is, delivery date, tracking, order status
- service_booking: wants a technician visit, installation, maintenance appointment, reschedule
- warranty_claim: asks if something is covered by warranty, wants a free repair/replacement, extended warranty
- technical_question: how-to or troubleshooting questions about a pump
- complaint: angry or unhappy about service/product, wants escalation or refund
- other: anything else (dealership, jobs, invoices, thanks, address change, quotes)

Reply with only the intent name, nothing else.

Email:
{email}"""


def email_text(e: dict) -> str:
    return f"Subject: {e['subject']}\n\n{e['body']}"


def report(name: str, preds: list[str], golds: list[str], seconds: list[float], cost_per_1k: str) -> dict:
    acc = sum(p == g for p, g in zip(preds, golds)) / len(golds)
    latency_ms = 1000 * sum(seconds) / len(seconds)
    print(f"\n{name}\n  accuracy        {acc:.1%} ({sum(p == g for p, g in zip(preds, golds))}/{len(golds)})")
    print(f"  latency/email   {latency_ms:.0f} ms\n  cost/1K emails  {cost_per_1k}")
    mistakes = Counter((g, p) for p, g in zip(preds, golds) if p != g)
    for (gold, pred), n in mistakes.most_common():
        print(f"    {n} x  expected {gold:<19} got {pred}")
    return {"accuracy": round(acc, 4), "latency_ms": round(latency_ms, 1), "cost_per_1k_emails": cost_per_1k}


def main() -> None:
    emails = json.loads(EVAL_FILE.read_text())
    golds = [e["expected_intent"] for e in emails]
    results = {}

    # 1. Fine-tuned DistilBERT (runs locally, free)
    clf = IntentClassifier()
    clf.predict("warm up")  # first call is slower (loading weights into memory)
    preds, secs = [], []
    for e in emails:
        start = time.perf_counter()
        preds.append(clf.predict(email_text(e))[0])
        secs.append(time.perf_counter() - start)
    results["fine_tuned_distilbert"] = report("Fine-tuned DistilBERT (local CPU)", preds, golds, secs, "$0 (runs on your own machine)")

    # 2. Zero-shot LLM
    try:
        llm = get_llm(max_tokens=4000)  # room for the model's built-in thinking
    except LLMNotConfigured as err:
        print(f"\nZero-shot LLM baseline skipped:\n{err}")
    else:
        preds, secs, cost = [], [], 0.0
        for e in emails:
            start = time.perf_counter()
            reply = llm.invoke(ZERO_SHOT_PROMPT.format(email=email_text(e)))
            secs.append(time.perf_counter() - start)
            label = reply.text.strip().lower()
            preds.append(label if label in INTENTS else "other")
            usage = reply.usage_metadata or {}
            cost += cost_usd(usage.get("input_tokens", 0), usage.get("output_tokens", 0)) or 0.0
        per_1k = f"${cost / len(emails) * 1000:.2f}" if cost else "unknown (add model price in common/llm.py)"
        results["zero_shot_llm"] = report(f"Zero-shot LLM ({LLM_PROVIDER}:{LLM_MODEL})", preds, golds, secs, per_1k)

    out = ARTIFACTS / "classifier_eval.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
