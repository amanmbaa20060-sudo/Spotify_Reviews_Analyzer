from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(
        self,
        *,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {}

    def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(
                    headers=self.headers, timeout=self.timeout_seconds, follow_redirects=True
                ) as client:
                    response = client.get(url, params=params)
                    if response.status_code == 429:
                        raise httpx.HTTPStatusError(
                            "Rate limited",
                            request=response.request,
                            response=response,
                        )
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep_for = self.backoff_seconds * (2**attempt)
                logger.warning(
                    "HTTP request failed (attempt %s/%s) url=%s error=%s; retrying in %.1fs",
                    attempt + 1,
                    self.max_retries + 1,
                    url,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)
        assert last_error is not None
        raise last_error
