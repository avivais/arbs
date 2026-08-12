"""CLI for a bounded, read-only live cross-venue MLB matching checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arbs.matching import live_mlb_matches


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the audit report atomically")
    parser.add_argument("--require-match", action="store_true", help="fail when no event match is found")
    args = parser.parse_args()

    matches, counts = live_mlb_matches()
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "read_only",
        "scope": "live MLB pre-game event-winner markets",
        "eligibility_notice": "Event identity only; REVIEW matches are not pricing or trading eligible.",
        "counts": counts,
        "matches": [_jsonable(asdict(item)) for item in matches],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["report_sha256"] = hashlib.sha256(canonical).hexdigest()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)
    print(json.dumps({"counts": counts, "report_sha256": payload["report_sha256"],
                      "output": str(args.output) if args.output else None}, sort_keys=True))
    if args.require_match and not matches:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
