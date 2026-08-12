"""Polymarket production public Gamma and CLOB APIs."""

from __future__ import annotations

from typing import Optional

from .http import JsonHttpClient, JsonResponse


class PolymarketPublicClient:
    GAMMA_URL = "https://gamma-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"

    def __init__(self, http: Optional[JsonHttpClient] = None) -> None:
        self.http = http or JsonHttpClient()

    def list_markets(
        self, *, limit: int = 10, active: bool = True, closed: bool = False, after_cursor: Optional[str] = None
    ) -> JsonResponse:
        if not 1 <= limit <= 100:
            raise ValueError("Polymarket limit must be between 1 and 100")
        return self.http.get(
            self.GAMMA_URL,
            "/markets/keyset",
            {
                "limit": limit,
                "active": str(active).lower(),
                "closed": str(closed).lower(),
                "after_cursor": after_cursor,
            },
        )

    def list_sports_events(
        self,
        tag_id: int,
        *,
        limit: int = 100,
        active: bool = True,
        closed: bool = False,
        after_cursor: Optional[str] = None,
    ) -> JsonResponse:
        if not 1 <= limit <= 100:
            raise ValueError("Polymarket limit must be between 1 and 100")
        return self.http.get(
            self.GAMMA_URL,
            "/events/keyset",
            {
                "tag_id": tag_id,
                "limit": limit,
                "active": str(active).lower(),
                "closed": str(closed).lower(),
                "after_cursor": after_cursor,
            },
        )

    def list_sports(self) -> JsonResponse:
        return self.http.get(self.GAMMA_URL, "/sports")

    def list_sports_market_types(self) -> JsonResponse:
        return self.http.get(self.GAMMA_URL, "/sports/market-types")

    def list_teams(self, *, limit: int = 100, offset: int = 0) -> JsonResponse:
        return self.http.get(self.GAMMA_URL, "/teams", {"limit": limit, "offset": offset})

    def get_orderbook(self, token_id: str) -> JsonResponse:
        return self.http.get(self.CLOB_URL, "/book", {"token_id": token_id})
