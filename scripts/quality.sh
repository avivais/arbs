#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests scripts
python3 scripts/render_rolling_plan.py --check
python3 - <<'PY'
from pathlib import Path
from arbs.replay import load_match_report
r=load_match_report(Path('data/reports/live-mlb-matches.json'))
assert len(r['matches']) == r['counts']['matched_events']
print(f"replay OK: {len(r['matches'])} matches")
PY
git diff --check
