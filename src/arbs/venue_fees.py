"""Standalone, read-only fee arithmetic; deliberately NOT wired into pricing.

All money is USD for unit-payout binary contracts. Inputs must be Decimal, not
floats (including float-derived conversions performed by this module). Each
FeeFill represents one actual execution, not a VWAP or an aggregated order.

Evidence is caller-supplied, not independently authenticated here. A verified
quote means the supplied schedule evidence is complete and effective as_of;
it does NOT establish live market eligibility, source freshness, or execution
permission. Unknown effective dates are never inferred from retrieval times.

Fees are buy-side bounds, not exact charged fees. Kalshi uses ceil-to-six-decimal
trade fees and a separate balance-grid adjustment; no accumulated rounding
rebate is credited. Missing account precision blocks verified calculations and
conditional estimates use the coarser cent grid. Numerical Kalshi base constants
are sensitivity inputs until supported by a fetched binding schedule.

Polymarket's documented five-decimal rounding does not specify tie direction.
We therefore ceil each positive fee to 0.00001, even sub-minimum amounts that
the documentation says round to zero. This is an upper bound, NOT the exact
venue fee. No maker rebates, incentives, settlement or withdrawal charges are
credited or modeled. Source snapshots and real effective dates must be supplied
by the caller; this module embeds no invented evidence or effective dates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
import re
from types import MappingProxyType
from typing import Iterable, Literal
from urllib.parse import urlparse


MODEL_VERSION = "venue-fees-2"
# Conditional numerical sensitivity bases, NOT live-verified current schedules.
# The binding Kalshi PDF returned HTTP 429 in the 2026-09-17 evidence generation.
KALSHI_TAKER_RATE = Decimal("0.07")
KALSHI_MAKER_RATE = Decimal("0.0175")
POLYMARKET_TAKER_RATES = MappingProxyType({
    "sports": Decimal("0.05"),
    "crypto": Decimal("0.07"),
    "finance": Decimal("0.04"),
    "politics": Decimal("0.04"),
})
ZERO = Decimal("0")


class UnverifiedFeeError(ValueError):
    """A fee quote cannot be verified under the supplied evidence."""


def _number(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal (floats and implicit coercion forbidden)")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _date(value: date, name: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be a date, not a timestamp or string")


def _decimal(value: Fraction) -> Decimal:
    """Convert a terminating rational exactly, independent of Decimal context."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("nonterminating decimal")
    scale = max(twos, fives)
    coefficient = value.numerator * 2 ** (scale - twos) * 5 ** (scale - fives)
    digits = Decimal(abs(coefficient)).as_tuple().digits
    return Decimal((int(coefficient < 0), digits, -scale))


def _ceil(value: Fraction, quantum: Decimal) -> Decimal:
    units = value / Fraction(quantum)
    rounded_units = -(-units.numerator // units.denominator)
    return _decimal(Fraction(rounded_units) * Fraction(quantum))


def kalshi_fee_upper_bound(raw_fee: Decimal, buy_notional: Decimal,
                           balance_precision: Decimal) -> Decimal:
    """Current documented buy-side rounding; conservatively credit no accumulator rebate.

    Source: docs.kalshi.com/getting_started/fee_rounding. This is not the old
    ceil-to-cent fee formula: rounding is applied to the signed balance change.
    """
    for name, value in (("raw_fee", raw_fee), ("buy_notional", buy_notional),
                        ("balance_precision", balance_precision)):
        _number(value, name)
    if raw_fee < 0 or buy_notional < 0 or balance_precision not in (Decimal('.01'), Decimal('.0001')):
        raise ValueError('invalid rounding inputs')
    trade_fee = _ceil(Fraction(raw_fee), Decimal('.000001'))
    debit = Fraction(buy_notional) + Fraction(trade_fee)
    return _decimal(Fraction(_ceil(debit, balance_precision)) - Fraction(buy_notional))


@dataclass(frozen=True)
class FeeFill:
    """One fill in the quote's market and side; quantity is contracts, not USD."""

    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        _number(self.price, "price")
        _number(self.quantity, "quantity")
        if not ZERO <= self.price <= Decimal("1"):
            raise ValueError("price must be in [0, 1]")
        if self.quantity <= ZERO:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True)
