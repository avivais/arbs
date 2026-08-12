"""Immutable reviewer events; reviews never alter pricing eligibility."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from typing import Any

TERMINAL={"APPROVED_OVERRIDE","REJECTED","NEEDS_MORE_EVIDENCE"}

@dataclass(frozen=True)
class ReviewEvent:
 case_id:str;event_seq:int;event_type:str;reviewer_id:str;recorded_at:datetime;expires_at:datetime|None
 decision_id:str;decision_evidence_sha256:str;differences:tuple[str,...];scenario_proof:dict[str,Any];snapshot_hashes:tuple[str,...];rationale:str


def validate(event:ReviewEvent,prior:tuple[ReviewEvent,...]=(),max_ttl:timedelta=timedelta(days=7))->None:
 if not event.reviewer_id.strip():raise ValueError('reviewer required')
 if event.event_seq!=len(prior)+1:raise ValueError('invalid event sequence')
 if prior and any(x.event_type in TERMINAL for x in prior):raise ValueError('terminal review already exists')
 if event.event_type in TERMINAL:
  if not event.differences or not event.scenario_proof or not event.snapshot_hashes:raise ValueError('terminal review evidence required')
  if event.expires_at is None or event.expires_at<=event.recorded_at or event.expires_at-event.recorded_at>max_ttl:raise ValueError('invalid expiry')


def effective_pricing_eligible(original_decision:str,original_eligible:bool,execution_phase_enabled:bool,reviews:tuple[ReviewEvent,...])->bool:
 del reviews
 return original_decision=='EXACT' and original_eligible and execution_phase_enabled
