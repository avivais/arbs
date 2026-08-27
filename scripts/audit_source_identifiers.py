#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from arbs.replay import load_match_report
from arbs.resolution_audit import unique_historical_matches
from arbs.source_identifier_audit import audit_report

parser = argparse.ArgumentParser()
parser.add_argument("--history", type=Path, default=Path("data/shadow"))
parser.add_argument(
    "--output",
    type=Path,
    default=Path("data/reports/source-identifier-audit.json"),
)
args = parser.parse_args()
reports = []
invalid_report_count = 0
for path in sorted(args.history.glob("20*.json")):
    try:
        reports.append(load_match_report(path))
    except (OSError, ValueError, json.JSONDecodeError):
        invalid_report_count += 1
value = audit_report(unique_historical_matches(reports))
value["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
value["report_count"] = len(reports)
value["invalid_report_count"] = invalid_report_count
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
print(json.dumps({key: value[key] for key in (
    "report_count", "invalid_report_count", "match_count", "status_counts",
    "independent_label_gate_status", "pricing_eligible",
)}, sort_keys=True))
