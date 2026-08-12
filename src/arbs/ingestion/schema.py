"""Strict validation for versioned raw JSONL captures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SnapshotValidationError(ValueError):
    pass


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_snapshot(path: Path) -> dict[str, int | str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SnapshotValidationError("empty snapshot")
    manifest = json.loads(lines[0])
    if manifest.get("type") != "manifest" or manifest.get("schema_version") != 1:
        raise SnapshotValidationError("unsupported manifest schema")
    if manifest.get("status", "complete") not in {"complete", "partial", "failed"}:
        raise SnapshotValidationError("invalid capture status")
    records = [json.loads(line) for line in lines[1:]]
    if manifest.get("record_count") != len(records):
        raise SnapshotValidationError("record count mismatch")
    required = {"type", "venue", "kind", "source_url", "http_status", "request_elapsed_ms",
                "received_at_unix_ms", "sha256", "payload"}
    for index, record in enumerate(records):
        if required - record.keys() or record.get("type") != "record":
            raise SnapshotValidationError(f"invalid record {index}")
        if _hash(record["payload"]) != record["sha256"]:
            raise SnapshotValidationError(f"hash mismatch in record {index}")
    return {"schema_version": 1, "status": manifest.get("status", "complete"), "records": len(records)}
