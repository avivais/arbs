"""Read-only production API connectivity smoke check."""

from __future__ import annotations

import json
from typing import Any, Dict

from .adapters import KalshiPublicClient, PolymarketPublicClient
from .adapters.http import ApiError, JsonResponse


def _summary(response: JsonResponse, count: int) -> Dict[str, Any]:
    return {
        "ok": True,
        "status": response.status,
        "elapsed_ms": round(response.elapsed_ms, 1),
        "received_at_unix_ms": response.received_at_unix_ms,
        "item_count": count,
        "url": response.url,
    }


def check_connections() -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    try:
        response = KalshiPublicClient().list_markets(limit=3)
        markets = response.data.get("markets", []) if isinstance(response.data, dict) else []
        results["kalshi_markets"] = _summary(response, len(markets))
    except (ApiError, ValueError) as exc:
        results["kalshi_markets"] = {"ok": False, "error": str(exc)}

    polymarket = PolymarketPublicClient()
    for name, fetch in (
        ("polymarket_markets", lambda: polymarket.list_markets(limit=3)),
        ("polymarket_sports", polymarket.list_sports),
        ("polymarket_sports_market_types", polymarket.list_sports_market_types),
    ):
        try:
            response = fetch()
            payload = response.data
            if isinstance(payload, list):
                count = len(payload)
            elif isinstance(payload, dict):
                collection = payload.get("markets", payload.get("marketTypes", []))
                count = len(collection) if isinstance(collection, list) else 0
            else:
                count = 0
            results[name] = _summary(response, count)
        except (ApiError, ValueError) as exc:
            results[name] = {"ok": False, "error": str(exc)}
    return results


def main() -> int:
    results = check_connections()
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(result.get("ok") for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

