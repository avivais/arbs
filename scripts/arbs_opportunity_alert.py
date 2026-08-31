#!/usr/bin/env python3
"""Emit Telegram-ready alerts for newly qualifying read-only Arbs observations.

Empty stdout is intentional: the Hermes no-agent cron remains silent when there is
no newly qualifying pair. A pair is eligible for an alert only when the complete
captured asks for all outcomes total at most 0.97 and the snapshot is fresh.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

THRESHOLD = Decimal(os.environ.get("ARBS_ALERT_THRESHOLD", "0.97"))
MAX_SNAPSHOT_AGE_SECONDS = int(os.environ.get("ARBS_ALERT_MAX_AGE_SECONDS", "90"))
INDICATORS = Path(
    os.environ.get(
        "ARBS_ALERT_INDICATORS",
        "/root/.openclaw/workspace/repos/arbs/data/shadow/latest-indicators.json",
    )
)
STATE = Path(
    os.environ.get(
        "ARBS_ALERT_STATE",
        "/root/.hermes/state/arbs-opportunity-alert.json",
    )
)
HEALTH_STATE = Path(
    os.environ.get(
        "ARBS_ALERT_HEALTH_STATE",
        "/root/.hermes/state/arbs-opportunity-health.json",
    )
)
HEALTH_FAILURE_SCANS = int(os.environ.get("ARBS_ALERT_HEALTH_FAILURE_SCANS", "3"))


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("snapshot timestamp is timezone-naive")
    return parsed.astimezone(timezone.utc)


def decimal(value: Any) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise InvalidOperation("non-finite decimal")
    return parsed


def pair_key(row: dict[str, Any]) -> str:
    legs = row["legs"]
    instruments = sorted(f'{leg.get("venue", "?")}:{leg.get("instrument_id", "?")}' for leg in legs)
    return f'{row.get("event_id", "?")}|{"|".join(instruments)}'


def threshold_metrics(legs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Walk two captured ask ladders while their combined price meets the alert threshold."""
    if len(legs) != 2:
        return None
    books: list[list[tuple[Decimal, Decimal]]] = []
    try:
        for leg in legs:
            levels = [
                (decimal(level["price"]), decimal(level["quantity"]))
                for level in leg["ask_levels"]
            ]
            if not levels or any(price <= 0 or quantity <= 0 for price, quantity in levels):
                return None
            books.append(sorted(levels))
    except (KeyError, TypeError, InvalidOperation, ValueError):
        return None

    i = j = 0
    left = books[0][0][1]
    right = books[1][0][1]
    matched = Decimal("0")
    spends = [Decimal("0"), Decimal("0")]
    while i < len(books[0]) and j < len(books[1]):
        first_price = books[0][i][0]
        second_price = books[1][j][0]
        if first_price + second_price > THRESHOLD:
            break
        matched_now = min(left, right)
        matched += matched_now
        spends[0] += first_price * matched_now
        spends[1] += second_price * matched_now
        left -= matched_now
        right -= matched_now
        if left == 0:
            i += 1
            if i < len(books[0]):
                left = books[0][i][1]
        if right == 0:
            j += 1
            if j < len(books[1]):
                right = books[1][j][1]

    if matched <= 0:
        return None
    total_spend = sum(spends, Decimal("0"))
    return {
        "top_total": books[0][0][0] + books[1][0][0],
        "top_quantities": [books[0][0][1], books[1][0][1]],
        "matched_volume": matched,
        "leg_spends": spends,
        "total_spend": total_spend,
        "nominal_payout": matched,
        "nominal_profit": matched - total_spend,
        "average_cost": total_spend / matched,
    }


def qualifying_rows(payload: dict[str, Any], now: datetime) -> list[dict[str, Any]] | None:
    generated_at = utc(str(payload["generated_at"]))
    age = (now - generated_at).total_seconds()
    if age < -2 or age > MAX_SNAPSHOT_AGE_SECONDS:
        return None

    qualified: list[dict[str, Any]] = []
    for row in payload.get("records", []):
        try:
            legs = row["legs"]
            if len(legs) != 2 or any(leg.get("best_ask") is None for leg in legs):
                continue
            if str(row.get("status", "")).startswith("UNAVAILABLE"):
                continue
            metrics = threshold_metrics(legs)
            if metrics is None:
                continue
            qualified.append({"key": pair_key(row), "row": row, "metrics": metrics})
        except (KeyError, TypeError, InvalidOperation, ValueError):
            continue
    return sorted(qualified, key=lambda item: (item["metrics"]["average_cost"], item["key"]))


def read_active() -> set[str]:
    try:
        payload = json.loads(STATE.read_text(encoding="utf-8"))
        return {str(value) for value in payload.get("active", [])}
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return set()


