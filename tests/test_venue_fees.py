"""Offline synthetic evidence fixtures; no live fee schedule is attested here."""
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction
import hashlib

import pytest

from arbs.venue_fees import (
    MODEL_VERSION,
    POLYMARKET_TAKER_RATES,
    FeeFill,
    FeeSchedule,
    UnverifiedFeeError,
    quote_fees,
)

D = Decimal
AS_OF = date(2026, 9, 17)


def schedule(venue="kalshi", role="taker", **changes):
    """Deliberately synthetic schedule evidence, not an official source snapshot."""
    values = dict(
        venue=venue, market_id="TEST-ONLY-MARKET", side="yes", role=role,
        product="general" if venue == "kalshi" else "sports",
        rate=(D("0.07") if role == "taker" else D("0.0175"))
        if venue == "kalshi" else (D("0.05") if role == "taker" else D("0")),
        source_url="https://example.invalid/synthetic-fee-fixture",
        source_hash=hashlib.sha256(b"synthetic test-only fee snapshot").hexdigest(),
        retrieved_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        balance_precision=D('.01') if venue == 'kalshi' else None,
        effective_date=date(2026, 9, 1), applicability=True,
        applicability_provenance="Synthetic explicit test-market applicability",
    )
    values.update(changes)
    return FeeSchedule(**values)


def quote(model=None, price="0.5", quantity="1", **kwargs):
    return quote_fees(model or schedule(), [FeeFill(D(price), D(quantity))],
                      as_of=AS_OF, **kwargs)


def test_kalshi_general_nonlinear_formula_not_notional_rate():
    result = quote(quantity="100")
    assert result.fills[0].raw_fee == D("1.75")
    assert result.total_fee == D("1.75")
    assert result.verified and not result.exact_venue_fee
    assert result.status == "VERIFIED_SCHEDULE"
    assert result.calculation == "conservative_upper_bound"
    assert result.version == MODEL_VERSION
    assert result.schedule.market_id == "TEST-ONLY-MARKET"
    assert result.schedule.side == "yes"
    assert result.as_of == AS_OF
    assert not result.blockers


def test_kalshi_maker_explicit_rate_and_applicability():
    result = quote(schedule(role="maker"), quantity="100")
    assert result.fills[0].raw_fee == D("0.4375")
    assert result.total_fee == D("0.44")
    with pytest.raises(ValueError, match="rate does not match"):
        schedule(role="maker", rate=D("0"))
    with pytest.raises(UnverifiedFeeError, match="UNKNOWN_APPLICABILITY"):
        quote(schedule(role="maker", applicability=None))


@pytest.mark.parametrize("product,rate,expected", [
    ("sports", "0.05", "1.25"), ("crypto", "0.07", "1.75"),
    ("finance", "0.04", "1"), ("politics", "0.04", "1"),
])
def test_polymarket_explicit_product_rates(product, rate, expected):
    result = quote(schedule("polymarket", product=product, rate=D(rate)), quantity="100")
    assert result.total_fee == D(expected)
    assert result.verified
    assert not result.exact_venue_fee
    assert result.calculation == "conservative_upper_bound"
    assert POLYMARKET_TAKER_RATES[product] == D(rate)


@pytest.mark.parametrize("product", list(POLYMARKET_TAKER_RATES))
def test_polymarket_maker_zero_only_for_explicit_product(product):
    result = quote(schedule("polymarket", "maker", product=product))
    assert result.total_fee == D("0")
    assert result.guaranteed_rebate == D("0")
    assert result.verified


@pytest.mark.parametrize("changes", [
    {"applicability": None}, {"applicability_provenance": None},
])
@pytest.mark.parametrize("allow_conditional", [False, True])
def test_unknown_maker_applicability_never_assumes_free(changes, allow_conditional):
    with pytest.raises(UnverifiedFeeError, match="MAKER_ZERO_REQUIRES"):
        quote(schedule("polymarket", "maker", **changes), allow_conditional=allow_conditional)


@pytest.mark.parametrize("changes,blocker", [
    ({"effective_date": None}, "UNKNOWN_EFFECTIVE_DATE"),
    ({"applicability": None}, "UNKNOWN_APPLICABILITY"),
    ({"applicability_provenance": None}, "MISSING_APPLICABILITY_PROVENANCE"),
])
def test_missing_evidence_fails_closed_or_explicitly_conditional(changes, blocker):
    model = schedule(**changes)
    with pytest.raises(UnverifiedFeeError, match=blocker):
        quote(model)
    result = quote(model, allow_conditional=True)
    assert result.status == "CONDITIONAL_ESTIMATE"
    assert not result.verified and not result.exact_venue_fee
    assert blocker in result.blockers
    assert result.total_fee == D("0.02")
    assert result.schedule is model
    if "effective_date" in changes:
        assert result.schedule.effective_date is None  # retrieval date is NOT a substitute


