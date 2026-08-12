"""CLI for read-only sports catalog captures."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.ingestion.snapshots import Capture, capture_kalshi, capture_polymarket, write_capture


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture public Kalshi and Polymarket sports catalogs")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-kalshi-series", type=int, default=None)
    parser.add_argument("--max-polymarket-sports", type=int, default=None)
    args = parser.parse_args(argv)
    capture = Capture(bounds={"max_kalshi_series": args.max_kalshi_series,
                              "max_polymarket_sports": args.max_polymarket_sports})
    for venue, operation in (("kalshi", lambda: capture_kalshi(KalshiPublicClient(), capture, max_series=args.max_kalshi_series)),
                             ("polymarket", lambda: capture_polymarket(PolymarketPublicClient(), capture, max_sports=args.max_polymarket_sports))):
        try:
            operation()
        except Exception as error:
            capture.fail(venue, error, venue=venue, operation="catalog_capture")
    target = write_capture(capture, args.output)
    counts = Counter((item["venue"], item["kind"]) for item in capture.records)
    print(json.dumps({
        "path": str(target), "requests": capture.request_count, "records": len(capture.records),
        "duplicates": capture.duplicate_count, "status": capture.status, "errors": capture.errors,
        "counts": {f"{venue}.{kind}": count for (venue, kind), count in sorted(counts.items())},
    }, indent=2))
    return {"complete": 0, "partial": 2, "failed": 3}[capture.status]


if __name__ == "__main__":
    raise SystemExit(main())

