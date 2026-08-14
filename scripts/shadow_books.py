#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from arbs.indicators import candidate_record, evaluate_candidate, leg_from_sample
from arbs.replay import load_match_report
from arbs.shadow_books import sample_pair, summarize


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def selected_pairs(report: dict, limit: int = 10) -> list[dict[str, str]]:
    """Select bounded, same-outcome venue pairs; never rely on venue array ordering."""
    selected: list[dict[str, str]] = []
    for match in report["matches"]:
        polymarket_by_team = {
            contract["selected_team"]: contract
            for contract in match["polymarket"].get("contracts", [])
            if contract.get("selected_team") and contract.get("token_id")
        }
        for kalshi in match["kalshi"].get("contracts", []):
            team = kalshi.get("selected_team")
            polymarket = polymarket_by_team.get(team)
            if not team or not kalshi.get("id") or not polymarket:
                continue
            selected.append(
                {
                    "event_id": match["kalshi"]["event_id"],
                    "team": team,
                    "kalshi_contract_id": kalshi["id"],
                    "polymarket_token_id": polymarket["token_id"],
                }
            )
            if len(selected) >= limit:
                return selected
    return selected


def polymarket_top(sample: dict) -> dict[str, str | None]:
    """Extract executable top-of-book prices without trusting payload ordering."""
    payload = sample.get("polymarket", {}).get("payload", {})
    bids = [float(level["price"]) for level in payload.get("bids", []) if level.get("price") is not None]
    asks = [float(level["price"]) for level in payload.get("asks", []) if level.get("price") is not None]
    return {
        "best_bid": str(max(bids)) if bids else None,
        "best_ask": str(min(asks)) if asks else None,
    }


def build_indicators(report: dict[str, Any], captured: list[tuple[dict[str, str], dict[str, Any]]], generated_at: datetime) -> dict[str, Any]:
    """Build both complementary cross-venue directions for each fully captured sports event."""
    samples = {(pair["event_id"], pair["team"]): (pair, sample) for pair, sample in captured if sample.get("status") == "complete"}
    matches = {match["kalshi"]["event_id"]: match for match in report.get("matches", [])}
    records = []
    for event_id in sorted({key[0] for key in samples}):
        match = matches.get(event_id)
        if match is None:
            continue
        teams = list(match.get("participants", []))
        if len(teams) != 2 or any((event_id, team) not in samples for team in teams):
            continue
        by_team = {team: samples[(event_id, team)] for team in teams}
        for kalshi_team, polymarket_team in ((teams[0], teams[1]), (teams[1], teams[0])):
            kalshi_pair, kalshi_sample = by_team[kalshi_team]
            polymarket_pair, polymarket_sample = by_team[polymarket_team]
            first = leg_from_sample(kalshi_sample, venue="kalshi", outcome=kalshi_team, instrument_id=kalshi_pair["kalshi_contract_id"])
            second = leg_from_sample(polymarket_sample, venue="polymarket", outcome=polymarket_team, instrument_id=polymarket_pair["polymarket_token_id"])
            record = candidate_record(evaluate_candidate(first, second, now=generated_at, reserve_per_pair=Decimal("0.01")))
            records.append({
                "sport": match.get("sport"), "competition": match.get("competition"),
                "event_id": event_id, "participants": teams, "start_utc": match.get("start_utc"),
                "kalshi_url": match["kalshi"].get("source_url"), "polymarket_url": match["polymarket"].get("source_url"),
                **record,
            })
    rank = {"OBSERVED_RESERVED_GAP": 0, "OBSERVED_RAW_GAP": 1, "UNAVAILABLE_FRESHNESS": 2, "NO_RAW_GAP": 3, "NO_DEPTH": 4}
    records.sort(key=lambda row: (rank.get(row["status"], 9), -float(row.get("gap_after_assumed_reserve_per_pair") or "-9"), row["event_id"]))
    return {
        "schema_version": 1, "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "scope": "Sports-only non-actionable normal-settlement complement-cost observations; no trading or account actions.",
        "method": {
            "directions": "Kalshi team YES plus opposing Polymarket outcome token",
            "quantity": "captured common depth capped at 1000 pairs; reserved-gap depth uses marginal combined asks",
            "reserve_per_pair": "0.01", "fees": "unverified_excluded",
            "pricing_eligible": False, "actionability": "NON_ACTIONABLE",
            "freshness_limits": {"quote_age_ms": 90000, "cross_leg_receipt_skew_ms": 800},
            "settlement": "REVIEW; exceptional settlement equivalence not proven",
        },
        "counts": {status: sum(row["status"] == status for row in records) for status in rank},
        "records": records,
    }


def main() -> None:
    root = Path("data/shadow/books")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = Path("data/shadow/latest.json") if Path("data/shadow/latest.json").exists() else Path("data/reports/live-mlb-matches.json")
    report = load_match_report(report_path)
    index_records = []
    captured = []

    pair_limit = int(os.environ.get("ARBS_SHADOW_PAIR_LIMIT", "10"))
    if pair_limit <= 0:
        raise ValueError("ARBS_SHADOW_PAIR_LIMIT must be positive")
    for pair in selected_pairs(report, limit=pair_limit):
        kalshi_id = pair["kalshi_contract_id"]
        output = root / f"{stamp}-{kalshi_id}.json"
        sample = sample_pair(kalshi_id, pair["polymarket_token_id"], output)
        captured.append((pair, sample))
        index_records.append(
            {
                **pair,
                "status": sample["status"],
                "polymarket_top": polymarket_top(sample),
                "receipt_skew_ms": sample.get("receipt_skew_ms"),
                "sample_url": f"books/{output.name}",
                "sampled_at": sample.get("started_at", stamp),
            }
        )

    atomic_json(
        Path("data/shadow/latest-books.json"),
        {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "scope": "Bounded same-outcome read-only samples; absence means not sampled, not an empty market.",
            "records": index_records,
        },
    )
    summary = summarize(sorted(root.glob("*.json")))
    atomic_json(Path("data/shadow/book-summary.json"), summary)
    generated_at = datetime.now(timezone.utc)
    atomic_json(Path("data/shadow/latest-indicators.json"), build_indicators(report, captured, generated_at))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
