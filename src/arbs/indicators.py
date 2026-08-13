"""Read-only sports price-dislocation indicators from captured public books.

These calculations deliberately remain separate from execution eligibility.  They expose
executable gross cross-venue price relationships while contract settlement equivalence and
venue-specific fee schedules remain under review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from arbs.pricing import Level, normalize_levels, walk


ONE = Decimal("1")


@dataclass(frozen=True)
class IndicatorLeg:
    venue: str
    outcome: str
    instrument_id: str
    asks: tuple[Level, ...]
    received_at: datetime


@dataclass(frozen=True)
class Candidate:
    status: str
    quantity: Decimal
    first: IndicatorLeg
    second: IndicatorLeg
    first_cost: Decimal
    second_cost: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    reserve: Decimal
    provisional_profit: Decimal
    pair_skew_ms: int
    quote_age_ms: int


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return result.astimezone(timezone.utc)


def kalshi_yes_asks(sample: dict[str, Any]) -> tuple[Level, ...]:
    """Kalshi exposes NO bids; each creates a YES ask at 1 - NO bid."""
    raw = sample["kalshi"]["payload"]["orderbook_fp"].get("no_dollars", [])
    return normalize_levels((str(ONE - Decimal(str(price))), str(quantity)) for price, quantity in raw)


def polymarket_asks(sample: dict[str, Any]) -> tuple[Level, ...]:
    raw = sample["polymarket"]["payload"].get("asks", [])
    return normalize_levels((str(level["price"]), str(level["size"])) for level in raw)


def leg_from_sample(sample: dict[str, Any], *, venue: str, outcome: str, instrument_id: str) -> IndicatorLeg:
    if sample.get("status") != "complete":
        raise ValueError("sample is not complete")
    source = sample[venue]
    asks = kalshi_yes_asks(sample) if venue == "kalshi" else polymarket_asks(sample)
    return IndicatorLeg(venue, outcome, instrument_id, asks, utc(source["received_at"]))


def _candidate_quantity(first: IndicatorLeg, second: IndicatorLeg, reserve_per_pair: Decimal) -> Decimal:
    """Maximum quantity whose next matched marginal unit survives the reserve."""
    i = j = 0
    left = first.asks[0].quantity if first.asks else Decimal("0")
    right = second.asks[0].quantity if second.asks else Decimal("0")
    quantity = Decimal("0")
    while i < len(first.asks) and j < len(second.asks):
        if first.asks[i].price + second.asks[j].price + reserve_per_pair >= ONE:
            break
        amount = min(left, right)
        quantity += amount
        left -= amount
        right -= amount
        if left == 0:
            i += 1
            if i < len(first.asks):
                left = first.asks[i].quantity
        if right == 0:
            j += 1
            if j < len(second.asks):
                right = second.asks[j].quantity
    return quantity


def evaluate_candidate(
    first: IndicatorLeg,
    second: IndicatorLeg,
    *,
    now: datetime,
    reserve_per_pair: Decimal = Decimal("0.01"),
    max_quote_age_ms: int = 90_000,
    max_cross_leg_skew_ms: int = 800,
) -> Candidate:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    receipts = (first.received_at, second.received_at)
    age = max(0, max(int((now.astimezone(timezone.utc) - value).total_seconds() * 1000) for value in receipts))
    skew = abs(int((receipts[0] - receipts[1]).total_seconds() * 1000))
    if not first.asks or not second.asks:
        return Candidate(
            "NO_DEPTH", Decimal("0"), first, second,
            Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"),
            skew, age,
        )
    top_quantity = min(first.asks[0].quantity, second.asks[0].quantity)
    top_combined = first.asks[0].price + second.asks[0].price
    buffered_quantity = _candidate_quantity(first, second, reserve_per_pair)
    quantity = buffered_quantity if buffered_quantity > 0 else top_quantity
    left, right = walk(first.asks, quantity), walk(second.asks, quantity)
    first_cost, second_cost = left.cost, right.cost
    cost = first_cost + second_cost
    gross = quantity - cost
    reserve = reserve_per_pair * quantity
    provisional = gross - reserve
    if buffered_quantity > 0:
        status = "BUFFERED_CANDIDATE"
    elif top_combined < ONE:
        status = "GROSS_ONLY"
    else:
        status = "NO_EDGE"
    if status in {"BUFFERED_CANDIDATE", "GROSS_ONLY"} and (age > max_quote_age_ms or skew > max_cross_leg_skew_ms):
        status = "STALE_OR_SKEWED"
    return Candidate(status, quantity, first, second, first_cost, second_cost, cost, gross, reserve, provisional, skew, age)


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def candidate_record(candidate: Candidate) -> dict[str, Any]:
    quantity = candidate.quantity
    return {
        "status": candidate.status,
        "settlement_status": "REVIEW",
        "fee_status": "EXCLUDED_UNVERIFIED",
        "quantity": decimal_text(quantity),
        "legs": [
            {
                "venue": leg.venue,
                "outcome": leg.outcome,
                "instrument_id": leg.instrument_id,
                "best_ask": decimal_text(leg.asks[0].price) if leg.asks else None,
                "vwap": decimal_text(cost / quantity) if quantity else None,
                "received_at": leg.received_at.isoformat().replace("+00:00", "Z"),
            }
            for leg, cost in ((candidate.first, candidate.first_cost), (candidate.second, candidate.second_cost))
        ],
        "combined_vwap": decimal_text(candidate.total_cost / quantity) if quantity else None,
        "gross_edge_per_pair": decimal_text(candidate.gross_profit / quantity) if quantity else None,
        "gross_profit": decimal_text(candidate.gross_profit),
        "reserve_per_pair": decimal_text(candidate.reserve / quantity) if quantity else None,
        "reserve_total": decimal_text(candidate.reserve),
        "provisional_edge_per_pair": decimal_text(candidate.provisional_profit / quantity) if quantity else None,
        "provisional_profit": decimal_text(candidate.provisional_profit),
        "quote_age_ms_at_generation": candidate.quote_age_ms,
        "cross_leg_receipt_skew_ms": candidate.pair_skew_ms,
    }
