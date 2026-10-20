"""Chapter 4b: ask a question, get retrieved sources (offline) and an answer with citations (LLM).

Run:  python 04_rag/ask.py "my booster pump keeps clicking on and off"
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from retriever import search  # noqa: E402

from common.llm import LLMNotConfigured, get_llm  # noqa: E402

ANSWER_PROMPT = """Answer the customer's question using ONLY the sources below.
After each fact, cite its source exactly as written, e.g. [VB-300 Pressure Booster Pump — Owner's Manual § Maintenance schedule].
If the sources don't contain the answer, say you don't know.

Sources:
{sources}

Question: {question}"""


def answer(question: str) -> tuple[str, list[dict]]:
    hits = search(question)
    sources = "\n\n".join(f"{h['citation']}\n{h['text']}" for h in hits)
    reply = get_llm().invoke(ANSWER_PROMPT.format(sources=sources, question=question))
    return reply.text, hits


def main() -> None:
    question = " ".join(sys.argv[1:]) or "My VP-100 is making a rattling noise like gravel. What should I check?"
    print(f"Question: {question}\n\nRetrieved (offline, local embeddings):")
    for h in search(question):
        print(f"  {h['score']:.3f}  {h['citation']}")
    try:
        text, _ = answer(question)
        print(f"\nAnswer:\n{text}")
    except LLMNotConfigured as err:
        print(f"\nAnswer generation skipped:\n{err}")


if __name__ == "__main__":
    main()
