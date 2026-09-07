#!/usr/bin/env python3
"""Run from any directory; defaults to this repository's discovery artifact."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arbs.discovery_catalog import main

if __name__ == "__main__":
    args = sys.argv[1:]
    if not any(arg == "--output" or arg.startswith("--output=") for arg in args):
        args = ["--output", str(ROOT / "data/discovery/catalog-latest.json"), *args]
    raise SystemExit(main(args))