def test_all_unknowns_preserved_and_no_default_effective_date():
    result = quote(schedule(effective_date=None, applicability=None,
                            applicability_provenance=None), allow_conditional=True)
    assert result.blockers == ("UNKNOWN_EFFECTIVE_DATE", "UNKNOWN_APPLICABILITY",
                               "MISSING_APPLICABILITY_PROVENANCE")
    assert result.schedule.effective_date is None


@pytest.mark.parametrize("conditional", [False, True])
@pytest.mark.parametrize("changes,reason", [
    ({"applicability": False}, "SCHEDULE_NOT_APPLICABLE"),
    ({"effective_date": date(2026, 9, 18)}, "SCHEDULE_NOT_YET_EFFECTIVE"),
])
def test_known_inapplicability_and_future_date_always_block(changes, reason, conditional):
    with pytest.raises(UnverifiedFeeError, match=reason):
        quote(schedule(**changes), allow_conditional=conditional)


def test_effective_date_boundary():
    assert quote(schedule(effective_date=AS_OF)).verified


def test_maker_date_unknown_can_only_be_conditional_with_explicit_applicability():
    model = schedule("polymarket", "maker", effective_date=None)
    with pytest.raises(UnverifiedFeeError, match="UNKNOWN_EFFECTIVE_DATE"):
        quote(model)
    result = quote(model, allow_conditional=True)
    assert result.total_fee == D("0") and not result.verified


@pytest.mark.parametrize("field", ["price", "quantity"])
@pytest.mark.parametrize("bad", [D("NaN"), D("sNaN"), D("Infinity"), D("-Infinity")])
def test_nonfinite_fills(field, bad):
    values = dict(price=D("0.5"), quantity=D("1"))
    values[field] = bad
    with pytest.raises(ValueError, match="finite"):
        FeeFill(**values)


@pytest.mark.parametrize("field", ["price", "quantity"])
@pytest.mark.parametrize("bad", [0.5, float("nan"), float("inf"), "0.5", 1, True])
def test_no_float_or_implicit_conversion(field, bad):
    values = dict(price=D("0.5"), quantity=D("1"))
    values[field] = bad
    with pytest.raises(TypeError, match="must be Decimal"):
        FeeFill(**values)


@pytest.mark.parametrize("field,bad", [
    ("price", "-0.01"), ("price", "1.01"), ("quantity", "0"), ("quantity", "-1"),
])
def test_fill_range_validation(field, bad):
    values = dict(price=D("0.5"), quantity=D("1"))
    values[field] = D(bad)
    with pytest.raises(ValueError):
        FeeFill(**values)


@pytest.mark.parametrize("field", ["rate", "minimum"])
@pytest.mark.parametrize("bad", [D("-0.01"), D("NaN"), D("sNaN"), D("Infinity")])
def test_nonfinite_negative_fee_and_rebate_rejected(field, bad):
    with pytest.raises(ValueError):
        schedule(**{field: bad})


@pytest.mark.parametrize("field", ["rate", "minimum"])
@pytest.mark.parametrize("bad", [0.07, "0.07", 0, False])
def test_fee_values_require_decimal(field, bad):
    with pytest.raises(TypeError):
        schedule(**{field: bad})


@pytest.mark.parametrize("changes", [
    {"market_id": ""}, {"side": " "}, {"role": "unknown"}, {"venue": "other"},
    {"product": ""}, {"source_url": "fees.md"}, {"source_url": "http://example.com"},
    {"source_hash": ""}, {"source_hash": "g" * 64},
    {"retrieved_at": datetime(2026, 9, 17)}, {"retrieved_at": None},
    {"effective_date": "2026-09-01"},
    {"effective_date": datetime(2026, 9, 1, tzinfo=timezone.utc)},
    {"applicability": 1}, {"applicability_provenance": " "},
    {"minimum_provenance": " "}, {"version": "future-unknown"},
    {"rate": D("0")},
])
def test_metadata_and_version_validation(changes):
    with pytest.raises((ValueError, TypeError)):
        schedule(**changes)


def test_required_scope_evidence_and_rate_have_no_silent_defaults():
    with pytest.raises(TypeError):
        FeeSchedule()
    model = schedule()
    for field in ("rate", "role", "market_id", "side", "product", "source_url",
                  "source_hash", "retrieved_at", "effective_date", "applicability",
                  "applicability_provenance"):
        values = model.__dict__.copy()
        del values[field]
        with pytest.raises(TypeError):
            FeeSchedule(**values)


def test_unknown_product_and_mismatched_rate_rejected():
    with pytest.raises(ValueError, match="unsupported Polymarket product"):
        schedule("polymarket", "maker", product="unverified-product")
    with pytest.raises(ValueError, match="rate does not match"):
        schedule("polymarket", product="crypto", rate=D("0.05"))


def test_kalshi_each_split_fill_rounds_up_separately():
    fills = [FeeFill(D("0.1"), D("1"))] * 3
    result = quote_fees(schedule(), iter(fills), as_of=AS_OF)
    assert [item.raw_fee for item in result.fills] == [D("0.0063")] * 3
    assert [item.fee for item in result.fills] == [D("0.01")] * 3
    assert result.total_fee == D("0.03")
    assert quote(price="0.1", quantity="3").total_fee == D("0.02")


