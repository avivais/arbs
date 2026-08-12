"""Typed canonical event identity with explicit unknowns and fail-closed comparison."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EventIdentity:
 venue:str; event_id:str; sport:str; competition:str; participants:tuple[str,...]; roles:tuple[tuple[str,str],...]
 start_utc:datetime; stage:str|None; game_number:int|None; neutral_site:bool|None; authoritative_ids:tuple[tuple[str,str],...]
 reschedule_state:str="NONE"


@dataclass(frozen=True)
class IdentityResult:
 decision:str; reasons:tuple[str,...]; start_delta_seconds:int


def compare(left:EventIdentity,right:EventIdentity,tolerance_seconds:int=900)->IdentityResult:
 reasons=[];delta=abs(int((left.start_utc-right.start_utc).total_seconds()))
 if left.sport!=right.sport or left.competition!=right.competition:return IdentityResult('NO_MATCH',('SPORT_OR_COMPETITION_CONFLICT',),delta)
 if set(left.participants)!=set(right.participants):return IdentityResult('NO_MATCH',('PARTICIPANT_SET_CONFLICT',),delta)
 if left.stage is not None and right.stage is not None and left.stage!=right.stage:return IdentityResult('NO_MATCH',('STAGE_CONFLICT',),delta)
 if left.game_number is not None and right.game_number is not None and left.game_number!=right.game_number:return IdentityResult('NO_MATCH',('GAME_NUMBER_CONFLICT',),delta)
 if left.neutral_site is not None and right.neutral_site is not None and left.neutral_site!=right.neutral_site:return IdentityResult('NO_MATCH',('NEUTRAL_SITE_CONFLICT',),delta)
 lr=dict(left.roles);rr=dict(right.roles)
 for participant in set(lr)&set(rr):
  if lr[participant]!=rr[participant]:return IdentityResult('NO_MATCH',('PARTICIPANT_ROLE_CONFLICT',),delta)
 la=dict(left.authoritative_ids);ra=dict(right.authoritative_ids)
 for namespace in set(la)&set(ra):
  if la[namespace]!=ra[namespace]:return IdentityResult('NO_MATCH',('AUTHORITATIVE_ID_CONFLICT',),delta)
 if delta>tolerance_seconds:return IdentityResult('NO_MATCH',('START_OUTSIDE_WINDOW',),delta)
 if not left.roles or not right.roles:reasons.append('PARTICIPANT_ROLE_UNKNOWN')
 if left.neutral_site is None or right.neutral_site is None:reasons.append('NEUTRAL_SITE_UNKNOWN')
 if left.game_number is None or right.game_number is None:reasons.append('GAME_NUMBER_UNKNOWN')
 if not set(la)&set(ra):reasons.append('NO_SHARED_AUTHORITATIVE_ID_NAMESPACE')
 if left.reschedule_state!='NONE' or right.reschedule_state!='NONE':reasons.append('RESCHEDULE_EVIDENCE_PRESENT')
 return IdentityResult('REVIEW' if reasons else 'EXACT',tuple(reasons),delta)
