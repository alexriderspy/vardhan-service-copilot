"""One function that returns the chat model, whatever the provider.

Set LLM_PROVIDER and LLM_MODEL in .env. Default is Anthropic Claude.
We never fake LLM output: if no key is set we stop with a clear message.
"""

import os

from common.config import LLM_MODEL, LLM_PROVIDER

# Which environment variable each provider needs (Ollama runs locally, no key).
KEY_FOR_PROVIDER = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "ollama": None}

# Prices in USD per 1M tokens (input, output), used for cost-per-email numbers.
# Add your model here if you switch. Unknown models report tokens only.
PRICE_PER_MTOK = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


class LLMNotConfigured(RuntimeError):
    """Raised when a step needs an LLM but no provider key is set."""


def llm_is_configured() -> bool:
    key_name = KEY_FOR_PROVIDER.get(LLM_PROVIDER)
    return key_name is None or bool(os.getenv(key_name))


def get_llm(max_tokens: int = 16000):
    """Return a LangChain chat model built from .env settings."""
    if LLM_PROVIDER not in KEY_FOR_PROVIDER:
        raise LLMNotConfigured(f"Unknown LLM_PROVIDER={LLM_PROVIDER!r}. Use anthropic, openai or ollama.")
    if not llm_is_configured():
        raise LLMNotConfigured(
            f"This step needs an LLM, but {KEY_FOR_PROVIDER[LLM_PROVIDER]} is not set.\n"
            f"Copy .env.example to .env and add your key (provider={LLM_PROVIDER}, model={LLM_MODEL}),\n"
            "or set LLM_PROVIDER=ollama to use a free local model."
        )
    from langchain.chat_models import init_chat_model

    # No temperature here: newer Claude models (Opus 5.5) reject sampling params.
    # Opus 5.5 always thinks before answering; max_tokens covers thinking + reply, so keep it roomy.
    return init_chat_model(LLM_MODEL, model_provider=LLM_PROVIDER, max_tokens=max_tokens)


def cost_usd(input_tokens: int, output_tokens: int) -> float | None:
    """Dollar cost of one call, or None if we don't know this model's price."""
    price = PRICE_PER_MTOK.get(LLM_MODEL)
    if price is None:
        return None
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000
