import pytest

from common import llm
from common.config import INTENTS


def test_every_intent_has_a_route():
    import nodes
    assert set(nodes.ROUTES) == set(INTENTS)
    assert nodes.route({"intent": "complaint"}) == "escalate_complaint"


def test_model_detection_and_skills():
    import nodes
    assert nodes.models_mentioned("my borewell pump") == {"VS-200"}
    assert nodes.guess_skill({"subject": "", "body": "booster is clicking"}, []) == "booster"
    assert nodes.guess_skill({"subject": "", "body": "visit please"}, [{"model": "VS-200"}]) == "submersible"


def test_missing_key_fails_loudly(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMNotConfigured, match="ANTHROPIC_API_KEY"):
        llm.get_llm()


def test_date_variants_for_groundedness():
    from metrics import facts_found
    assert facts_found(["2027-02-14"], "Your warranty runs until 14 February 2027.") == [True]
    assert facts_found([["cancelled", "canceled"]], "The order was canceled.") == [True]
