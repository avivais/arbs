"""Bounded, read-only public event/market discovery (not execution eligibility).

The latest artifact is also the pagination checkpoint. Each generation samples
only newly fetched pages, not a cumulative or exhaustive exchange catalog.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import ssl
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

import certifi

ENDPOINTS = {
    "kalshi": "https://api.elections.kalshi.com/trade-api/v2/events",
    "polymarket": "https://gamma-api.polymarket.com/events/keyset",
}
CATEGORIES = ("economics", "politics", "crypto", "sports", "other")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json(url, *, timeout=15.0, retries=2):
    """GET only; bounded attempts, per-socket timeout and response size."""
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "arbs-readonly-catalog/1.0", "Accept": "application/json"})
            with urlopen(request, timeout=timeout, context=ssl.create_default_context(cafile=certifi.where())) as response:
                body = response.read(32 * 1024 * 1024 + 1)
                if len(body) > 32 * 1024 * 1024:
                    raise ValueError("response exceeds 32 MiB limit")
                return json.loads(body)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt == retries:
                raise
        time.sleep(min(2 ** attempt, 4))


def _array(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError("expected outcome array")
    return value


def category_for(event):
    """Source-category/tag mapping, never an assertion of settlement identity."""
    labels = {str(event.get("category", "")).lower()}
    labels.update(str(t.get("label", "")).lower() for t in event.get("tags", []) if isinstance(t, dict))
    mapping = {
        "crypto": {"crypto", "cryptocurrency", "bitcoin", "ethereum"},
        "sports": {"sports", "soccer", "nba", "nfl", "mlb", "nhl", "tennis", "esports"},
        "politics": {"politics", "elections", "us politics", "geopolitics"},
        "economics": {"economics", "economy", "financials", "finance", "business", "fed", "inflation"},
    }
    for category, aliases in mapping.items():
        if labels & aliases:
            return category
    return "other"


def normalize_market(venue, market, event, source_url, received_at):
    if venue == "kalshi":
        identifier = market.get("ticker")
        title = market.get("title")
        rules = "\n\n".join(str(market[k]) for k in ("rules_primary", "rules_secondary") if market.get(k))
        description = market.get("subtitle") or event.get("sub_title") or ""
        url = f"https://kalshi.com/markets/{quote(str(event.get('series_ticker', identifier)), safe='').lower()}/{quote(str(event.get('event_ticker', identifier)), safe='').lower()}"
        outcomes = ["Yes", "No"] if market.get("market_type", "binary") == "binary" else []
        close_time = market.get("close_time")
        sources = event.get("settlement_sources", [])
    else:
        identifier = market.get("id")
        title = market.get("question")
        description = market.get("description") or event.get("description") or ""
        rules = description  # Gamma publishes resolution rules in description.
        url = "https://polymarket.com/event/" + quote(str(event.get("slug") or market.get("slug") or identifier), safe="")
        outcomes = _array(market.get("outcomes", []))
        close_time = market.get("endDate") or event.get("endDate")
        sources = [{"url": market.get("resolutionSource") or event.get("resolutionSource")}]
        sources = [s for s in sources if s["url"]]
    if not identifier or not title:
        raise ValueError("missing market identity/title")
    return {
        "venue": venue, "id": str(identifier), "title": title,
        "category": category_for(event), "description": description, "rules": rules,
        "url": url, "close_time": close_time, "outcomes": outcomes,
        "source_url": source_url, "received_at": received_at,
        "source_excerpt": rules[:2000], "settlement_sources": sources,
        "rules_available": bool(rules), "category_method": "source_category_or_tags_v1",
        "raw": market,
        "raw_event": {k: v for k, v in event.items() if k != "markets"},
    }


def _balanced_sample(markets, limit):
    buckets = {c: deque() for c in CATEGORIES}
    for market in markets:
        buckets[market["category"]].append(market)
    result = []
    while len(result) < limit and any(buckets.values()):
        for category in CATEGORIES:
            if buckets[category] and len(result) < limit:
                result.append(buckets[category].popleft())
    return result


def collect_venue(venue, *, limit=1000, max_pages=10, page_size=100,
                  position=None, fetch=fetch_json):
    position = position if isinstance(position, str) else ""
    start = position
    coverage = {
        "endpoint": ENDPOINTS[venue], "requested_market_limit": limit,
        "max_pages": max_pages, "page_size_events": page_size,
        "start_position": start, "next_position": start, "pages_fetched": 0,
        "events_fetched": 0, "raw_markets_seen": 0, "inactive_markets_skipped": 0,
        "invalid_markets": 0, "duplicates": 0, "errors": [], "page_urls": [],
        "end_of_catalog_reached": False, "total_venue_markets": None,
        "complete_catalog": False,
        "scope": "active/open events; active nonclosed nested markets; rotating bounded pages",
        "sampling": "round-robin source categories within fetched pages; unsampled rows not retained",
        "pagination_caveat": "Live listings can change between pages/runs; offset/cursor traversal is not a frozen snapshot.",
    }
    candidates = {}
    for _ in range(max_pages):
        params: dict[str, object] = {"limit": page_size}
        if venue == "kalshi":
            params.update(status="open", with_nested_markets="true")
            if position:
                params["cursor"] = position
        else:
            params.update(active="true", closed="false")
            if position:
                params["after_cursor"] = position
        url = ENDPOINTS[venue] + "?" + urlencode(params)
        try:
            payload = fetch(url)
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list) or any(not isinstance(e, dict) or not isinstance(e.get("markets"), list) for e in events):
                raise ValueError("malformed events response")
            if venue == "kalshi" and ("cursor" not in payload or not isinstance(payload["cursor"], str)):
                raise ValueError("missing/invalid pagination cursor")
            if venue == "polymarket" and ("next_cursor" not in payload or payload["next_cursor"] is not None and not isinstance(payload["next_cursor"], str)):
                raise ValueError("missing/invalid keyset cursor")
        except Exception as exc:
            coverage["errors"].append({"url": url, "type": type(exc).__name__, "message": str(exc)[:500]})
            break  # retain last successful cursor, so the failed page is retried next run
        received = utc_now()
        coverage["pages_fetched"] += 1
        coverage["page_urls"].append(url)
        coverage["events_fetched"] += len(events)
        for event in events:
            for market in event["markets"]:
                coverage["raw_markets_seen"] += 1
                if not isinstance(market, dict):
                    coverage["invalid_markets"] += 1
                    continue
                active = market.get("status") in ("active", "open") if venue == "kalshi" else market.get("active") is True and market.get("closed") is False
                if not active:
                    coverage["inactive_markets_skipped"] += 1
                    continue
                try:
                    normalized = normalize_market(venue, market, event, url, received)
                except (ValueError, TypeError, KeyError) as exc:
                    coverage["invalid_markets"] += 1
                    continue
                key = normalized["id"]
                if key in candidates:
                    coverage["duplicates"] += 1
                candidates[key] = normalized
        next_position = payload["cursor"] if venue == "kalshi" else payload.get("next_cursor", "")
        exhausted = not next_position
        if exhausted:
            position = ""
            coverage["end_of_catalog_reached"] = True
        elif next_position == position:
            coverage["errors"].append({"url": url, "type": "PaginationError", "message": "nonadvancing cursor"})
        else:
            position = next_position
        coverage["next_position"] = position
        if exhausted or coverage["errors"]:
            break
    sampled = _balanced_sample(candidates.values(), limit)
    coverage.update(
        unique_active_markets_seen=len(candidates), markets_returned=len(sampled),
        sampled_out=len(candidates) - len(sampled),
        category_counts=dict(Counter(m["category"] for m in sampled)),
        missing_categories=[c for c in CATEGORIES if not any(m["category"] == c for m in sampled)],
        rules_missing=sum(not m["rules_available"] for m in sampled),
        status="partial_error" if coverage["errors"] else "ok",
    )
    return sampled, coverage


def atomic_json(path, payload, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def discover(output="data/discovery/catalog-latest.json", *, limit=1000,
             max_pages=10, page_size=100, reset=False, fetch=fetch_json):
    if limit < 1 or not 1 <= max_pages <= 100 or not 1 <= page_size <= 100:
        raise ValueError("limit must be positive; max_pages/page_size must be 1..100")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = {}
        if path.exists() and not reset:
            previous = json.loads(path.read_text()).get("coverage", {})
        result = {"schema_version": 1, "generated_at": utc_now(), "coverage": {}, "markets": [],
                  "read_only": True, "actionability": "Catalog discovery only; no equivalence, executable-price or trading claim."}
        for venue in ENDPOINTS:
            rows, coverage = collect_venue(venue, limit=limit, max_pages=max_pages,
                page_size=page_size, position=previous.get(venue, {}).get("next_position"), fetch=fetch)
            result["markets"].extend(rows)
            result["coverage"][venue] = coverage
        result["generated_at"] = utc_now()
        if not any(c["pages_fetched"] for c in result["coverage"].values()):
            raise RuntimeError("No venue pages fetched; previous latest preserved: " + json.dumps(result["coverage"]))
        atomic_json(path, result)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/discovery/catalog-latest.json")
    parser.add_argument("--limit", type=int, default=1000, help="maximum normalized markets per venue")
    parser.add_argument("--max-pages", type=int, default=10, help="maximum event pages per venue")
    parser.add_argument("--page-size", type=int, default=100, help="events per page (1..100)")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--reset-cursor", action="store_true")
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 60 or not 0 <= args.retries <= 5:
        parser.error("timeout must be (0,60]; retries must be 0..5")
    result = discover(args.output, limit=args.limit, max_pages=args.max_pages,
        page_size=args.page_size, reset=args.reset_cursor,
        fetch=lambda url: fetch_json(url, timeout=args.timeout, retries=args.retries))
    print(json.dumps({"generated_at": result["generated_at"], "output": args.output,
                      "markets": len(result["markets"]), "coverage": result["coverage"]}, indent=2))
    return 2 if any(c["errors"] for c in result["coverage"].values()) else 0
