"""Fail-closed audit of public cross-venue resolution evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable

from arbs.adapters.kalshi import KalshiPublicClient
from arbs.adapters.polymarket import PolymarketPublicClient
from arbs.source_identifier_audit import audit_match as audit_source_identifiers


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _poly_moneyline(event: dict[str, Any]) -> dict[str, Any] | None:
    rows = [x for x in event.get("markets", []) if x.get("sportsMarketType") == "moneyline"]
    return rows[0] if len(rows) == 1 else None


def unique_historical_matches(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain one source-linked row per cross-venue event across rolling reports.

    Resolution evidence becomes available after an event leaves the live catalog, so
    auditing only the newest discovery report would discard the events most likely
    to be final. Later representations win deterministically.
    """
    matches: dict[tuple[str, str], dict[str, Any]] = {}
    for report in reports:
        for match in report.get("matches", []):
            key = (
                str(match["kalshi"]["event_id"]),
                str(match["polymarket"]["event_id"]),
            )
            matches[key] = match
    return [matches[key] for key in sorted(matches)]


def audit_match(
    match: dict[str, Any],
    kalshi_get: Callable[[str], Any] | None = None,
    polymarket_get: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Compare only authoritative final venue outcomes; pending/ambiguous data stays UNKNOWN."""
    # Historical reports with source identifiers receive an independent identity
    # cross-check before any outcome comparison. A date/participant conflict may
    # represent a reschedule, but without independent review it cannot establish
    # post-resolution agreement and therefore remains fail-closed.
    if match.get("polymarket", {}).get("source_url"):
        identity = audit_source_identifiers(match)
        if identity["status"] != "IDENTIFIERS_CORROBORATE_EVENT":
            return {
                "kalshi_event_id": match["kalshi"]["event_id"],
                "polymarket_event_id": str(match["polymarket"]["event_id"]),
                "participants": match["participants"],
                "kalshi_status": "NOT_FETCHED_IDENTITY_REVIEW",
                "polymarket_status": "NOT_FETCHED_IDENTITY_REVIEW",
                "kalshi_outcome": None,
                "polymarket_outcome": None,
                "comparable": False,
                "agreement": None,
                "pricing_eligible": False,
                "identity_cross_check": identity["status"],
                "identity_evidence_sha256": identity["evidence_sha256"],
            }
    kalshi_get = kalshi_get or (lambda ticker: KalshiPublicClient().get_market(ticker).data)
    polymarket_get = polymarket_get or (lambda event_id: PolymarketPublicClient().get_event(event_id).data)
    k_contracts = match["kalshi"]["contracts"]
    k_payloads = [kalshi_get(x["id"])["market"] for x in k_contracts]
    p_event = polymarket_get(str(match["polymarket"]["event_id"]))
    p_market = _poly_moneyline(p_event)

    k_winners = [
        c["selected_team"] for c, payload in zip(k_contracts, k_payloads)
        if str(payload.get("result", "")).lower() == "yes"
    ]
    k_final = all(
        str(x.get("status", "")).lower() in {"settled", "closed", "finalized"}
        and x.get("result")
        for x in k_payloads
    )

    p_outcome = None
    p_final = False
    if p_market is not None:
        outcomes = json.loads(p_market.get("outcomes", "[]"))
        prices = json.loads(p_market.get("outcomePrices", "[]"))
        p_final = bool(p_market.get("closed")) and p_market.get("umaResolutionStatus") == "resolved"
        winners = [outcomes[i] for i, price in enumerate(prices) if str(price) == "1"] if len(outcomes) == len(prices) else []
        if p_final and len(winners) == 1:
            selected = {x["selected_team"]: x for x in match["polymarket"]["contracts"]}
            p_outcome = next((team for team, row in selected.items() if row.get("outcome") == winners[0]), None)
            if p_outcome is None:
                # Live reports currently retain team and token, while the event retains outcome order.
                teams = [x["selected_team"] for x in match["polymarket"]["contracts"]]
                p_outcome = teams[outcomes.index(winners[0])] if len(teams) == len(outcomes) else None

    k_outcome = k_winners[0] if k_final and len(k_winners) == 1 else None
    comparable = k_outcome is not None and p_outcome is not None
    return {
        "kalshi_event_id": match["kalshi"]["event_id"],
        "polymarket_event_id": str(match["polymarket"]["event_id"]),
        "participants": match["participants"],
        "kalshi_status": "FINAL" if k_outcome else "PENDING_OR_UNKNOWN",
        "polymarket_status": "FINAL" if p_outcome else "PENDING_OR_UNKNOWN",
        "kalshi_outcome": k_outcome,
        "polymarket_outcome": p_outcome,
        "comparable": comparable,
        "agreement": (k_outcome == p_outcome) if comparable else None,
        "pricing_eligible": False,
        "evidence_sha256": {"kalshi": _hash(k_payloads), "polymarket": _hash(p_event)},
    }


def audit_report(matches: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for match in matches:
        try:
            rows.append(audit_match(match))
        except Exception as exc:
            rows.append({
                "kalshi_event_id": match["kalshi"]["event_id"],
                "polymarket_event_id": str(match["polymarket"]["event_id"]),
                "status": "FETCH_FAILED",
                "error_type": type(exc).__name__,
                "comparable": False,
                "agreement": None,
                "pricing_eligible": False,
            })
    comparable = [x for x in rows if x.get("comparable")]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "match_count": len(rows),
        "comparable_count": len(comparable),
        "agreement_count": sum(x["agreement"] is True for x in comparable),
        "divergence_count": sum(x["agreement"] is False for x in comparable),
        "gate_status": "READY_FOR_REVIEW" if comparable else "AWAITING_BOTH_VENUE_FINALS",
        "pricing_eligible": False,
        "audits": rows,
    }