class FeeSchedule:
    """Explicit schedule assertion scoped to one venue/market/side/role/product.

    side is the caller's nonempty venue-specific side identifier (e.g. yes/no
    or buy/sell); no cross-venue side normalization is implied. applicability
    True asserts that this exact rate/formula/product applies to that scope,
    backed by applicability_provenance. False is an explicit exclusion and
    blocks even conditional estimates. Positive minimums are per fill, need
    their own provenance, and are applied before rounding (including p=0/1).

    Rates are required, with no default maker-free assumption. This version
    supports only the listed general Kalshi and Polymarket product rates;
    market-specific alternative schedules need a separate implementation.
    """

    venue: Literal["kalshi", "polymarket"]
    market_id: str
    side: str
    role: Literal["maker", "taker"]
    product: str
    rate: Decimal
    source_url: str
    source_hash: str  # SHA-256 of the actual source snapshot, 64 hex digits.
    retrieved_at: datetime
    effective_date: date | None
    applicability: bool | None
    applicability_provenance: str | None
    minimum: Decimal = ZERO
    minimum_provenance: str | None = None
    version: str = MODEL_VERSION
    multiplier: Decimal = Decimal("1")
    # None means account precision unknown; conditional bound uses coarser cents.
    balance_precision: Decimal | None = None

    def __post_init__(self) -> None:
        _number(self.multiplier, "multiplier")
        if self.multiplier <= ZERO:
            raise ValueError("multiplier must be positive")
        if self.venue == "polymarket" and self.multiplier != Decimal("1"):
            raise ValueError("Polymarket multiplier unsupported")
        if self.balance_precision is not None:
            _number(self.balance_precision, "balance_precision")
            if self.balance_precision not in (Decimal(".01"), Decimal(".0001")):
                raise ValueError("unsupported account balance precision")
        if self.version != MODEL_VERSION:
            raise ValueError("unsupported fee model version")
        if self.venue not in ("kalshi", "polymarket"):
            raise ValueError("unsupported venue")
        if self.role not in ("maker", "taker"):
            raise ValueError("role must be explicit maker or taker")
        for name in ("market_id", "side", "product", "source_url", "source_hash"):
            _text(getattr(self, name), name)
        if self.side not in ('yes', 'no', 'buy') and not self.side.startswith('buy:'):
            raise ValueError('only buy-side fee replay is supported')
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url must be an absolute HTTPS URL")
        if re.fullmatch(r"[0-9a-fA-F]{64}", self.source_hash) is None:
            raise ValueError("source_hash must be a SHA-256 hex digest")
        if (not isinstance(self.retrieved_at, datetime)
                or self.retrieved_at.utcoffset() is None):
            raise ValueError("retrieved_at must be a timezone-aware datetime")
        if self.effective_date is not None:
            _date(self.effective_date, "effective_date")
        if self.applicability is not None and type(self.applicability) is not bool:
            raise TypeError("applicability must be True, False or None")
        for name in ("applicability_provenance", "minimum_provenance"):
            if getattr(self, name) is not None:
                _text(getattr(self, name), name)
        _number(self.rate, "rate")
        _number(self.minimum, "minimum")
        if self.rate < ZERO or self.minimum < ZERO:
            raise ValueError("negative fees or guaranteed rebates are not supported")
        if self.minimum > ZERO and self.minimum_provenance is None:
            raise ValueError("positive minimum requires explicit provenance")
        if self.venue == "kalshi":
            expected = KALSHI_MAKER_RATE if self.role == "maker" else KALSHI_TAKER_RATE
        else:
            if self.product not in POLYMARKET_TAKER_RATES:
                raise ValueError("unsupported Polymarket product")
            expected = ZERO if self.role == "maker" else POLYMARKET_TAKER_RATES[self.product]
        if self.rate != expected:
            raise ValueError("rate does not match the supported venue/product/role schedule")
        if self.rate == ZERO and self.minimum != ZERO:
            raise ValueError("maker-free product cannot have a positive minimum")

    @property
    def quantum(self) -> Decimal:
        return Decimal("0.01") if self.venue == "kalshi" else Decimal("0.00001")


