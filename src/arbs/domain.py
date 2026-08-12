"""Versioned canonical contracts for deterministic sports-market comparison."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Mapping

SCHEMA_VERSION = "1.0.0"
PARSER_VERSION = "mlb-moneyline-1.0.0"


class Decision(StrEnum):
    EXACT = "EXACT"
    REVIEW = "REVIEW"
    NO_MATCH = "NO_MATCH"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class SourceEvidence:
    venue: str
    source_id: str
    source_url: str
    snapshot_sha256: str | None
    received_at: str | None
    field_paths: tuple[str, ...]
    excerpts: tuple[str, ...]


@dataclass(frozen=True)
class Predicate:
    market_family: str
    metric: str
    subject: str
    event_scope: str
    grading_period: str
    operator: str
    threshold: Decimal | None
    selected_outcome: str


@dataclass(frozen=True)
class NormalizedTime:
    utc: datetime
    original_text: str
    original_timezone: str


@dataclass(frozen=True)
class MaterialRules:
    official_source: str | None
    correction_window: str | None
    overtime_extra_time_shootout: str | None
    postponement: str | None
    cancellation_abandonment: str | None
    venue_opponent_change: str | None
    participation: str | None
    dnp_withdrawal: str | None
    tie_push_dead_heat: str | None
    format_change: str | None
    statistic_definition: str | None
    deadline_timezone: str | None
    exceptional_settlement: str | None

    def complete(self) -> bool:
        return all(value is not None for value in asdict(self).values())


@dataclass(frozen=True)
class CanonicalContract:
    schema_version: str
    parser_version: str
    venue: str
    event_id: str
    contract_id: str
    sport_id: str
    competition_id: str
    participant_ids: tuple[str, str]
    scheduled_start_utc: datetime
    scheduled_start_source: NormalizedTime
    stage_or_game_number: str
    participant_roles: tuple[tuple[str, str], ...]
    neutral_site: bool | None
    authoritative_event_id: str | None
    predicate: Predicate
    rules: MaterialRules
    lifecycle: str
    evidence: SourceEvidence

    def stable_id(self) -> str:
        payload = json.dumps(to_primitive(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def decimal_exact(value: Any) -> Decimal:
    if isinstance(value, float):
        raise ValueError("binary float is not accepted for exact decimal fields")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("decimal must be finite")
    return result


def utc_exact(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def to_primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value
