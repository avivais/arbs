#!/usr/bin/env python3
"""Capture a bounded public MLB raw corpus; no authentication or account access."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.ingestion.corpus import write_corpus
from arbs.matching.live import MLB_KALSHI_SERIES, MLB_POLYMARKET_TAG


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    kalshi_response = KalshiPublicClient().list_series_markets(MLB_KALSHI_SERIES, limit=1000, status="open")
    k_payload = kalshi_response.data
    records = [{"venue": "kalshi", "kind": "market", "source_id": str(m["ticker"]),
                "source_url": kalshi_response.url, "received_at": captured_at, "payload": m}
               for m in k_payload.get("markets", [])]
    poly_client = PolymarketPublicClient()
    cursor = None; seen = set()
    for _ in range(10):
        response = poly_client.list_sports_events(MLB_POLYMARKET_TAG, limit=100, after_cursor=cursor)
        payload = response.data
        for event in payload.get("events", []):
            records.append({"venue": "polymarket", "kind": "event", "source_id": str(event["id"]),
                            "source_url": response.url, "received_at": captured_at, "payload": event})
        nxt = payload.get("next_cursor")
        if not nxt: break
        if str(nxt) in seen: raise RuntimeError("repeated cursor")
        seen.add(str(nxt)); cursor = str(nxt)
    else: raise RuntimeError("pagination exceeded bound")
    target = write_corpus(args.output, records, corpus_id="mlb-public-2026-08-12", captured_at=captured_at)
    print(target)
    return 0


if __name__ == "__main__": raise SystemExit(main())