def test_polymarket_split_fills_and_unknown_rounding_tie():
    model = schedule("polymarket")
    fills = [FeeFill(D("0.5"), D("0.0004"))] * 2
    result = quote_fees(model, fills, as_of=AS_OF)
    assert [item.raw_fee for item in result.fills] == [D("0.000005")] * 2
    assert result.total_fee == D("0.00002")
    assert quote(model, quantity="0.0008").total_fee == D("0.00001")
    assert not result.exact_venue_fee


def test_polymarket_subminimum_is_deliberately_overestimated_not_claimed_exact():
    result = quote(schedule("polymarket"), price="0.0001")
    assert result.fills[0].raw_fee == D("0.0000049995")
    # Docs say amounts below the smallest fee round to zero; our ceiling is
    # intentionally an upper bound and not a reproduction of venue rounding.
    assert result.total_fee == D("0.00001")
    assert result.calculation == "conservative_upper_bound"
    assert not result.exact_venue_fee


@pytest.mark.parametrize("price", ["0", "1"])
@pytest.mark.parametrize("venue", ["kalshi", "polymarket"])
def test_zero_formula_endpoints_have_no_artificial_minimum(price, venue):
    assert quote(schedule(venue), price=price).total_fee == D("0")


def test_minimum_is_evidenced_per_fill_before_rounding():
    with pytest.raises(ValueError, match="minimum requires explicit provenance"):
        schedule(minimum=D("0.031"))
    model = schedule(minimum=D("0.031"), minimum_provenance="Synthetic market minimum")
    result = quote_fees(model, [FeeFill(D("0.1"), D("1"))] * 2, as_of=AS_OF)
    assert result.total_fee == D("0.08")
    assert all(item.assessed_base == D("0.031") for item in result.fills)
    assert quote(model, price="0").total_fee == D("0.04")
    assert quote(model, quantity="100").total_fee == D("1.75")
    with pytest.raises(ValueError, match="maker-free"):
        schedule("polymarket", "maker", minimum=D("0.01"), minimum_provenance="test")


def test_multiple_prices_are_not_replaced_by_vwap():
    fills = [FeeFill(D("0.1"), D("100")), FeeFill(D("0.9"), D("100"))]
    result = quote_fees(schedule(), fills, as_of=AS_OF)
    assert result.total_fee == D("1.26")
    assert quote(price="0.5", quantity="200").total_fee == D("3.5")


def test_arithmetic_exact_even_under_hostile_decimal_context():
    model = schedule("polymarket", product="crypto", rate=D("0.07"))
    fill = FeeFill(D("0.123456789123456789123456789"),
                   D("987654321098765432109876543210.123456789"))
    expected_raw = Fraction(fill.quantity) * Fraction(model.rate) * Fraction(fill.price) * (
        1 - Fraction(fill.price))
    with localcontext() as context:
        context.prec = 2
        context.Emax = 9
        context.Emin = -9
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        result = quote_fees(model, [fill, fill], as_of=AS_OF)
    assert Fraction(result.fills[0].raw_fee) == expected_raw
    assert Fraction(result.total_fee) == 2 * Fraction(result.fills[0].fee)
    assert expected_raw <= Fraction(result.fills[0].fee) < expected_raw + Fraction(D("0.00001"))


@pytest.mark.parametrize("venue", ["kalshi", "polymarket"])
def test_rounding_upper_bound_and_no_guaranteed_rebates_across_prices(venue):
    model = schedule(venue)
    for numerator in range(101):
        price = D(numerator) / D(100)
        result = quote(model, price=str(price), quantity="1.23456789")
        item = result.fills[0]
        assert item.raw_fee <= item.fee < item.raw_fee + model.quantum
        assert result.total_fee >= 0 and result.guaranteed_rebate == 0


def test_empty_and_wrong_fills_rejected():
    with pytest.raises(ValueError, match="at least one"):
        quote_fees(schedule(), [], as_of=AS_OF)
    with pytest.raises(TypeError, match="FeeFill"):
        quote_fees(schedule(), [(D("0.5"), D("1"))], as_of=AS_OF)
    with pytest.raises(TypeError, match="schedule"):
        quote_fees(None, [], as_of=AS_OF)
    with pytest.raises(TypeError, match="allow_conditional"):
        quote(allow_conditional="true")
    with pytest.raises(TypeError, match="as_of"):
        quote_fees(schedule(), [], as_of="2026-09-17")


def test_evidence_and_results_are_immutable():
    model = schedule()
    result = quote(model)
    with pytest.raises(FrozenInstanceError):
        model.effective_date = None
    with pytest.raises(FrozenInstanceError):
        result.verified = False
    with pytest.raises(TypeError):
        POLYMARKET_TAKER_RATES["sports"] = D("0")
    assert not quote(replace(model, effective_date=None), allow_conditional=True).verified
