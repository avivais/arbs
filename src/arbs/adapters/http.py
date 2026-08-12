"""Small standard-library JSON HTTP client with bounded retries."""

from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover - Python may have a correctly configured system CA store.
    certifi = None


class ApiError(RuntimeError):
    """A public API request failed or returned an invalid response."""


@dataclass(frozen=True)
class JsonResponse:
    data: Any
    url: str
    status: int
    elapsed_ms: float
    received_at_unix_ms: int


class JsonHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_attempts: int = 3,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        max_response_bytes: int = 10_000_000,
        max_retry_after_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0 or max_attempts < 1 or max_response_bytes < 1 or max_retry_after_seconds < 0:
            raise ValueError("invalid HTTP client bounds")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_response_bytes = max_response_bytes
        self.max_retry_after_seconds = max_retry_after_seconds
        self._opener = opener
        self._sleeper = sleeper
        self._ssl_context = ssl.create_default_context(cafile=certifi.where() if certifi else None)

    def get(self, base_url: str, path: str, params: Optional[Mapping[str, Any]] = None) -> JsonResponse:
        query = urlencode([(key, value) for key, value in (params or {}).items() if value is not None])
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "arbs/0.1"}, method="GET")

        for attempt in range(1, self.max_attempts + 1):
            started = time.monotonic()
            try:
                with self._opener(request, timeout=self.timeout_seconds, context=self._ssl_context) as response:
                    payload = response.read(self.max_response_bytes + 1)
                    if len(payload) > self.max_response_bytes:
                        raise ApiError(f"Response too large from {url}")
                    status = int(getattr(response, "status", 200))
                try:
                    data = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ApiError(f"Invalid JSON from {url}: {exc}") from exc
                return JsonResponse(
                    data=data,
                    url=url,
                    status=status,
                    elapsed_ms=(time.monotonic() - started) * 1000,
                    received_at_unix_ms=time.time_ns() // 1_000_000,
                )
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == self.max_attempts:
                    raise ApiError(f"HTTP {exc.code} from {url}") from exc
                delay = 0.25 * (2 ** (attempt - 1))
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            delay = max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
                        except (TypeError, ValueError, OverflowError):
                            pass
                self._sleeper(min(delay, self.max_retry_after_seconds))
                continue
            except (URLError, TimeoutError) as exc:
                if attempt == self.max_attempts:
                    raise ApiError(f"Request failed for {url}: {type(exc).__name__}") from exc
            self._sleeper(0.25 * (2 ** (attempt - 1)))

        raise AssertionError("retry loop exited unexpectedly")
