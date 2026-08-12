"""Pinned, offline replay loading with integrity and schema checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ReplayError(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_match_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "generated_at", "scope", "counts", "matches", "report_sha256"}
    missing = required - data.keys()
    if missing:
        raise ReplayError(f"missing report fields: {sorted(missing)}")
    unsigned = {key: value for key, value in data.items() if key != "report_sha256"}
    if canonical_hash(unsigned) != data["report_sha256"]:
        raise ReplayError("report SHA-256 mismatch")
    if data["counts"].get("matched_events") != len(data["matches"]):
        raise ReplayError("matched-event count mismatch")
    for index, match in enumerate(data["matches"]):
        for key in ("decision", "pricing_eligible", "participants", "start_utc", "kalshi", "polymarket", "checks"):
            if key not in match:
                raise ReplayError(f"match {index} missing {key}")
    return data


def replay_matches(path: Path) -> list[dict[str, Any]]:
    """Return deterministic, source-linked matches without network access."""
    return load_match_report(path)["matches"]
