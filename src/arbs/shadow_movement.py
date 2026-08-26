"""Derived subsequent-movement report from immutable paired-book samples."""
from __future__ import annotations
import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _top(payload:dict[str,Any],venue:str)->tuple[Decimal|None,Decimal|None]:
 if venue=='polymarket':
  bids=[(Decimal(str(x['price'])),Decimal(str(x['size']))) for x in payload.get('bids',[]) if Decimal(str(x['size']))>0]
  asks=[(Decimal(str(x['price'])),Decimal(str(x['size']))) for x in payload.get('asks',[]) if Decimal(str(x['size']))>0]
  return (max((x[0] for x in bids),default=None),min((x[0] for x in asks),default=None))
 book=payload.get('orderbook_fp',{});yes=[(Decimal(str(x[0])),Decimal(str(x[1]))) for x in book.get('yes_dollars',[])];no=[(Decimal(str(x[0])),Decimal(str(x[1]))) for x in book.get('no_dollars',[])]
 bid=max((x[0] for x in yes if x[1]>0),default=None);ask=min((Decimal('1')-x[0] for x in no if x[1]>0),default=None)
 return bid,ask


def report(paths: list[Path], *, include_transitions: bool = True) -> dict[str, Any]:
    """Summarize movement in one pass, retaining at most one payload per pair.

    Shadow filenames begin with a sortable UTC capture timestamp. Sorting here makes
    callers deterministic and avoids retaining the full multi-day payload corpus in
    memory. Checkpoint generation does not need transition detail and can disable it.
    """
    previous: dict[str, dict[str, Any]] = {}
    pair_counts: dict[str, int] = {}
    failures = 0
    transition_count = 0
    changed_transition_count = 0
    top_quote_changed_transition_count = 0
    transitions: list[dict[str, Any]] = []
    for path in sorted(paths):
        current = json.loads(path.read_text())
        if current.get("status") != "complete":
            failures += 1
            continue
        pair_id = current["pair_id"]
        pair_counts[pair_id] = pair_counts.get(pair_id, 0) + 1
        before = previous.get(pair_id)
        previous[pair_id] = current
        if before is None:
            continue
        row = {
            "pair_id": pair_id,
            "before": before["started_at"],
            "after": current["started_at"],
            "venues": {},
        }
        transition_count += 1
        payload_changed = False
        top_quote_changed = False
        for venue in ("kalshi", "polymarket"):
            old_top = _top(before[venue]["payload"], venue)
            new_top = _top(current[venue]["payload"], venue)
            venue_changed = before[venue]["payload_sha256"] != current[venue]["payload_sha256"]
            venue_row = {
                "bid_before": str(old_top[0]) if old_top[0] is not None else None,
                "bid_after": str(new_top[0]) if new_top[0] is not None else None,
                "ask_before": str(old_top[1]) if old_top[1] is not None else None,
                "ask_after": str(new_top[1]) if new_top[1] is not None else None,
                "payload_changed": venue_changed,
            }
            row["venues"][venue] = venue_row
            payload_changed = payload_changed or venue_changed
            top_quote_changed = top_quote_changed or (
                venue_row["bid_before"] != venue_row["bid_after"]
                or venue_row["ask_before"] != venue_row["ask_after"]
            )
        changed_transition_count += int(payload_changed)
        top_quote_changed_transition_count += int(top_quote_changed)
        if include_transitions:
            transitions.append(row)
    return {
        "schema_version": 1,
        "pair_count": len(pair_counts),
        "successful_samples": sum(pair_counts.values()),
        "failure_count": failures,
        "transition_count": transition_count,
        "changed_transition_count": changed_transition_count,
        "top_quote_changed_transition_count": top_quote_changed_transition_count,
        "transitions": transitions,
    }