@dataclass(frozen=True)
class FillFee:
    fill: FeeFill
    raw_fee: Decimal
    assessed_base: Decimal  # max(raw fee, evidenced per-fill minimum)
    fee: Decimal


@dataclass(frozen=True)
class FeeQuote:
    schedule: FeeSchedule
    as_of: date
    fills: tuple[FillFee, ...]
    total_fee: Decimal
    verified: bool
    blockers: tuple[str, ...]
    calculation: Literal["exact_schedule_round_up", "conservative_upper_bound"]
    version: str = MODEL_VERSION

    @property
    def status(self) -> str:
        return "VERIFIED_SCHEDULE" if self.verified else "CONDITIONAL_ESTIMATE"

    @property
    def exact_venue_fee(self) -> bool:
        return self.verified and self.calculation == "exact_schedule_round_up"

    @property
    def guaranteed_rebate(self) -> Decimal:
        return ZERO


def quote_fees(
    schedule: FeeSchedule,
    fills: Iterable[FeeFill],
    *,
    as_of: date,
    allow_conditional: bool = False,
) -> FeeQuote:
    """Round each execution independently, then sum exactly.

    Default behavior fails closed on unknown date or applicability evidence.
    Explicit conditional estimates retain blockers and never become verified.
    Known inapplicability/not-yet-effective schedules always fail. Maker-zero
    estimates additionally require affirmative product applicability evidence,
    even when conditional estimates were requested. as_of is the caller's
    intended fee-effective calendar date, not an inferred retrieval date.
    """
    if not isinstance(schedule, FeeSchedule):
        raise TypeError("schedule must be FeeSchedule")
    if type(allow_conditional) is not bool:
        raise TypeError("allow_conditional must be bool")
    _date(as_of, "as_of")
    if schedule.applicability is False:
        raise UnverifiedFeeError("SCHEDULE_NOT_APPLICABLE")
    if schedule.effective_date is not None and schedule.effective_date > as_of:
        raise UnverifiedFeeError("SCHEDULE_NOT_YET_EFFECTIVE")
    blockers = []
    if schedule.effective_date is None:
        blockers.append("UNKNOWN_EFFECTIVE_DATE")
    if schedule.applicability is not True:
        blockers.append("UNKNOWN_APPLICABILITY")
    if schedule.applicability_provenance is None:
        blockers.append("MISSING_APPLICABILITY_PROVENANCE")
    if schedule.rate == ZERO and (
        schedule.applicability is not True or schedule.applicability_provenance is None
    ):
        raise UnverifiedFeeError("MAKER_ZERO_REQUIRES_EXPLICIT_PRODUCT_APPLICABILITY")
    if schedule.venue == "kalshi" and schedule.balance_precision is None:
        blockers.append("UNKNOWN_ACCOUNT_BALANCE_PRECISION")
    if blockers and not allow_conditional:
        raise UnverifiedFeeError(",".join(blockers))
    results = []
    for fill in fills:
        if not isinstance(fill, FeeFill):
            raise TypeError("fills must contain FeeFill instances, not aggregate pricing.Fill")
        price = Fraction(fill.price)
        raw = Fraction(fill.quantity) * Fraction(schedule.rate) * Fraction(schedule.multiplier) * price * (1 - price)
        base = max(raw, Fraction(schedule.minimum))
        assessed = (kalshi_fee_upper_bound(_decimal(base), _decimal(Fraction(fill.quantity)*price),
                    schedule.balance_precision or Decimal('.01')) if schedule.venue == 'kalshi'
                    else _ceil(base, schedule.quantum))
        results.append(FillFee(fill, _decimal(raw), _decimal(base), assessed))
    if not results:
        raise ValueError("at least one actual fill is required")
    total = _decimal(sum((Fraction(result.fee) for result in results), Fraction(0)))
    calculation = "conservative_upper_bound"
    return FeeQuote(schedule, as_of, tuple(results), total, not blockers,
                    tuple(blockers), calculation)
