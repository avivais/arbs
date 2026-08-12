"""Sports catalog discovery and immutable JSONL snapshot storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.adapters.http import JsonResponse


class IngestionError(RuntimeError):
    pass


@dataclass
class Capture:
    records: List[Dict[str, Any]] = field(default_factory=list)
    request_count: int = 0
    duplicate_count: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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

    def error(self, venue: str, scope: str, exc: BaseException) -> None:
        self.errors.append({"venue": venue, "scope": scope, "error": f"{type(exc).__name__}: {exc}"})


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
    workers: int = 12,
) -> None:
    cursor: Optional[str] = None
    seen_cursors: Set[str] = set()
    series_seen = 0
    pages = 0
    discovered: List[tuple] = []
    limit_reached = False
    while True:
        response = client.list_series(category="Sports", limit=100, cursor=cursor)
        capture.request_count += 1
        pages += 1
        payload = response.data
        if not isinstance(payload, dict) or not isinstance(payload.get("series"), list):
            raise IngestionError("Kalshi series response has an unexpected shape")
        for series in payload["series"]:
            if max_series is not None and series_seen >= max_series:
                limit_reached = True
                break
            ticker = str(series.get("ticker", ""))
            if not ticker:
                raise IngestionError("Kalshi series is missing ticker")
            capture.add(venue="kalshi", kind="series", response=response, payload=series)
            discovered.append((ticker, series_seen))
            series_seen += 1
        if limit_reached:
            break
        cursor = _next_cursor(payload, "cursor")
        if not cursor:
            break
        if cursor in seen_cursors or pages >= max_pages:
            raise IngestionError("Kalshi series pagination did not terminate safely")
        seen_cursors.add(cursor)
    def fetch(ticker: str) -> Capture:
        child = Capture()
        try:
            _capture_kalshi_series_markets(client, child, ticker, max_pages=max_pages)
        except Exception as exc:
            child.error("kalshi", f"series:{ticker}", exc)
        return child
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fetch, ticker): (index, ticker) for ticker, index in discovered}
        completed = []
        for future in as_completed(futures):
            index, _ = futures[future]
            completed.append((index, future.result()))
    for _, child in sorted(completed):
        capture.records.extend(child.records)
        capture.request_count += child.request_count
        capture.duplicate_count += child.duplicate_count
        capture.errors.extend(child.errors)


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
    workers: int = 8,
) -> None:
    sports_response = client.list_sports()
    capture.request_count += 1
    sports = sports_response.data
    if not isinstance(sports, list):
        raise IngestionError("Polymarket sports response has an unexpected shape")
    seen_sports: Set[str] = set()
    seen_tags: Set[int] = set()
    seen_events: Set[str] = set()
    seen_markets: Set[str] = set()
    processed = 0
    discovered: List[tuple] = []
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
        numeric_tag = int(tag_id)
        if numeric_tag in seen_tags:
            capture.duplicate_count += 1
        else:
            seen_tags.add(numeric_tag)
            discovered.append((processed, numeric_tag, sport_id))
        processed += 1
        if max_sports is not None and processed >= max_sports:
            break
    def fetch(index: int, tag_id: int, sport_id: str) -> tuple:
        child = Capture()
        try:
            _capture_polymarket_sport_events(
                client, child, tag_id, sport_id, set(), set(), max_pages=max_pages
            )
        except Exception as exc:
            child.error("polymarket", f"sport:{sport_id}:tag:{tag_id}", exc)
        return index, child
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(fetch, *item) for item in discovered]
        completed = [future.result() for future in as_completed(futures)]
    global_event_ids: Set[str] = set()
    global_market_ids: Set[str] = set()
    for _, child in sorted(completed):
        capture.request_count += child.request_count
        capture.errors.extend(child.errors)
        for record in child.records:
            payload = record["payload"]
            identifier = str(payload.get("id", ""))
            target = global_event_ids if record["kind"] == "event" else global_market_ids
            if identifier and identifier in target:
                capture.duplicate_count += 1
                continue
            if identifier:
                target.add(identifier)
            capture.records.append(record)


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
            markets = event.get("markets", [])
            if not isinstance(markets, list):
                raise IngestionError("Polymarket event markets has an unexpected shape")
            event_without_markets = dict(event)
            event_without_markets.pop("markets", None)
            capture.add(venue="polymarket", kind="event", response=response, payload=event_without_markets, parent_id=sport_id)
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


def write_capture(capture: Capture, root: Path, *, complete: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = root / f"sports-{stamp}.jsonl"
    manifest = {
        "schema_version": 2,
        "status": "complete" if complete and not capture.errors else "partial",
        "started_at": capture.started_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request_count": capture.request_count,
        "record_count": len(capture.records),
        "duplicate_count": capture.duplicate_count,
        "error_count": len(capture.errors),
        "errors": capture.errors,
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


def load_capture(path: Path) -> Capture:
    """Load an existing snapshot so a later run can resume without losing records."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or rows[0].get("type") != "manifest":
        raise IngestionError("Resume file is missing a valid manifest")
    capture = Capture(
        records=[{key: value for key, value in row.items() if key != "type"} for row in rows[1:]],
        request_count=int(rows[0].get("request_count", 0)),
        duplicate_count=int(rows[0].get("duplicate_count", 0)),
        errors=list(rows[0].get("errors", [])),
        started_at=str(rows[0].get("started_at", rows[0].get("created_at"))),
    )
    return capture


def retry_failed_kalshi(client: KalshiPublicClient, capture: Capture, *, workers: int = 2) -> None:
    tickers = []
    retained_errors = []
    for error in capture.errors:
        scope = error.get("scope", "")
        if error.get("venue") == "kalshi" and scope.startswith("series:"):
            tickers.append(scope.split(":", 1)[1])
        else:
            retained_errors.append(error)
    capture.errors = retained_errors
    existing = {
        str(record["payload"].get("ticker"))
        for record in capture.records
        if record.get("venue") == "kalshi" and record.get("kind") == "market"
    }
    def fetch(ticker: str) -> Capture:
        child = Capture()
        try:
            _capture_kalshi_series_markets(client, child, ticker, max_pages=1000)
        except Exception as exc:
            child.error("kalshi", f"series:{ticker}", exc)
        return child
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fetch, ticker): ticker for ticker in sorted(set(tickers))}
        for future in as_completed(futures):
            child = future.result()
            capture.request_count += child.request_count
            capture.errors.extend(child.errors)
            for record in child.records:
                market_id = str(record["payload"].get("ticker"))
                if market_id in existing:
                    capture.duplicate_count += 1
                    continue
                existing.add(market_id)
                capture.records.append(record)
