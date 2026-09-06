#!/usr/bin/env bash
# Full immutable-corpus evidence rebuild; intentionally NOT part of quality.sh.
# Optional replay: bash scripts/empirical_checkpoint.sh --cutoff <input_snapshot.cutoff>
# Exit 75 means another rebuild holds the lock; do not publish overlapping runs.
set -euo pipefail
umask 077
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONPATH=src
exec flock -n -E 75 "${TMPDIR:-/tmp}/arbs-empirical-checkpoint-${UID}.lock" \
  python3 scripts/build_shadow_checkpoint.py "$@"
