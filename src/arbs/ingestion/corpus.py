"""Build and load immutable sanitized raw replay corpora."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1.0.0"


class CorpusError(ValueError):
    pass


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def source_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    return record["venue"], record["kind"], record["source_id"]


def write_corpus(root: Path, records: Iterable[dict[str, Any]], *, corpus_id: str, captured_at: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=source_identity)
    seen: set[tuple[str, str, str]] = set()
    normalized = []
    for record in ordered:
        identity = source_identity(record)
        if identity in seen:
            raise CorpusError(f"duplicate source identity: {identity}")
        seen.add(identity)
        item = dict(record)
        item["payload_sha256"] = canonical_hash(item["payload"])
        normalized.append(item)
    records_path = root / "records.jsonl"
    rendered = "".join(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n" for item in normalized)
    records_path.write_text(rendered, encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION, "corpus_id": corpus_id, "captured_at": captured_at,
        "redaction": {"status": "reviewed", "removed": [], "prohibited_fields_present": False},
        "record_count": len(normalized), "records_file": records_path.name,
        "records_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "counts": {f"{v}.{k}": sum(1 for r in normalized if r["venue"] == v and r["kind"] == k)
                   for v, k in sorted({(r["venue"], r["kind"]) for r in normalized})},
    }
    target = root / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_corpus(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CorpusError("unsupported corpus schema")
    if manifest.get("redaction") != {"status": "reviewed", "removed": [], "prohibited_fields_present": False}:
        raise CorpusError("corpus redaction declaration missing or unsafe")
    raw = (root / manifest["records_file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["records_sha256"]:
        raise CorpusError("records file SHA-256 mismatch")
    records = []
    seen = set()
    for index, line in enumerate(raw.decode().splitlines()):
        record = json.loads(line)
        required = {"venue", "kind", "source_id", "source_url", "received_at", "payload_sha256", "payload"}
        if required - record.keys():
            raise CorpusError(f"record {index} missing fields")
        if record["venue"] not in {"kalshi", "polymarket"} or not record["source_url"].startswith("https://"):
            raise CorpusError(f"record {index} invalid source")
        if canonical_hash(record["payload"]) != record["payload_sha256"]:
            raise CorpusError(f"record {index} payload hash mismatch")
        identity = source_identity(record)
        if identity in seen:
            raise CorpusError(f"duplicate source identity: {identity}")
        seen.add(identity); records.append(record)
    if records != sorted(records, key=source_identity) or len(records) != manifest["record_count"]:
        raise CorpusError("record ordering or count mismatch")
    counts = {f"{v}.{k}": sum(1 for r in records if r["venue"] == v and r["kind"] == k)
              for v, k in sorted({(r["venue"], r["kind"]) for r in records})}
    if counts != manifest["counts"]:
        raise CorpusError("venue/kind counts mismatch")
    return manifest, records
