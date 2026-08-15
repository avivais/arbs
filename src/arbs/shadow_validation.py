"""Fail-closed operational evidence derived from immutable shadow scan reports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def operational_evidence(paths: list[Path], schedule_seconds: int = 300) -> dict[str, Any]:
    """Report artifact cadence and semantic eligibility without inferring service uptime.

    Artifact coverage is intentionally distinct from host/process uptime: missing artifacts
    identify unobserved scheduled slots, while present valid artifacts prove completed scans.
    """
    if schedule_seconds <= 0:
        raise ValueError("schedule_seconds must be positive")
    times: set[datetime] = set()
    invalid = 0
    successful = 0
    decisions: dict[str, str] = {}
    eligible_ids: set[str] = set()
    for path in paths:
        try:
            value = json.loads(path.read_text())
            when = _time(value["generated_at"])
            matches = value["matches"]
            if not isinstance(matches, list):
                raise ValueError("matches must be a list")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
            continue
        times.add(when)
        successful += 1
        for match in matches:
            key = f"{match['kalshi']['event_id']}|{match['polymarket']['event_id']}"
            decision = str(match.get("decision", "UNKNOWN"))
            previous = decisions.setdefault(key, decision)
            if previous != decision:
                decisions[key] = "DRIFT"
            if match.get("pricing_eligible") is True:
                eligible_ids.add(key)
    ordered = sorted(times)
    elapsed = (ordered[-1] - ordered[0]).total_seconds() if len(ordered) > 1 else 0.0
    expected = int(elapsed // schedule_seconds) + 1 if ordered else 0
    occupied_slots = (
        len({int((when - ordered[0]).total_seconds() // schedule_seconds) for when in ordered})
        if ordered
        else 0
    )
    gaps = [(after - before).total_seconds() for before, after in zip(ordered, ordered[1:])]
    counts: dict[str, int] = {}
    for decision in decisions.values():
        counts[decision] = counts.get(decision, 0) + 1
    coverage = occupied_slots / expected if expected else 0.0
    return {
        "schema_version": 1,
        "artifact_cadence": {
            "schedule_seconds": schedule_seconds,
            "first": ordered[0].isoformat() if ordered else None,
            "last": ordered[-1].isoformat() if ordered else None,
            "elapsed_seconds": elapsed,
            "valid_unique_reports": len(ordered),
            "successful_report_reads": successful,
            "invalid_report_count": invalid,
            "expected_slots_between_first_and_last": expected,
            "occupied_schedule_slots": occupied_slots,
            "observed_slot_coverage": coverage,
            "largest_observed_gap_seconds": max(gaps, default=0.0),
            "claim_scope": "ARTIFACT_COVERAGE_NOT_HOST_OR_PROCESS_UPTIME",
        },
        "decision_audit": {
            "unique_event_pairs": len(decisions),
            "decision_counts": dict(sorted(counts.items())),
            "pricing_eligible_pairs": len(eligible_ids),
            "theoretical_fill_count": 0,
            "modeled_net_result_status": (
                "NOT_COMPUTABLE_NO_PRICING_ELIGIBLE_PAIRS"
                if not eligible_ids
                else "NOT_COMPUTED"
            ),
        },
    }
