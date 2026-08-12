"""Conservative normalized order books and read-only opportunity calculations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_UP
from typing import Iterable

from arbs.domain import decimal_exact


@dataclass(frozen=True)
class Level:
    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        if not (Decimal("0") < self.price <= Decimal("1")) or self.quantity <= 0:
            raise ValueError("invalid price level")


@dataclass(frozen=True)
class Book:
    venue: str
    contract_id: str
    outcome: str
    asks: tuple[Level, ...]
    received_at: datetime
    source_at: datetime | None = None
    tick_size: Decimal = Decimal("0.01")
    sequence: str | None = None
    payout: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if self.tick_size <= 0 or self.payout != Decimal("1"):
            raise ValueError("book must use a positive tick and $1 payout model")


@dataclass(frozen=True)
class Fill:
    quantity: Decimal
    cost: Decimal
    vwap: Decimal


@dataclass(frozen=True)
class FeeModel:
    rate: Decimal
    minimum: Decimal = Decimal("0")
    increment: Decimal = Decimal("0.0001")
    version: str = "generic-1"
    effective_at: str = "1970-01-01T00:00:00Z"
    settlement_cost: Decimal = Decimal("0")
    withdrawal_cost: Decimal = Decimal("0")

    def fee(self, notional: Decimal) -> Decimal:
        raw = max(self.minimum, notional * self.rate) + self.settlement_cost + self.withdrawal_cost
        return raw.quantize(self.increment, rounding=ROUND_UP)


@dataclass(frozen=True)
class Opportunity:
    eligible: bool
    reason: str
    quantity: Decimal
    total_cost: Decimal
    gross_payout: Decimal
    total_fees: Decimal
    safety_buffer: Decimal
    net_profit: Decimal
    quote_age_ms: int
    pair_skew_ms: int


def normalize_levels(raw: Iterable[tuple[object, object]]) -> tuple[Level, ...]:
    levels = [Level(decimal_exact(price), decimal_exact(quantity)) for price, quantity in raw]
    return tuple(sorted(levels, key=lambda level: level.price))


def walk(asks: tuple[Level, ...], requested: Decimal) -> Fill:
    if requested <= 0:
        raise ValueError("requested quantity must be positive")
    remaining, cost = requested, Decimal("0")
    for level in asks:
        amount = min(remaining, level.quantity)
        cost += amount * level.price
        remaining -= amount
        if remaining == 0:
            break
    filled = requested - remaining
    if filled <= 0:
        return Fill(Decimal("0"), Decimal("0"), Decimal("0"))
    return Fill(filled, cost, cost / filled)


def common_depth(*books: Book) -> Decimal:
    if not books:
        return Decimal("0")
    return min(sum((level.quantity for level in book.asks), Decimal("0")) for book in books)


def price_pair(
    first: Book,
    second: Book,
    *,
    semantic_pricing_eligible: bool,
    now: datetime,
    max_age_ms: int,
    max_skew_ms: int,
    first_fee: FeeModel,
    second_fee: FeeModel,
    safety_buffer_per_contract: Decimal,
    quantity: Decimal | None = None,
) -> Opportunity:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    receipts = (first.received_at.astimezone(timezone.utc), second.received_at.astimezone(timezone.utc))
    age = max(0, max(int((now.astimezone(timezone.utc) - received).total_seconds() * 1000) for received in receipts))
    skew = abs(int((receipts[0] - receipts[1]).total_seconds() * 1000))
    depth = common_depth(first, second)
    requested = min(quantity, depth) if quantity is not None else depth
    zero = Opportunity(False, "", Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"),
                       Decimal("0"), Decimal("0"), age, skew)
    if not semantic_pricing_eligible:
        return Opportunity(**{**zero.__dict__, "reason": "SEMANTIC_MATCH_NOT_PRICING_ELIGIBLE"})
    if age > max_age_ms:
        return Opportunity(**{**zero.__dict__, "reason": "STALE_BOOK"})
    if skew > max_skew_ms:
        return Opportunity(**{**zero.__dict__, "reason": "PAIR_SKEW_EXCEEDED"})
    if requested <= 0:
        return Opportunity(**{**zero.__dict__, "reason": "NO_COMMON_DEPTH"})
    left, right = walk(first.asks, requested), walk(second.asks, requested)
    if left.quantity != requested or right.quantity != requested:
        return Opportunity(**{**zero.__dict__, "reason": "INSUFFICIENT_DEPTH"})
    cost = left.cost + right.cost
    fees = first_fee.fee(left.cost) + second_fee.fee(right.cost)
    buffer = safety_buffer_per_contract * requested
    payout = requested
    profit = payout - cost - fees - buffer
    return Opportunity(profit > 0, "QUALIFYING" if profit > 0 else "NO_CONSERVATIVE_EDGE",
                       requested, cost, payout, fees, buffer, profit, age, skew)
