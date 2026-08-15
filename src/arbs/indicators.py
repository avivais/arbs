"""Non-actionable sports complement-cost observations from captured public books."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from arbs.pricing import Level, normalize_levels, walk
ONE=Decimal("1")

@dataclass(frozen=True)
class IndicatorLeg:
 venue:str; outcome:str; instrument_id:str; asks:tuple[Level,...]; received_at:datetime
 source_time_status:str="not_exposed"; source_age_at_receipt_ms:Decimal|None=None

@dataclass(frozen=True)
class Candidate:
 status:str; quantity:Decimal; first:IndicatorLeg; second:IndicatorLeg
 first_cost:Decimal; second_cost:Decimal; total_cost:Decimal; raw_gap:Decimal
 reserve:Decimal; gap_after_reserve:Decimal; pair_skew_ms:int; quote_age_ms:int

def utc(value:str)->datetime:
 result=datetime.fromisoformat(value.replace("Z","+00:00"))
 if result.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
 return result.astimezone(timezone.utc)

def kalshi_yes_asks(sample:dict[str,Any])->tuple[Level,...]:
 raw=sample["kalshi"]["payload"]["orderbook_fp"].get("no_dollars",[])
 return normalize_levels((str(ONE-Decimal(str(p))),str(q)) for p,q in raw)

def polymarket_asks(sample:dict[str,Any])->tuple[Level,...]:
 raw=sample["polymarket"]["payload"].get("asks",[])
 return normalize_levels((str(x["price"]),str(x["size"])) for x in raw)

def leg_from_sample(sample:dict[str,Any],*,venue:str,outcome:str,instrument_id:str)->IndicatorLeg:
 if sample.get("status")!="complete": raise ValueError("sample is not complete")
 source=sample[venue]
 if source.get("identifier")!=instrument_id: raise ValueError("captured instrument mismatch")
 age=source.get("source_age_at_receipt_ms")
 return IndicatorLeg(venue,outcome,instrument_id,kalshi_yes_asks(sample) if venue=="kalshi" else polymarket_asks(sample),utc(source["received_at"]),str(source.get("source_time_status","invalid")),Decimal(str(age)) if age is not None else None)

def _candidate_quantity(a:IndicatorLeg,b:IndicatorLeg,reserve:Decimal)->Decimal:
 i=j=0; left=a.asks[0].quantity if a.asks else Decimal(0); right=b.asks[0].quantity if b.asks else Decimal(0); q=Decimal(0)
 while i<len(a.asks) and j<len(b.asks):
  if a.asks[i].price+b.asks[j].price+reserve>=ONE: break
  x=min(left,right); q+=x; left-=x; right-=x
  if left==0:
   i+=1; left=a.asks[i].quantity if i<len(a.asks) else Decimal(0)
  if right==0:
   j+=1; right=b.asks[j].quantity if j<len(b.asks) else Decimal(0)
 return q

def evaluate_candidate(first:IndicatorLeg,second:IndicatorLeg,*,now:datetime,reserve_per_pair:Decimal=Decimal("0.01"),max_quote_age_ms:int=90000,max_cross_leg_skew_ms:int=800,max_source_age_ms:int=90000,future_tolerance_ms:int=2000,quantity_cap:Decimal=Decimal("1000"))->Candidate:
 if now.tzinfo is None: raise ValueError("now must be timezone-aware")
 ages=tuple(int((now.astimezone(timezone.utc)-x.received_at).total_seconds()*1000) for x in (first,second)); age=max(ages); skew=abs(int((first.received_at-second.received_at).total_seconds()*1000))
 invalid_source=any(x.source_time_status in {"invalid","future"} or (x.source_time_status=="available" and (x.source_age_at_receipt_ms is None or x.source_age_at_receipt_ms < -future_tolerance_ms or x.source_age_at_receipt_ms > max_source_age_ms)) for x in (first,second))
 unavailable=any(x < -future_tolerance_ms for x in ages) or invalid_source or age>max_quote_age_ms or skew>max_cross_leg_skew_ms
 zero=Decimal(0)
 if not first.asks or not second.asks: return Candidate("NO_DEPTH",zero,first,second,zero,zero,zero,zero,zero,zero,skew,age)
 buffered=_candidate_quantity(first,second,reserve_per_pair); top=min(first.asks[0].quantity,second.asks[0].quantity); q=min(buffered if buffered>0 else top,quantity_cap)
 left,right=walk(first.asks,q),walk(second.asks,q); cost=left.cost+right.cost; raw=q-cost; reserve=reserve_per_pair*q; after=raw-reserve
 status="OBSERVED_RESERVED_GAP" if buffered>0 else "OBSERVED_RAW_GAP" if first.asks[0].price+second.asks[0].price<ONE else "NO_RAW_GAP"
 if unavailable: status="UNAVAILABLE_FRESHNESS"
 return Candidate(status,q,first,second,left.cost,right.cost,cost,raw,reserve,after,skew,age)

def decimal_text(value:Decimal)->str:return format(value,"f")

def candidate_record(c:Candidate)->dict[str,Any]:
 q=c.quantity
 legs=[]
 for x,cost in ((c.first,c.first_cost),(c.second,c.second_cost)):
  legs.append({
   "venue":x.venue,
   "outcome":x.outcome,
   "instrument_id":x.instrument_id,
   "best_ask":decimal_text(x.asks[0].price) if x.asks else None,
   "best_ask_quantity":decimal_text(x.asks[0].quantity) if x.asks else None,
   "ask_levels":[{"price":decimal_text(level.price),"quantity":decimal_text(level.quantity)} for level in x.asks],
   "vwap":decimal_text(cost/q) if q else None,
   "received_at":x.received_at.isoformat().replace("+00:00","Z"),
   "source_time_status":x.source_time_status,
   "source_age_at_receipt_ms":decimal_text(x.source_age_at_receipt_ms) if x.source_age_at_receipt_ms is not None else None,
  })
 return {"status":c.status,"indicator_type":"NORMAL_SETTLEMENT_COMPLEMENT_COST","assumed_scenario":"GAME_COMPLETES_AND_BOTH_VENUES_GRADE_THE_SAME_WINNER","pricing_eligible":False,"actionability":"NON_ACTIONABLE","settlement_status":"REVIEW","fee_status":"UNVERIFIED_EXCLUDED","fee_total":None,"net_edge":None,"reason_codes":["SETTLEMENT_EQUIVALENCE_NOT_PROVEN","CANCELLATION_POSTPONEMENT_RULES_DIFFER"],"quantity":decimal_text(q),"quantity_cap":"1000","legs":legs,"combined_vwap":decimal_text(c.total_cost/q) if q else None,"normal_settlement_raw_gap_per_pair":decimal_text(c.raw_gap/q) if q else None,"normal_settlement_raw_gap_total":decimal_text(c.raw_gap),"assumed_execution_reserve_per_pair":decimal_text(c.reserve/q) if q else None,"assumed_execution_reserve_total":decimal_text(c.reserve),"gap_after_assumed_reserve_per_pair":decimal_text(c.gap_after_reserve/q) if q else None,"gap_after_assumed_reserve_total":decimal_text(c.gap_after_reserve),"quote_age_ms_at_generation":c.quote_age_ms,"cross_leg_receipt_skew_ms":c.pair_skew_ms}
