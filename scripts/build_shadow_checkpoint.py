#!/usr/bin/env python3
"""Full empirical rebuild, deliberately separate from the bounded unit quality gate.

Replay with --cutoff from input_snapshot. Raw artifacts must remain immutable;
input metadata digests detect additions/replacements when comparing two rebuilds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from arbs.shadow_books import summarize
from arbs.shadow_movement import report
from arbs.shadow_validation import operational_evidence


def parse_cutoff(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("cutoff must include a timezone")
    return result.astimezone(timezone.utc)


def snapshot(directory: Path, cutoff: datetime, *, reports: bool = False) -> tuple[list[Path], dict]:
    """Freeze published inputs before any payload reads, excluding late publications."""
    since_epoch = cutoff - datetime(1970, 1, 1, tzinfo=timezone.utc)
    cutoff_ns = ((since_epoch.days * 86400 + since_epoch.seconds) * 1_000_000 + since_epoch.microseconds) * 1000
    entries = []
    with os.scandir(directory) as scan:
        for entry in scan:
            if not entry.name.endswith(".json") or (reports and not entry.name.startswith("20")):
                continue
            stat = entry.stat()
            if entry.is_file() and stat.st_mtime_ns <= cutoff_ns:
                entries.append((entry.name, stat.st_size, stat.st_mtime_ns))
    entries.sort()
    digest = hashlib.sha256()
    for row in entries:
        digest.update((json.dumps(row, separators=(",", ":")) + "\n").encode())
    return [directory / row[0] for row in entries], {
        "file_count": len(entries),
        "metadata_sha256": digest.hexdigest(),
    }


def atomic_write(output: Path, value: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # These are intentionally public, read-only evidence reports. mkstemp's
        # default 0600 would make the mounted Caddy preview return 403.
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books", type=Path, default=Path("data/shadow/books"))
    parser.add_argument("--reports", type=Path, default=Path("data/shadow"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/shadow-validation-checkpoint.json"))
    parser.add_argument("--cutoff", type=parse_cutoff, help="Inclusive publication mtime cutoff (timezone-aware ISO-8601); defaults to rebuild start")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    cutoff = args.cutoff or now
    if cutoff > now:
        parser.error("cutoff must not be in the future")
    book_paths, book_snapshot = snapshot(args.books, cutoff)
    report_paths, report_snapshot = snapshot(args.reports, cutoff, reports=True)
    print(f"Frozen inputs: {len(book_paths)} books, {len(report_paths)} reports; cutoff={cutoff.isoformat()}", flush=True)
    timing = summarize(book_paths, include_window=True)
    window = timing.pop("evidence_window")
    print("Timing complete", flush=True)
    movement = report(book_paths, include_transitions=False)
    print("Movement complete", flush=True)
    operations = operational_evidence(report_paths)
    # Detect replacements/deletions/backdated additions before publishing evidence.
    if snapshot(args.books, cutoff)[1] != book_snapshot or snapshot(args.reports, cutoff, reports=True)[1] != report_snapshot:
        raise RuntimeError("Frozen input metadata changed during rebuild; checkpoint not published")
    checkpoint = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_snapshot": {
            "cutoff": cutoff.isoformat(),
            "selection": "publication_mtime_ns_lte_cutoff",
            "replay_requires": "IMMUTABLE_INPUTS_WITH_PRESERVED_MTIME",
            "digest_scope": "SORTED_FILENAME_SIZE_MTIME_NS_NOT_CONTENT",
            "books": book_snapshot,
            "reports": report_snapshot,
        },
        "evidence_window": window,
        "timing": timing,
        "movement": {key: value for key, value in movement.items() if key != "transitions"},
        "operations": operations,
        "semantic_eligibility": "ALL_REVIEW_PRICING_DISABLED",
        "gate_status": "PARTIAL_EVIDENCE_ONLY",
    }
    atomic_write(args.output, checkpoint)
    print(json.dumps({"output": str(args.output), "movement": checkpoint["movement"], "operations": operations}, sort_keys=True))


if __name__ == "__main__":
    main()
