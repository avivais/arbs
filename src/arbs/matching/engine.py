"""Pure candidate and equivalence helpers for canonical contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from arbs.domain import CanonicalContract, Decision


@dataclass(frozen=True)
class EquivalenceResult:
    decision: Decision
    pricing_eligible: bool
    reasons: tuple[str, ...]
    checks: tuple[str, ...]


def candidate_pairs(left: Iterable[CanonicalContract], right: Iterable[CanonicalContract], tolerance_seconds: int = 900):
    for a in left:
        survivors = []
        for b in right:
            if a.sport_id != b.sport_id or a.competition_id != b.competition_id:
                continue
            if a.participant_ids != b.participant_ids:
                continue
            if abs((a.scheduled_start_utc - b.scheduled_start_utc).total_seconds()) <= tolerance_seconds:
                survivors.append(b)
        yield a, tuple(survivors)


def decide(a: CanonicalContract, candidates: tuple[CanonicalContract, ...]) -> EquivalenceResult:
    if len(candidates) != 1:
        return EquivalenceResult(Decision.REVIEW, False, ("AMBIGUOUS_OR_MISSING_UNIQUE_CANDIDATE",), ("uniqueness",))
    b = candidates[0]
    if a.predicate != b.predicate:
        return EquivalenceResult(Decision.NO_MATCH, False, ("PREDICATE_DIFFERENCE",), ("event", "predicate"))
    if a.lifecycle != b.lifecycle:
        return EquivalenceResult(Decision.REVIEW, False, ("LIFECYCLE_DIFFERENCE",), ("event", "predicate", "lifecycle"))
    if not a.rules.complete() or not b.rules.complete():
        return EquivalenceResult(Decision.REVIEW, False, ("MATERIAL_RULE_UNKNOWN",), ("event", "predicate", "lifecycle", "rules"))
    if a.rules != b.rules:
        return EquivalenceResult(Decision.REVIEW, False, ("MATERIAL_RULE_DIFFERENCE",), ("event", "predicate", "lifecycle", "rules"))
    return EquivalenceResult(Decision.EXACT, True, (), ("event", "predicate", "lifecycle", "rules", "uniqueness", "evidence"))


def complementary_binary(selected: tuple[str, ...], full_outcome_space: tuple[str, ...]) -> bool:
    return len(full_outcome_space) == 2 and len(set(full_outcome_space)) == 2 and set(selected) == set(full_outcome_space)
