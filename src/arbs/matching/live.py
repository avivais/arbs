"""Read-only live matching for pre-game MLB winner markets.

This deliberately narrow vertical slice proves event-level overlap between Kalshi and
Polymarket. It does not claim resolution-rule equivalence or trading eligibility.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient

MLB_KALSHI_SERIES = "KXMLBGAME"
MLB_POLYMARKET_TAG = 100381
START_TOLERANCE_SECONDS = 15 * 60

# Canonical MLB identity, with source display variants observed in production.
_TEAM_ALIASES = {
    "arizona": "ARI", "arizona diamondbacks": "ARI",
    "athletics": "ATH", "oakland": "ATH", "oakland athletics": "ATH", "a's": "ATH",
    "atlanta": "ATL", "atlanta braves": "ATL",
    "baltimore": "BAL", "baltimore orioles": "BAL",
    "boston": "BOS", "boston red sox": "BOS",
    "chicago c": "CHC", "chicago cubs": "CHC",
    "chicago w": "CWS", "chicago ws": "CWS", "chicago white sox": "CWS",
    "cincinnati": "CIN", "cincinnati reds": "CIN",
    "cleveland": "CLE", "cleveland guardians": "CLE",
    "colorado": "COL", "colorado rockies": "COL",
    "detroit": "DET", "detroit tigers": "DET",
    "houston": "HOU", "houston astros": "HOU",
    "kansas city": "KC", "kansas city royals": "KC",
    "los angeles a": "LAA", "los angeles angels": "LAA",
    "los angeles d": "LAD", "los angeles dodgers": "LAD",
    "miami": "MIA", "miami marlins": "MIA",
    "milwaukee": "MIL", "milwaukee brewers": "MIL",
    "minnesota": "MIN", "minnesota twins": "MIN",
    "new york m": "NYM", "new york mets": "NYM",
    "new york y": "NYY", "new york yankees": "NYY",
    "philadelphia": "PHI", "philadelphia phillies": "PHI",
    "pittsburgh": "PIT", "pittsburgh pirates": "PIT",
    "san diego": "SD", "san diego padres": "SD",
    "san francisco": "SF", "san francisco giants": "SF",
    "seattle": "SEA", "seattle mariners": "SEA",
    "st. louis": "STL", "st louis": "STL", "st. louis cardinals": "STL",
    "tampa bay": "TB", "tampa bay rays": "TB",
    "texas": "TEX", "texas rangers": "TEX",
    "toronto": "TOR", "toronto blue jays": "TOR",
    "washington": "WSH", "washington nationals": "WSH",
}

_KALSHI_START_RE = re.compile(
    r"originally scheduled for (?P<month>[A-Z][a-z]{2}) (?P<day>\d{1,2}), "
    r"(?P<year>\d{4}) at (?P<hour>\d{1,2}):(?P<minute>\d{2}) (?P<ampm>AM|PM) "
    r"(?P<zone>EDT|EST)"
)


def _canonical_team(value: str) -> Optional[str]:
    key = re.sub(r"\s+", " ", value.strip().lower())
    return _TEAM_ALIASES.get(key)


def _participants(title: str) -> Optional[tuple[str, str]]:
    parts = re.split(r"\s+vs\.?\s+", title.replace(" Winner?", ""), maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    teams = (_canonical_team(parts[0]), _canonical_team(parts[1]))
    if None in teams or teams[0] == teams[1]:
        return None
    return tuple(sorted(teams))  # type: ignore[arg-type]


def _kalshi_start(market: dict[str, Any]) -> Optional[datetime]:
    text = f"{market.get('rules_primary', '')}\n{market.get('rules_secondary', '')}"
    match = _KALSHI_START_RE.search(text)
    if not match:
        return None
    raw = "{month} {day} {year} {hour}:{minute} {ampm}".format(**match.groupdict())
    local = datetime.strptime(raw, "%b %d %Y %I:%M %p").replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def _iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass(frozen=True)
class VenueEvent:
    venue: str
    event_id: str
    participants: tuple[str, str]
    start_utc: datetime
    title: str
    source_url: str
    contracts: tuple[dict[str, Any], ...]
    rules: str


@dataclass(frozen=True)
class MatchEvidence:
    decision: str
    pricing_eligible: bool
    sport: str
    competition: str
    participants: tuple[str, str]
    start_utc: str
    start_delta_seconds: int
    kalshi: dict[str, Any]
    polymarket: dict[str, Any]
    checks: tuple[dict[str, Any], ...]
    review_reasons: tuple[str, ...]


def normalize_kalshi(markets: Iterable[dict[str, Any]]) -> list[VenueEvent]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for market in markets:
        if market.get("status") not in {"active", "open"}:
            continue
        grouped.setdefault(str(market.get("event_ticker", "")), []).append(market)
    result: list[VenueEvent] = []
    for event_id, contracts in grouped.items():
        sample = contracts[0]
        participants, start = _participants(str(sample.get("title", ""))), _kalshi_start(sample)
        selected = {_canonical_team(str(item.get("yes_sub_title", ""))) for item in contracts}
        if not event_id or not participants or not start or set(participants) != selected:
            continue
        compact = tuple({
            "id": str(item["ticker"]), "selected_team": _canonical_team(str(item["yes_sub_title"])),
            "yes_bid": item.get("yes_bid_dollars"), "yes_ask": item.get("yes_ask_dollars"),
            "no_bid": item.get("no_bid_dollars"), "no_ask": item.get("no_ask_dollars"),
        } for item in sorted(contracts, key=lambda x: str(x["ticker"])))
        rules = "\n".join(filter(None, [sample.get("rules_primary"), sample.get("rules_secondary")]))
        result.append(VenueEvent("kalshi", event_id, participants, start, str(sample["title"]),
                                 f"https://kalshi.com/markets/{event_id.lower()}", compact, rules))
    return result


def normalize_polymarket(events: Iterable[dict[str, Any]]) -> list[VenueEvent]:
    result: list[VenueEvent] = []
    for event in events:
        if not event.get("active") or event.get("closed") or " - " in str(event.get("title", "")):
            continue
        participants = _participants(str(event.get("title", "")))
        if not participants or not event.get("endDate"):
            continue
        # The ungrouped event-winner market is the only MVP contract accepted here.
        candidates = [m for m in event.get("markets", []) if not m.get("groupItemTitle") and m.get("active") and not m.get("closed")]
        if len(candidates) != 1:
            continue
        market = candidates[0]
        try:
            outcomes = json.loads(market.get("outcomes", "[]"))
            prices = json.loads(market.get("outcomePrices", "[]"))
            tokens = json.loads(market.get("clobTokenIds", "[]"))
        except (TypeError, json.JSONDecodeError):
            continue
        canonical_outcomes = tuple(_canonical_team(str(x)) for x in outcomes)
        if set(canonical_outcomes) != set(participants) or len(tokens) != 2:
            continue
        contracts = tuple({"token_id": str(tokens[i]), "selected_team": canonical_outcomes[i],
                           "indicative_price": str(prices[i]), "best_bid": market.get("bestBid") if i == 0 else None,
                           "best_ask": market.get("bestAsk") if i == 0 else None}
                          for i in range(2))
        # Sports event endDate can be an administrative close date days after play.
        # gameStartTime on the moneyline contract is the canonical scheduled start.
        game_start = market.get("gameStartTime")
        if not game_start:
            continue
        slug = str(event.get("slug") or event.get("ticker"))
        result.append(VenueEvent("polymarket", str(event["id"]), participants, _iso_utc(str(game_start)),
                                 str(event["title"]), f"https://polymarket.com/event/{slug}", contracts,
                                 str(event.get("description") or market.get("description") or "")))
    return result


def match_events(kalshi: Iterable[VenueEvent], polymarket: Iterable[VenueEvent]) -> list[MatchEvidence]:
    poly_by_participants: dict[tuple[str, str], list[VenueEvent]] = {}
    for event in polymarket:
        poly_by_participants.setdefault(event.participants, []).append(event)
    matches: list[MatchEvidence] = []
    for k_event in kalshi:
        candidates = []
        for p_event in poly_by_participants.get(k_event.participants, []):
            delta = abs(int((k_event.start_utc - p_event.start_utc).total_seconds()))
            if delta <= START_TOLERANCE_SECONDS:
                candidates.append((delta, p_event))
        if len(candidates) != 1:
            continue
        delta, p_event = candidates[0]
        # Event identity is deterministic. Full payout equivalence remains REVIEW because
        # venue cancellation/postponement/fair-price behavior is materially different.
        reasons = ("MATERIAL_RULE_EQUIVALENCE_NOT_PROVEN", "VENUE_CANCELLATION_OR_POSTPONEMENT_RULES_DIFFER")
        checks = (
            {"code": "SPORT_EQUAL", "passed": True, "value": "baseball"},
            {"code": "COMPETITION_EQUAL", "passed": True, "value": "mlb"},
            {"code": "PARTICIPANTS_EQUAL", "passed": True, "value": list(k_event.participants)},
            {"code": "START_DELTA_WITHIN_15_MINUTES", "passed": True, "value": delta},
            {"code": "UNIQUE_CANDIDATE", "passed": True, "value": 1},
            {"code": "MATERIAL_RULES_EQUAL", "passed": False, "value": list(reasons)},
        )
        matches.append(MatchEvidence(
            "REVIEW", False, "baseball", "mlb", k_event.participants,
            k_event.start_utc.isoformat().replace("+00:00", "Z"), delta,
            {**asdict(k_event), "start_utc": k_event.start_utc.isoformat().replace("+00:00", "Z")},
            {**asdict(p_event), "start_utc": p_event.start_utc.isoformat().replace("+00:00", "Z")},
            checks, reasons,
        ))
    return sorted(matches, key=lambda item: (item.start_utc, item.participants))


def fetch_all_polymarket_events(client: PolymarketPublicClient, *, max_pages: int = 10) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cursor: Optional[str] = None
    seen: set[str] = set()
    # Keep each public response comfortably below the bounded HTTP client's 10 MB cap.
    # Gamma event payloads grew beyond that bound at limit=100 as nested markets expanded.
    for _ in range(max_pages):
        response = client.list_sports_events(MLB_POLYMARKET_TAG, limit=50, after_cursor=cursor)
        payload = response.data
        page = payload.get("events", []) if isinstance(payload, dict) else []
        events.extend(page)
        next_cursor = payload.get("next_cursor") if isinstance(payload, dict) else None
        if not next_cursor:
            return events
        cursor = str(next_cursor)
        if cursor in seen:
            raise RuntimeError("Polymarket pagination repeated a cursor")
        seen.add(cursor)
    raise RuntimeError("Polymarket pagination exceeded safety bound")


def live_mlb_matches() -> tuple[list[MatchEvidence], dict[str, int]]:
    kalshi_client, poly_client = KalshiPublicClient(), PolymarketPublicClient()
    k_payload = kalshi_client.list_series_markets(MLB_KALSHI_SERIES, limit=1000, status="open").data
    k_raw = k_payload.get("markets", []) if isinstance(k_payload, dict) else []
    p_raw = fetch_all_polymarket_events(poly_client)
    k_events, p_events = normalize_kalshi(k_raw), normalize_polymarket(p_raw)
    found = match_events(k_events, p_events)
    return found, {"kalshi_raw_markets": len(k_raw), "kalshi_normalized_events": len(k_events),
                   "polymarket_raw_events": len(p_raw), "polymarket_normalized_events": len(p_events),
                   "matched_events": len(found)}
