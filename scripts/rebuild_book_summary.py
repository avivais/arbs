#!/usr/bin/env python3
"""Rebuild cumulative paired-book timing statistics off the alert-critical path."""
from __future__ import annotations

import json
from pathlib import Path

from arbs.shadow_books import summarize


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    root = Path("data/shadow/books")
    summary = summarize(sorted(root.glob("*.json")))
    atomic_json(Path("data/shadow/book-summary.json"), summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