def write_active(active: set[str], generated_at: str) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(STATE.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "threshold": format(THRESHOLD, "f"),
                "snapshot_generated_at": generated_at,
                "active": sorted(active),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(STATE)


def usable_keys(payload: dict[str, Any]) -> set[str]:
    """Return identities evaluated from complete, freshness-eligible rows."""
    usable: set[str] = set()
    for row in payload.get("records", []):
        try:
            legs = row["legs"]
            if (
                len(legs) == 2
                and all(leg.get("best_ask") is not None and leg.get("ask_levels") for leg in legs)
                and not str(row.get("status", "")).startswith("UNAVAILABLE")
            ):
                usable.add(pair_key(row))
        except (KeyError, TypeError):
            continue
    return usable


def update_health(generated_at: str, total: int, usable: int) -> str | None:
    """Deduplicate sustained coverage-loss and recovery notices by completed scan."""
    try:
        prior = json.loads(HEALTH_STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        prior = {}
    if prior.get("last_snapshot_generated_at") == generated_at:
        return None

    consecutive = int(prior.get("consecutive_unusable_scans", 0))
    alerted = bool(prior.get("alerted", False))
    message = None
    if total == 0 or usable == 0:
        consecutive += 1
        if consecutive >= HEALTH_FAILURE_SCANS and not alerted:
            alerted = True
            message = (
                "⚠️ **Arbs monitoring coverage degraded**\n"
                f"No fresh, evaluable market directions were available in {consecutive} consecutive completed scans. "
                "Opportunity alerts remain fail-closed; no stale quote is being presented as current."
            )
    else:
        if alerted:
            message = (
                "✅ **Arbs monitoring coverage recovered**\n"
                f"The latest completed scan has {usable}/{total} fresh, evaluable directions. "
                "Normal ≥3% opportunity alerting has resumed."
            )
        consecutive = 0
        alerted = False

    HEALTH_STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HEALTH_STATE.with_suffix(HEALTH_STATE.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "last_snapshot_generated_at": generated_at,
                "consecutive_unusable_scans": consecutive,
                "alerted": alerted,
                "total_directions": total,
                "usable_directions": usable,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(HEALTH_STATE)
    return message


def money(value: Decimal) -> str:
    return f"{value * 100:.2f}".rstrip("0").rstrip(".") + "¢"


def percentage(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".") + "%"


def quantity(value: Decimal) -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def dollars(value: Decimal) -> str:
    return f"${value:,.2f}"


def render(items: list[dict[str, Any]], generated_at: str) -> str:
    minimum_edge = (Decimal("1") - THRESHOLD) * Decimal("100")
    lines = [
        f"🚨 **Arbitrage observation ≥{percentage(minimum_edge)}**",
        f"Captured total buy cost ≤ {money(THRESHOLD)} · snapshot {generated_at}",
        "",
    ]
    for item in items:
        row = item["row"]
        legs = row["legs"]
        metrics = item["metrics"]
        label = " + ".join(
            f'{leg.get("outcome", "?")} on {str(leg.get("venue", "?")).title()} @ {money(decimal(leg["best_ask"]))}'
            f' (best-ask volume {quantity(metrics["top_quantities"][index])})'
            for index, leg in enumerate(legs)
        )
        spend_label = " + ".join(
            f'{str(leg.get("venue", "?")).title()} {dollars(metrics["leg_spends"][index])}'
            for index, leg in enumerate(legs)
        )
        participants = " vs ".join(str(value) for value in row.get("participants", [])) or str(row.get("event_id", "Unknown event"))
        lines.extend(
            [
                f"**{participants}**",
                f"• {label}",
                f'• Qualified matched volume: **{quantity(metrics["matched_volume"])} pairs**',
                f'• Captured spend: {spend_label} = **{dollars(metrics["total_spend"])} total**',
                f'• Nominal payout: {dollars(metrics["nominal_payout"])} · **expected nominal profit: {dollars(metrics["nominal_profit"])}**',
                f'• Average combined cost: {money(metrics["average_cost"])} per pair',
                f'• [Kalshi]({row.get("kalshi_url", "")}) · [Polymarket]({row.get("polymarket_url", "")})',
                "",
            ]
        )
    lines.append("⚠️ Read-only signal. Spend and profit are calculated from captured asks; no order was placed. Fees are excluded; quotes can move; cancellation/postponement settlement equivalence is still under REVIEW.")
    return "\n".join(lines)


def main() -> int:
    try:
        payload = json.loads(INDICATORS.read_text(encoding="utf-8"))
        generated_at = str(payload["generated_at"])
        current = qualifying_rows(payload, datetime.now(timezone.utc))
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"Arbs alert monitor could not validate its indicator snapshot: {error}", file=sys.stderr)
        return 1

    # A stale snapshot is not evidence that a previously qualifying pair disappeared.
    # Keep active state unchanged and wait for the next successful broad capture.
    if current is None:
        return 0
    valid_keys = usable_keys(payload)
    health_message = update_health(generated_at, len(payload.get("records", [])), len(valid_keys))
    previous = read_active()
    qualifying = {item["key"] for item in current}
    # Only a fresh, valid evaluation of the same identity may clear it. Rows
    # that are stale/unavailable, or absent from this catalog generation, are
    # unknown and preserve prior deduplication state.
    active = (previous - valid_keys) | qualifying
    newly_qualified = [item for item in current if item["key"] not in previous]
    write_active(active, generated_at)
    messages = []
    if health_message:
        messages.append(health_message)
    if newly_qualified:
        messages.append(render(newly_qualified, generated_at))
    if messages:
        print("\n\n".join(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
