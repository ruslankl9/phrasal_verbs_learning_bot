from __future__ import annotations

"""Client for Explain feature using an OpenAI-compatible API."""

from dataclasses import dataclass
from openai import AsyncOpenAI


from srsbot.config import (
    EXPLAIN_API_BASE,
    EXPLAIN_API_KEY,
    EXPLAIN_MODEL,
    EXPLAIN_TIMEOUT_SECONDS,
)


@dataclass
class ExplainClientError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


async def get_explanation(prompt: str) -> str:
    """Call OpenAI-compatible chat completions endpoint and return text content.

    Sends a single user message, low temperature, returns first choice content.
    """
    if not EXPLAIN_API_BASE:
        raise ExplainClientError("EXPLAIN_API_BASE is not configured")

    client = AsyncOpenAI(
        base_url=EXPLAIN_API_BASE,
        api_key=EXPLAIN_API_KEY,
        timeout=EXPLAIN_TIMEOUT_SECONDS,
    )
    response = await client.responses.create(
        model=EXPLAIN_MODEL,
        temperature=0.3,
        input=prompt,
        timeout=EXPLAIN_TIMEOUT_SECONDS,
    )

    if response.error:
        raise ExplainClientError(f"OpenAI API error: {response.error}")

    # OpenAI-compatible structure
    try:
        assert response is not None
        content = response.output[0].content[0].text
        return content
    except Exception as e:  # pragma: no cover - defensive
        raise ExplainClientError(f"Unexpected response format: {e}")
