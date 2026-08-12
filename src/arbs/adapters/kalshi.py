"""Kalshi production public market-data API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .http import JsonHttpClient, JsonResponse


class KalshiPublicClient:
    BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

    def __init__(self, http: Optional[JsonHttpClient] = None) -> None:
        self.http = http or JsonHttpClient()

    def list_markets(self, *, limit: int = 10, status: str = "open", cursor: Optional[str] = None) -> JsonResponse:
        if not 1 <= limit <= 1000:
            raise ValueError("Kalshi limit must be between 1 and 1000")
        if status not in {"unopened", "open", "paused", "closed", "settled"}:
            raise ValueError("Unsupported Kalshi market status")
        return self.http.get(self.BASE_URL, "/markets", {"limit": limit, "status": status, "cursor": cursor})

    def list_series(self, *, category: str = "Sports", limit: int = 100, cursor: Optional[str] = None) -> JsonResponse:
        if not 1 <= limit <= 1000:
            raise ValueError("Kalshi limit must be between 1 and 1000")
        return self.http.get(
            self.BASE_URL, "/series", {"category": category, "limit": limit, "cursor": cursor}
        )

    def list_series_markets(
        self, series_ticker: str, *, limit: int = 1000, status: str = "open", cursor: Optional[str] = None
    ) -> JsonResponse:
        if not series_ticker:
            raise ValueError("series_ticker is required")
        if not 1 <= limit <= 1000:
            raise ValueError("Kalshi limit must be between 1 and 1000")
        return self.http.get(
            self.BASE_URL,
            "/markets",
            {"series_ticker": series_ticker, "status": status, "limit": limit, "cursor": cursor},
        )

    def get_market(self, ticker: str) -> JsonResponse:
        return self.http.get(self.BASE_URL, f"/markets/{ticker}")

    def get_orderbook(self, ticker: str, *, depth: Optional[int] = None) -> JsonResponse:
        params: Dict[str, Any] = {"depth": depth}
        return self.http.get(self.BASE_URL, f"/markets/{ticker}/orderbook", params)
