from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RateLimitState:
    request_timestamps: deque[float] = field(default_factory=deque)
    token_events: deque[tuple[float, int]] = field(default_factory=deque)


class GroqRateLimiter:
    """In-memory limiter for Groq free-tier quotas (RPM/RPD/TPM/TPD)."""

    def __init__(
        self,
        *,
        requests_per_minute: int,
        requests_per_day: int,
        tokens_per_minute: int,
        tokens_per_day: int,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.tokens_per_minute = tokens_per_minute
        self.tokens_per_day = tokens_per_day
        self._state = RateLimitState()
        self._lock = Lock()

    def _prune(self, now: float) -> None:
        minute_ago = now - 60.0
        day_ago = now - 86400.0
        while self._state.request_timestamps and self._state.request_timestamps[0] < day_ago:
            self._state.request_timestamps.popleft()
        while self._state.token_events and self._state.token_events[0][0] < day_ago:
            self._state.token_events.popleft()
        # Keep minute-level request count accurate
        recent_requests = [ts for ts in self._state.request_timestamps if ts >= minute_ago]
        self._state.request_timestamps = deque(recent_requests)

    def _usage(self, now: float) -> dict[str, int]:
        minute_ago = now - 60.0
        day_ago = now - 86400.0
        requests_minute = sum(1 for ts in self._state.request_timestamps if ts >= minute_ago)
        requests_day = len(self._state.request_timestamps)
        tokens_minute = sum(tokens for ts, tokens in self._state.token_events if ts >= minute_ago)
        tokens_day = sum(tokens for ts, tokens in self._state.token_events if ts >= day_ago)
        return {
            "requests_minute": requests_minute,
            "requests_day": requests_day,
            "tokens_minute": tokens_minute,
            "tokens_day": tokens_day,
        }

    def check(self, estimated_tokens: int) -> tuple[bool, str | None]:
        with self._lock:
            now = time.monotonic()
            self._prune(now)
            usage = self._usage(now)
            if usage["requests_minute"] >= self.requests_per_minute:
                return False, "Groq request-per-minute limit reached"
            if usage["requests_day"] >= self.requests_per_day:
                return False, "Groq request-per-day limit reached"
            if usage["tokens_minute"] + estimated_tokens > self.tokens_per_minute:
                return False, "Groq tokens-per-minute limit would be exceeded"
            if usage["tokens_day"] + estimated_tokens > self.tokens_per_day:
                return False, "Groq tokens-per-day limit would be exceeded"
            return True, None

    def record(self, *, tokens_used: int) -> None:
        with self._lock:
            now = time.monotonic()
            self._state.request_timestamps.append(now)
            self._state.token_events.append((now, tokens_used))

    def wait_if_needed(self, estimated_tokens: int, *, max_wait_seconds: float = 65.0) -> None:
        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            allowed, _ = self.check(estimated_tokens)
            if allowed:
                return
            time.sleep(1.0)
