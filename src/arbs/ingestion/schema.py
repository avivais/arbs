"""Strict fail-closed validation for versioned raw JSONL captures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA = 1
VENUE_KINDS = {"kalshi": {"series", "market"}, "polymarket": {"sport", "event", "market"}}


class SnapshotValidationError(ValueError):
    pass


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(value: dict[str, Any], required: set[str], optional: set[str], label: str) -> None:
    missing, unknown = required - value.keys(), value.keys() - required - optional
    if missing or unknown:
        raise SnapshotValidationError(f"{label} fields invalid: missing={sorted(missing)} unknown={sorted(unknown)}")


def validate_snapshot(path: Path) -> dict[str, int | str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotValidationError("invalid snapshot encoding or JSON") from exc
    if not values or not isinstance(values[0], dict):
        raise SnapshotValidationError("empty or invalid snapshot")
    manifest = values[0]
    _exact_keys(manifest,
                {"type", "schema_version", "created_at", "started_at", "completed_at", "bounds", "status",
                 "errors", "request_count", "record_count", "duplicate_count"}, set(), "manifest")
    if manifest["type"] != "manifest" or manifest["schema_version"] != SUPPORTED_SCHEMA:
        raise SnapshotValidationError("unsupported manifest schema")
    if manifest["status"] not in {"complete", "partial", "failed"}:
        raise SnapshotValidationError("invalid capture status")
    if not all(isinstance(manifest[k], int) and manifest[k] >= 0 for k in ("request_count", "record_count", "duplicate_count")):
        raise SnapshotValidationError("invalid manifest counts")
    if not isinstance(manifest["bounds"], dict) or not isinstance(manifest["errors"], list):
        raise SnapshotValidationError("invalid bounds or errors")
    if manifest["status"] == "complete" and manifest["errors"]:
        raise SnapshotValidationError("complete capture cannot contain errors")
    if manifest["status"] != "complete" and not manifest["errors"]:
        raise SnapshotValidationError("partial/failed capture requires errors")
    error_fields = {"stage", "venue", "operation", "cursor", "reason_code", "error_type", "message"}
    for error in manifest["errors"]:
        if not isinstance(error, dict) or set(error) != error_fields or not error["reason_code"]:
            raise SnapshotValidationError("invalid capture error")
    records = values[1:]
    if manifest["record_count"] != len(records):
        raise SnapshotValidationError("record count mismatch")
    required = {"type", "record_schema_version", "venue", "kind", "parent_id", "source_url", "http_status",
                "request_elapsed_ms", "received_at_unix_ms", "sha256", "payload"}
    for index, record in enumerate(records):
        if not isinstance(record, dict): raise SnapshotValidationError(f"invalid record {index}")
        _exact_keys(record, required, set(), f"record {index}")
        venue, kind = record["venue"], record["kind"]
        if record["type"] != "record" or record["record_schema_version"] != SUPPORTED_SCHEMA:
            raise SnapshotValidationError(f"unsupported record schema {index}")
        if venue not in VENUE_KINDS or kind not in VENUE_KINDS[venue]:
            raise SnapshotValidationError(f"invalid venue/kind in record {index}")
        if not isinstance(record["source_url"], str) or not record["source_url"].startswith("https://"):
            raise SnapshotValidationError(f"invalid source URL in record {index}")
        if not isinstance(record["http_status"], int) or not 200 <= record["http_status"] < 300:
            raise SnapshotValidationError(f"invalid HTTP status in record {index}")
        if not isinstance(record["received_at_unix_ms"], int) or record["received_at_unix_ms"] < 0:
            raise SnapshotValidationError(f"invalid receipt time in record {index}")
        if _hash(record["payload"]) != record["sha256"]:
            raise SnapshotValidationError(f"hash mismatch in record {index}")
    if manifest["status"] == "failed" and records:
        raise SnapshotValidationError("failed capture cannot contain records")
    if manifest["status"] == "partial" and not records:
        raise SnapshotValidationError("partial capture requires records")
    return {"schema_version": SUPPORTED_SCHEMA, "status": manifest["status"], "records": len(records)}
