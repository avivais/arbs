#!/usr/bin/env bash
# Deterministic daily evidence refresh, no inference, trading, or gate promotion.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
export PYTHONPATH=src
mkdir -p data/shadow/validation
exec 9>data/validation.lock
flock -n 9 || { printf 'Validation refresh already running\n'; exit 0; }
stage=$(mktemp -d data/shadow/validation/.stage.XXXXXX)
trap 'rm -rf "$stage"' EXIT
python3 scripts/build_shadow_checkpoint.py --output "$stage/checkpoint.json"
python3 scripts/audit_resolutions.py --output "$stage/resolutions.json"
python3 - "$stage" <<'PY'
import json, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
stage=Path(sys.argv[1])
checkpoint=json.loads((stage/'checkpoint.json').read_text())
resolutions=json.loads((stage/'resolutions.json').read_text())
assert checkpoint['semantic_eligibility']=='ALL_REVIEW_PRICING_DISABLED'
assert resolutions['pricing_eligible'] is False
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
manifest={'schema_version':1,'generated_at':stamp,'status':'REFRESHED_NOT_RELEASE_APPROVAL',
          'checkpoint_generated_at':checkpoint['generated_at'],
          'resolution_generated_at':resolutions['generated_at'],
          'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.glob('*.json')}}
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
destination=stage.parent/stamp
stage.rename(destination)
latest=destination.parent/'latest.json'
tmp=latest.with_suffix('.tmp')
tmp.write_text(json.dumps({'generation':stamp,**manifest},indent=2)+'\n')
tmp.replace(latest)
print(f'Evidence refreshed: {destination}; read-only eligibility unchanged.')
PY
