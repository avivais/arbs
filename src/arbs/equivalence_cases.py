"""Executable structured equivalence cases for the activated decision engine."""
from __future__ import annotations
from dataclasses import dataclass,replace
from datetime import datetime,timezone
from arbs.domain import CanonicalContract,MaterialRules,NormalizedTime,Predicate,SourceEvidence
from arbs.matching.engine import candidate_pairs,decide


def _contract(venue:str)->CanonicalContract:
 when=datetime(2026,8,12,17,40,tzinfo=timezone.utc)
 rules=MaterialRules('MLB','none','included','24h','fair','same-event-only','team','void','none','review','official','UTC','fair')
 return CanonicalContract('1.0.0','cases',venue,venue+'-event',venue+'-contract','baseball','mlb',('BAL','MIN'),when,
  NormalizedTime(when,'2026-08-12T17:40:00Z','UTC'),'regular-season',(('BAL','away'),('MIN','home')),False,None,
  Predicate('HEAD_TO_HEAD','winner','event','full_game','full_game_including_extras','EQ',None,'BAL'),rules,'open',
  SourceEvidence(venue,venue+'-id','https://example.com','a'*64,'2026-08-12T00:00:00Z',('title',),('fixture',)))


def run_cases()->list[dict[str,str]]:
 a=_contract('a');b=_contract('b');cases=[]
 def add(identifier:str,left:CanonicalContract,right:CanonicalContract,expected:str):
  candidates=next(candidate_pairs((left,),(right,)))[1]
  actual=decide(left,candidates).decision.value;cases.append({'id':identifier,'expected':expected,'actual':actual})
 add('head_to_head_exact',a,b,'EXACT')
 add('same_teams_next_day',a,replace(b,scheduled_start_utc=datetime(2026,8,13,17,40,tzinfo=timezone.utc)),'REVIEW')
 add('postponement_window_differs',a,replace(b,rules=replace(b.rules,postponement='7d')),'REVIEW')
 add('predicate_family_differs',a,replace(b,predicate=replace(b.predicate,market_family='HANDICAP')),'NO_MATCH')
 add('unknown_material_rule',a,replace(b,rules=replace(b.rules,exceptional_settlement=None)),'REVIEW')
 return cases
