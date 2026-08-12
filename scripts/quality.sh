#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests scripts
python3 scripts/render_rolling_plan.py --check
python3 - <<'PY'
from pathlib import Path
from arbs.ingestion.corpus import load_corpus
from arbs.replay import load_match_report
load_corpus(Path('tests/fixtures/replay/mlb-public-2026-08-12'))
report=load_match_report(Path('data/reports/live-mlb-matches.json'))
print(f"replay OK: {len(report['matches'])} matches")
PY
git diff --check
