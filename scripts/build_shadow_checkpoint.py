#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from arbs.shadow_books import summarize
from arbs.shadow_movement import report
from arbs.shadow_validation import operational_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--books", type=Path, default=Path("data/shadow/books"))
parser.add_argument("--reports", type=Path, default=Path("data/shadow"))
parser.add_argument(
    "--output",
    type=Path,
    default=Path("data/reports/shadow-validation-checkpoint.json"),
)
args = parser.parse_args()
book_paths = sorted(args.books.glob("*.json"))
report_paths = sorted(args.reports.glob("20*.json"))
timing = summarize(book_paths)
movement = report(book_paths)
operations = operational_evidence(report_paths)
times = []
for path in book_paths:
    value = json.loads(path.read_text())
    if value.get("status") == "complete":
        times.append(datetime.fromisoformat(value["started_at"].replace("Z", "+00:00")))
checkpoint = {
    "schema_version": 1,
    "generated_at": datetime.now().astimezone().isoformat(),
    "evidence_window": {
        "first": min(times).isoformat() if times else None,
        "last": max(times).isoformat() if times else None,
        "elapsed_seconds": (max(times) - min(times)).total_seconds() if times else 0,
    },
    "timing": timing,
    "movement": {key: value for key, value in movement.items() if key != "transitions"},
    "operations": operations,
    "semantic_eligibility": "ALL_REVIEW_PRICING_DISABLED",
    "gate_status": "PARTIAL_EVIDENCE_ONLY",
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
print(
    json.dumps(
        {
            "movement": checkpoint["movement"],
            "operations": operations,
        },
        sort_keys=True,
    )
)
