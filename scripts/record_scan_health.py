#!/usr/bin/env python3
"""Prospective per-run telemetry; never infer continuous service uptime."""
from __future__ import annotations
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def record(root: Path, run_id: str, phase: str, exit_code: int | None = None) -> dict:
    if phase not in {"started", "finished"} or not run_id.replace("T", "").replace("Z", "").isdigit():
        raise ValueError("invalid telemetry identity")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    value = json.loads(path.read_text()) if phase == "finished" and path.exists() else {
        "schema_version": 1, "run_id": run_id,
        "claim_scope": "SAMPLED_HOST_AND_SCAN_LIFECYCLE_NOT_CONTINUOUS_UPTIME",
    }
    now = datetime.now(timezone.utc).isoformat()
    value[phase] = {"observed_at": now, "monotonic_seconds": time.monotonic(),
                    "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    "host_uptime_seconds": float(Path('/proc/uptime').read_text().split()[0])}
    if phase == "finished":
        value["exit_code"] = exit_code
        value["status"] = "SUCCESS" if exit_code == 0 else "FAILED"
    else:
        value["status"] = "STARTED_WITHOUT_COMPLETION"
    temporary = path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)
    return value


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path('data/shadow/health'))
    p.add_argument('--run-id', required=True)
    p.add_argument('--phase', choices=['started', 'finished'], required=True)
    p.add_argument('--exit-code', type=int)
    a = p.parse_args()
    record(a.root, a.run_id, a.phase, a.exit_code)
