from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from spotify_app_review_analyzer.agent.rate_limiter import GroqRateLimiter
from spotify_app_review_analyzer.core.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroqCompletion:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class GroqClientProtocol(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> GroqCompletion: ...


class GroqClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        rate_limiter: GroqRateLimiter | None = None,
    ) -> None:
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.temperature = temperature if temperature is not None else settings.groq_temperature
        self.rate_limiter = rate_limiter or GroqRateLimiter(
            requests_per_minute=settings.groq_requests_per_minute,
            requests_per_day=settings.groq_requests_per_day,
            tokens_per_minute=settings.groq_tokens_per_minute,
            tokens_per_day=settings.groq_tokens_per_day,
        )
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        from groq import Groq

        self._client = Groq(api_key=self.api_key)
        return self._client

    def estimate_tokens(self, text: str) -> int:
        # Rough heuristic: ~4 chars per token for English prose.
        return max(1, len(text) // 4)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> GroqCompletion:
        estimated = self.estimate_tokens(system_prompt + user_prompt)
        self.rate_limiter.wait_if_needed(estimated)
        allowed, reason = self.rate_limiter.check(estimated)
        if not allowed:
            raise RuntimeError(reason or "Groq rate limit exceeded")

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=max_output_tokens or settings.groq_max_output_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or estimated)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or self.estimate_tokens(content))
        total_tokens = input_tokens + output_tokens
        self.rate_limiter.record(tokens_used=total_tokens)
        logger.info(
            "Groq completion model=%s input_tokens=%s output_tokens=%s",
            self.model,
            input_tokens,
            output_tokens,
        )
        return GroqCompletion(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
        )


class MockGroqClient:
    """Deterministic client for tests and offline golden-question runs."""

    def __init__(self, *, response_text: str | None = None) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, str]] = []

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> GroqCompletion:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        text = self.response_text or (
            "Based on the evidence pack, users report discovery friction. "
            "Citations: review_id `00000000-0000-4000-8000-000000000001`."
        )
        return GroqCompletion(
            content=text,
            input_tokens=100,
            output_tokens=50,
            model="mock-groq",
        )
