"""Sports catalog discovery and immutable JSONL snapshot storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.adapters.http import JsonResponse


class IngestionError(RuntimeError):
    pass


@dataclass
class Capture:
    records: List[Dict[str, Any]] = field(default_factory=list)
    request_count: int = 0
    duplicate_count: int = 0
    status: str = "complete"
    errors: List[Dict[str, str]] = field(default_factory=list)

    def fail(self, stage: str, error: BaseException) -> None:
        self.status = "partial" if self.records else "failed"
        self.errors.append({"stage": stage, "error_type": type(error).__name__, "message": str(error)})

    def add(self, *, venue: str, kind: str, response: JsonResponse, payload: Any, parent_id: Optional[str] = None) -> None:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.records.append(
            {
                "venue": venue,
                "kind": kind,
                "parent_id": parent_id,
                "source_url": response.url,
                "http_status": response.status,
                "request_elapsed_ms": round(response.elapsed_ms, 3),
                "received_at_unix_ms": response.received_at_unix_ms,
                "sha256": hashlib.sha256(canonical).hexdigest(),
                "payload": payload,
            }
        )


def _next_cursor(payload: Dict[str, Any], key: str) -> Optional[str]:
    value = payload.get(key)
    if value in (None, "", "LTE="):
        return None
    return str(value)


def capture_kalshi(
    client: KalshiPublicClient,
    capture: Capture,
    *,
    max_series: Optional[int] = None,
    max_pages: int = 1000,
) -> None:
    cursor: Optional[str] = None
    seen_cursors: Set[str] = set()
    series_seen = 0
    pages = 0
    while True:
        response = client.list_series(category="Sports", limit=100, cursor=cursor)
        capture.request_count += 1
        pages += 1
        payload = response.data
        if not isinstance(payload, dict) or not isinstance(payload.get("series"), list):
            raise IngestionError("Kalshi series response has an unexpected shape")
        for series in payload["series"]:
            ticker = str(series.get("ticker", ""))
            if not ticker:
                raise IngestionError("Kalshi series is missing ticker")
            capture.add(venue="kalshi", kind="series", response=response, payload=series)
            _capture_kalshi_series_markets(client, capture, ticker, max_pages=max_pages)
            series_seen += 1
            if max_series is not None and series_seen >= max_series:
                return
        cursor = _next_cursor(payload, "cursor")
        if not cursor:
            return
        if cursor in seen_cursors or pages >= max_pages:
            raise IngestionError("Kalshi series pagination did not terminate safely")
        seen_cursors.add(cursor)


def _capture_kalshi_series_markets(
    client: KalshiPublicClient, capture: Capture, ticker: str, *, max_pages: int
) -> None:
    cursor: Optional[str] = None
    seen_cursors: Set[str] = set()
    seen_tickers: Set[str] = set()
    pages = 0
    while True:
        response = client.list_series_markets(ticker, limit=1000, status="open", cursor=cursor)
        capture.request_count += 1
        pages += 1
        payload = response.data
        if not isinstance(payload, dict) or not isinstance(payload.get("markets"), list):
            raise IngestionError("Kalshi markets response has an unexpected shape")
        for market in payload["markets"]:
            market_id = str(market.get("ticker", ""))
            if not market_id:
                raise IngestionError("Kalshi market is missing ticker")
            if market_id in seen_tickers:
                capture.duplicate_count += 1
                continue
            seen_tickers.add(market_id)
            capture.add(venue="kalshi", kind="market", response=response, payload=market, parent_id=ticker)
        cursor = _next_cursor(payload, "cursor")
        if not cursor:
            return
        if cursor in seen_cursors or pages >= max_pages:
            raise IngestionError(f"Kalshi market pagination did not terminate for {ticker}")
        seen_cursors.add(cursor)


def capture_polymarket(
    client: PolymarketPublicClient,
    capture: Capture,
    *,
    max_sports: Optional[int] = None,
    max_pages: int = 1000,
) -> None:
    sports_response = client.list_sports()
    capture.request_count += 1
    sports = sports_response.data
    if not isinstance(sports, list):
        raise IngestionError("Polymarket sports response has an unexpected shape")
    seen_sports: Set[str] = set()
    seen_events: Set[str] = set()
    seen_markets: Set[str] = set()
    processed = 0
    for sport in sports:
        sport_id = str(sport.get("sport", ""))
        tag_id = sport.get("primaryTagId")
        if not sport_id or tag_id is None:
            continue
        if sport_id in seen_sports:
            capture.duplicate_count += 1
            continue
        seen_sports.add(sport_id)
        capture.add(venue="polymarket", kind="sport", response=sports_response, payload=sport)
        _capture_polymarket_sport_events(
            client, capture, int(tag_id), sport_id, seen_events, seen_markets, max_pages=max_pages
        )
        processed += 1
        if max_sports is not None and processed >= max_sports:
            return


def _capture_polymarket_sport_events(
    client: PolymarketPublicClient,
    capture: Capture,
    tag_id: int,
    sport_id: str,
    seen_events: Set[str],
    seen_markets: Set[str],
    *,
    max_pages: int,
) -> None:
    cursor: Optional[str] = None
    seen_cursors: Set[str] = set()
    pages = 0
    while True:
        response = client.list_sports_events(tag_id, limit=100, after_cursor=cursor)
        capture.request_count += 1
        pages += 1
        payload = response.data
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise IngestionError("Polymarket events response has an unexpected shape")
        for event in payload["events"]:
            event_id = str(event.get("id", ""))
            if not event_id:
                raise IngestionError("Polymarket event is missing id")
            if event_id in seen_events:
                capture.duplicate_count += 1
                continue
            seen_events.add(event_id)
            capture.add(venue="polymarket", kind="event", response=response, payload=event, parent_id=sport_id)
            markets = event.get("markets", [])
            if not isinstance(markets, list):
                raise IngestionError("Polymarket event markets has an unexpected shape")
            for market in markets:
                market_id = str(market.get("id", ""))
                if not market_id:
                    raise IngestionError("Polymarket market is missing id")
                if market_id in seen_markets:
                    capture.duplicate_count += 1
                    continue
                seen_markets.add(market_id)
                capture.add(venue="polymarket", kind="market", response=response, payload=market, parent_id=event_id)
        cursor = _next_cursor(payload, "next_cursor")
        if not cursor:
            return
        if cursor in seen_cursors or pages >= max_pages:
            raise IngestionError(f"Polymarket event pagination did not terminate for {sport_id}")
        seen_cursors.add(cursor)


def write_capture(capture: Capture, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = root / f"sports-{stamp}.jsonl"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": capture.status,
        "errors": capture.errors,
        "request_count": capture.request_count,
        "record_count": len(capture.records),
        "duplicate_count": capture.duplicate_count,
    }
    fd, temp_name = tempfile.mkstemp(prefix=".capture-", suffix=".tmp", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"type": "manifest", **manifest}, ensure_ascii=False) + "\n")
            for record in capture.records:
                stream.write(json.dumps({"type": "record", **record}, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return target

