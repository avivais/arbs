#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

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


def main() -> None:
    root = Path("data/shadow/books")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = Path("data/shadow/latest.json") if Path("data/shadow/latest.json").exists() else Path("data/reports/live-mlb-matches.json")
    report = load_match_report(report_path)
    index_records = []

    for pair in selected_pairs(report):
        kalshi_id = pair["kalshi_contract_id"]
        output = root / f"{stamp}-{kalshi_id}.json"
        sample = sample_pair(kalshi_id, pair["polymarket_token_id"], output)
        index_records.append(
            {
                **pair,
                "status": sample["status"],
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
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
