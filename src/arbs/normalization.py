"""Conservative canonical projection and coverage reporting for raw snapshots."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


FAMILY_PATTERNS = [
    ("HANDICAP", re.compile(r"\b(spread|handicap|run line|puck line)\b", re.I)),
    ("TOTAL", re.compile(r"\b(total|over|under)\b", re.I)),
    ("PLAYER_PROP", re.compile(r"\b(player|points|rebounds|assists|touchdowns|shots)\b", re.I)),
    ("STAGE_ADVANCEMENT", re.compile(r"\b(qualif|advance|reach the|playoffs|finals)\b", re.I)),
    ("AWARD", re.compile(r"\b(mvp|award|ballon d'or|gold glove)\b", re.I)),
    ("MULTIWAY_WINNER", re.compile(r"\b(champion|division winner|tournament winner|win the 20\d\d)\b", re.I)),
    ("HEAD_TO_HEAD", re.compile(r"\b(vs\.?|defeat|win the match|win the game|winner)\b", re.I)),
]


def parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def classify_family(text: str, explicit: Optional[str] = None) -> str:
    if explicit:
        normalized = explicit.upper().replace("-", "_").replace(" ", "_")
        if normalized:
            return normalized
    for family, pattern in FAMILY_PATTERNS:
        if pattern.search(text):
            return family
    return "OTHER"


def normalize_record(row: Dict[str, Any], parents: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row.get("kind") != "market":
        return None
    venue = row["venue"]
    p = row["payload"]
    parent = parents.get(f"{venue}:{row.get('parent_id')}", {})
    if venue == "kalshi":
        title = str(p.get("title") or "")
        series_title = str(parent.get("title") or "")
        tags = parent.get("tags") or []
        sport = str(tags[0]).lower() if tags else None
        rules = "\n".join(x for x in (p.get("rules_primary"), p.get("rules_secondary")) if x)
        return {
            "venue": venue, "market_id": p.get("ticker"), "event_id": p.get("event_ticker"),
            "container_id": row.get("parent_id"), "sport": sport, "competition": series_title or None,
            "title": title, "family": classify_family(f"{series_title} {title}"),
            "start_time": p.get("occurrence_datetime"), "close_time": p.get("close_time"),
            "live": bool(p.get("is_live", False)), "status": p.get("status"),
            "outcomes": ["Yes", "No"],
            "prices": {"yes_bid": p.get("yes_bid_dollars"), "yes_ask": p.get("yes_ask_dollars"),
                       "no_bid": p.get("no_bid_dollars"), "no_ask": p.get("no_ask_dollars")},
            "rules": rules or None, "resolution_source": parent.get("settlement_sources"),
            "source_hash": row.get("sha256"),
        }
    if venue == "polymarket":
        title = str(p.get("question") or "")
        sport_parent = parents.get(f"polymarket:{parent.get('_parent_id')}", {})
        return {
            "venue": venue, "market_id": p.get("id"), "event_id": row.get("parent_id"),
            "container_id": parent.get("ticker") or parent.get("slug"),
            "sport": sport_parent.get("sport"), "competition": sport_parent.get("name"),
            "title": title, "family": classify_family(title, p.get("sportsMarketType")),
            "start_time": p.get("gameStartTime") or parent.get("gameStartTime") or parent.get("startDate"),
            "close_time": p.get("endDate"), "live": bool(p.get("live", False)),
            "status": "active" if p.get("active") and not p.get("closed") else "closed",
            "outcomes": parse_jsonish(p.get("outcomes")),
            "prices": {"outcome_prices": parse_jsonish(p.get("outcomePrices")), "best_bid": p.get("bestBid"), "best_ask": p.get("bestAsk")},
            "rules": p.get("description") or parent.get("description"),
            "resolution_source": parent.get("resolutionSource") or sport_parent.get("resolution"),
            "source_hash": row.get("sha256"),
        }
    return None


def iter_normalized(path: Path) -> Iterable[Dict[str, Any]]:
    parents: Dict[str, Dict[str, Any]] = {}
    with path.open(encoding="utf-8") as stream:
        next(stream, None)
        for line in stream:
            row = json.loads(line)
            if row.get("kind") == "market":
                continue
            payload = dict(row.get("payload", {}))
            payload.pop("markets", None)
            payload["_parent_id"] = row.get("parent_id")
            if row.get("kind") == "sport":
                identifier = payload.get("sport")
            elif row.get("venue") == "polymarket":
                identifier = payload.get("id")
            else:
                identifier = payload.get("ticker")
            if identifier is not None:
                parents[f"{row.get('venue')}:{identifier}"] = payload
    with path.open(encoding="utf-8") as stream:
        next(stream, None)
        for line in stream:
            item = normalize_record(json.loads(line), parents)
            if item is not None:
                yield item


def load_and_normalize(path: Path) -> List[Dict[str, Any]]:
    return list(iter_normalized(path))


def coverage(markets: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    items = list(markets)
    by_venue = Counter(x["venue"] for x in items)
    families = Counter((x["venue"], x["family"]) for x in items)
    sports = defaultdict(set)
    missing = Counter()
    for item in items:
        if item.get("sport"):
            sports[item["venue"]].add(item["sport"])
        for field in ("sport", "competition", "title", "start_time", "close_time", "rules", "resolution_source"):
            if item.get(field) in (None, "", []):
                missing[(item["venue"], field)] += 1
    overlap = sorted(sports["kalshi"] & sports["polymarket"])
    return {
        "market_count": dict(sorted(by_venue.items())),
        "sports": {venue: sorted(values) for venue, values in sorted(sports.items())},
        "sport_overlap": overlap,
        "families": {f"{v}.{f}": n for (v, f), n in sorted(families.items())},
        "missing_fields": {f"{v}.{f}": n for (v, f), n in sorted(missing.items())},
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize and report a raw sports snapshot")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or args.snapshot.with_name(args.snapshot.stem + "-normalized.jsonl")
    markets = []
    with output.open("w", encoding="utf-8") as stream:
        for item in iter_normalized(args.snapshot):
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
            markets.append(item)
    report = coverage(markets)
    print(json.dumps({"normalized_path": str(output), **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
