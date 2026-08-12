#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests scripts
python3 scripts/render_rolling_plan.py --check
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from arbs.decision_evidence import build
from arbs.ingestion.corpus import load_corpus
from arbs.replay import load_match_report
load_corpus(Path('tests/fixtures/replay/mlb-public-2026-08-12'))
report=load_match_report(Path('data/reports/live-mlb-matches.json'))
evidence=build(Path('tests/fixtures/replay/mlb-public-2026-08-12'))
assert evidence['counts']=={'records':175,'parse_decisions':137,'matches':38,'unpaired':61}
print(f"replay OK: {len(report['matches'])} published matches; {evidence['counts']['matches']} raw-replay matches")
PY
git diff --check
