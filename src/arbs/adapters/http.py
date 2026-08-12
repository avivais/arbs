"""Small standard-library JSON HTTP client with bounded retries."""

from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
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
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
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
                    payload = response.read()
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
            except (URLError, TimeoutError) as exc:
                if attempt == self.max_attempts:
                    raise ApiError(f"Request failed for {url}: {exc}") from exc
            self._sleeper(0.25 * (2 ** (attempt - 1)))

        raise AssertionError("retry loop exited unexpectedly")
