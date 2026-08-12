"""Measured read-only public order-book capture for matched contracts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient


def _fetch(client: Any, identifier: str) -> dict[str, Any]:
    before = monotonic()
    response = client.get_orderbook(identifier, depth=50) if isinstance(client, KalshiPublicClient) else client.get_orderbook(identifier)
    received = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = response.data
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {"identifier": identifier, "source_url": response.url, "http_status": response.status,
            "received_at": received, "request_elapsed_ms": round((monotonic() - before) * 1000, 3),
            "payload_sha256": hashlib.sha256(canonical).hexdigest(), "payload": payload}


def capture_pair(kalshi_ticker: str, polymarket_token_id: str) -> dict[str, Any]:
    pair_id = hashlib.sha256(f"{kalshi_ticker}|{polymarket_token_id}".encode()).hexdigest()
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    k = _fetch(KalshiPublicClient(), kalshi_ticker)
    p = _fetch(PolymarketPublicClient(), polymarket_token_id)
    kr = datetime.fromisoformat(k["received_at"].replace("Z", "+00:00"))
    pr = datetime.fromisoformat(p["received_at"].replace("Z", "+00:00"))
    return {"schema_version": 1, "pair_id": pair_id, "started_at": started,
            "receipt_skew_ms": abs(int((kr-pr).total_seconds()*1000)), "kalshi": k, "polymarket": p}
