"""Independent, fail-closed cross-check of identifiers retained in shadow matches.

This module deliberately does not reuse the live parser's title/rule normalization.  It
compares the date and participant tokens independently exposed by each venue's public
identifier.  Agreement is useful corroboration, but is not a human/independent label
and cannot satisfy the matching precision release gate by itself.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date
from typing import Any
from urllib.parse import urlparse

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
# Identifier tokens only.  This is intentionally separate from display-name aliases
# used by the production parser.
_KALSHI_TEAMS = {
    "AZ": "ARI", "ATH": "ATH", "ATL": "ATL", "BAL": "BAL", "BOS": "BOS",
    "CHC": "CHC", "CIN": "CIN", "CLE": "CLE", "COL": "COL", "CWS": "CWS",
    "DET": "DET", "HOU": "HOU", "KC": "KC", "LAA": "LAA", "LAD": "LAD",
    "MIA": "MIA", "MIL": "MIL", "MIN": "MIN", "NYM": "NYM", "NYY": "NYY",
    "PHI": "PHI", "PIT": "PIT", "SD": "SD", "SEA": "SEA", "SF": "SF",
    "STL": "STL", "TB": "TB", "TEX": "TEX", "TOR": "TOR", "WSH": "WSH",
}
_POLYMARKET_TEAMS = {
    **{value.lower(): value for value in set(_KALSHI_TEAMS.values())},
    "ari": "ARI",
    "oak": "ATH",
}
_KALSHI_RE = re.compile(
    r"^KXMLBGAME-(?P<year>\d{2})(?P<month>[A-Z]{3})(?P<day>\d{2})"
    r"(?P<time>\d{4})(?P<teams>[A-Z]+?)(?P<game>G[12])?$"
)
_POLYMARKET_RE = re.compile(
    r"^mlb-(?P<first>[a-z]+)-(?P<second>[a-z]+)-"
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$"
)


def _sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def decode_kalshi(event_id: str) -> dict[str, Any] | None:
    match = _KALSHI_RE.fullmatch(event_id)
    if match is None or match["month"] not in _MONTHS:
        return None
    token = match["teams"]
    splits = [
        (_KALSHI_TEAMS[token[:index]], _KALSHI_TEAMS[token[index:]])
        for index in range(1, len(token))
        if token[:index] in _KALSHI_TEAMS and token[index:] in _KALSHI_TEAMS
    ]
    if len(splits) != 1 or splits[0][0] == splits[0][1]:
        return None
    try:
        event_date = date(2000 + int(match["year"]), _MONTHS[match["month"]], int(match["day"]))
    except ValueError:
        return None
    return {
        "date": event_date.isoformat(),
        "participants": sorted(splits[0]),
        "game_number": int(match["game"][1]) if match["game"] else None,
    }


def decode_polymarket(source_url: str) -> dict[str, Any] | None:
    slug = urlparse(source_url).path.rstrip("/").split("/")[-1]
    match = _POLYMARKET_RE.fullmatch(slug)
    if match is None:
        return None
    teams = (_POLYMARKET_TEAMS.get(match["first"]), _POLYMARKET_TEAMS.get(match["second"]))
    if None in teams or teams[0] == teams[1]:
        return None
    try:
        event_date = date(int(match["year"]), int(match["month"]), int(match["day"]))
    except ValueError:
        return None
    return {"date": event_date.isoformat(), "participants": sorted(teams)}


def audit_match(match: dict[str, Any]) -> dict[str, Any]:
    kalshi_id = str(match["kalshi"]["event_id"])
    polymarket_id = str(match["polymarket"]["event_id"])
    kalshi = decode_kalshi(kalshi_id)
    polymarket = decode_polymarket(str(match["polymarket"]["source_url"]))
    reported = sorted(str(value) for value in match.get("participants", []))
    if kalshi is None or polymarket is None:
        status = "UNSUPPORTED_IDENTIFIER_FORMAT"
    elif kalshi["participants"] != polymarket["participants"]:
        status = "REVIEW_PARTICIPANT_IDENTIFIER_CONFLICT"
    elif kalshi["date"] != polymarket["date"]:
        status = "REVIEW_DATE_IDENTIFIER_CONFLICT"
    elif reported != kalshi["participants"]:
        status = "REVIEW_REPORTED_PARTICIPANT_CONFLICT"
    else:
        status = "IDENTIFIERS_CORROBORATE_EVENT"
    identity = {
        "kalshi_event_id": kalshi_id,
        "polymarket_event_id": polymarket_id,
        "polymarket_source_url": str(match["polymarket"]["source_url"]),
    }
    return {
        **identity,
        "evidence_sha256": _sha256(identity),
        "matcher_decision": str(match.get("decision", "UNKNOWN")),
        "pricing_eligible": False,
        "reported_participants": reported,
        "kalshi_identifier": kalshi,
        "polymarket_identifier": polymarket,
        "status": status,
    }


def audit_report(matches: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [audit_match(match) for match in matches]
    counts = Counter(row["status"] for row in rows)
    return {
        "schema_version": 1,
        "method": "AUTOMATED_INDEPENDENT_SOURCE_IDENTIFIER_CROSS_CHECK",
        "scope": "PARSER_AND_EVENT_IDENTITY_CORROBORATION_ONLY",
        "independent_label_gate_status": "NOT_SATISFIED_AUTOMATED_CHECK_IS_NOT_INDEPENDENT_REVIEW",
        "pricing_eligible": False,
        "match_count": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "audits": rows,
    }
