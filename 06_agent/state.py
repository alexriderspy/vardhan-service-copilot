"""What the agent knows about one email as it moves through the graph."""

import operator
from typing import Annotated, TypedDict


class EmailState(TypedDict, total=False):
    email_id: str
    email: dict                 # from, subject, body
    intent: str                 # one of the 6 intents
    confidence: float           # classifier confidence, 0..1
    intent_source: str          # "model", or the escalation rule that overrode it
    facts: dict                 # what we looked up (orders, pumps, customer)
    sources: list[dict]         # manual/warranty chunks used, with citations
    slots: list[dict]           # free technician slots (service_booking)
    tool_calls: Annotated[list[str], operator.add]   # every tool we called, in order (appended by each node)
    ticket_id: int | None       # complaint ticket
    draft: str                  # reply written by the LLM (empty for complaints)
    llm_usage: dict             # tokens used by the draft (for cost tracking)
    needs_human: str            # why a human must look at this
    decision: dict              # what the human decided in the UI
    result: dict                # what we actually did after approval
