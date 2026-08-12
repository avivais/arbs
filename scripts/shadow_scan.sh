#!/usr/bin/env bash
set -euo pipefail
ROOT=/root/.openclaw/workspace/repos/arbs
cd "$ROOT"
export PYTHONPATH=src
mkdir -p data/shadow
exec 9>data/arbs.lock
flock -n 9 || exit 0
stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp="data/shadow/.${stamp}.tmp"
PYTHONPATH=src python3 -m arbs.match_live --output "$tmp" >/dev/null
python3 - "$tmp" <<'PY'
import sys
from pathlib import Path
from arbs.replay import load_match_report
load_match_report(Path(sys.argv[1]))
PY
mv "$tmp" "data/shadow/${stamp}.json"
cp "data/shadow/${stamp}.json" data/shadow/latest.json
PYTHONPATH=src python3 scripts/shadow_books.py
find data/shadow -type f -name '*.json' ! -name latest.json -mtime +30 -delete
