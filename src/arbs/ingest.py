"""CLI for read-only sports catalog captures."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.ingestion.snapshots import Capture, capture_kalshi, capture_polymarket, load_capture, retry_failed_kalshi, write_capture


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture public Kalshi and Polymarket sports catalogs")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-kalshi-series", type=int, default=None)
    parser.add_argument("--max-polymarket-sports", type=int, default=None)
    parser.add_argument("--resume", type=Path, default=None, help="Preserve records from an earlier partial snapshot")
    parser.add_argument("--retry-errors", action="store_true", help="With --resume, fetch only failed containers")
    args = parser.parse_args(argv)
    capture = load_capture(args.resume) if args.resume else Capture()
    if args.retry_errors:
        if not args.resume:
            parser.error("--retry-errors requires --resume")
        retry_failed_kalshi(KalshiPublicClient(), capture)
    else:
        capture_kalshi(KalshiPublicClient(), capture, max_series=args.max_kalshi_series)
        capture_polymarket(PolymarketPublicClient(), capture, max_sports=args.max_polymarket_sports)
    target = write_capture(capture, args.output)
    counts = Counter((item["venue"], item["kind"]) for item in capture.records)
    print(json.dumps({
        "path": str(target), "requests": capture.request_count, "records": len(capture.records),
        "duplicates": capture.duplicate_count, "error_count": len(capture.errors),
        "error_sample": capture.errors[:10],
        "counts": {f"{venue}.{kind}": count for (venue, kind), count in sorted(counts.items())},
    }, indent=2))
    return 0 if not capture.errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
