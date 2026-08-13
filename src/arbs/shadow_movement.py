"""Derived subsequent-movement report from immutable paired-book samples."""
from __future__ import annotations
import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _top(payload:dict[str,Any],venue:str)->tuple[Decimal|None,Decimal|None]:
 if venue=='polymarket':
  bids=[(Decimal(str(x['price'])),Decimal(str(x['size']))) for x in payload.get('bids',[]) if Decimal(str(x['size']))>0]
  asks=[(Decimal(str(x['price'])),Decimal(str(x['size']))) for x in payload.get('asks',[]) if Decimal(str(x['size']))>0]
  return (max((x[0] for x in bids),default=None),min((x[0] for x in asks),default=None))
 book=payload.get('orderbook_fp',{});yes=[(Decimal(str(x[0])),Decimal(str(x[1]))) for x in book.get('yes_dollars',[])];no=[(Decimal(str(x[0])),Decimal(str(x[1]))) for x in book.get('no_dollars',[])]
 bid=max((x[0] for x in yes if x[1]>0),default=None);ask=min((Decimal('1')-x[0] for x in no if x[1]>0),default=None)
 return bid,ask


def report(paths:list[Path])->dict[str,Any]:
 series:dict[str,list[dict[str,Any]]]={}
 failures=0
 for path in paths:
  x=json.loads(path.read_text())
  if x.get('status')!='complete':failures+=1;continue
  series.setdefault(x['pair_id'],[]).append(x)
 transitions=[]
 for pair_id,items in series.items():
  items.sort(key=lambda x:x['started_at'])
  for before,after in zip(items,items[1:]):
   row={'pair_id':pair_id,'before':before['started_at'],'after':after['started_at'],'venues':{}}
   for venue in ('kalshi','polymarket'):
    b=_top(before[venue]['payload'],venue);a=_top(after[venue]['payload'],venue)
    row['venues'][venue]={'bid_before':str(b[0]) if b[0] is not None else None,'bid_after':str(a[0]) if a[0] is not None else None,
                          'ask_before':str(b[1]) if b[1] is not None else None,'ask_after':str(a[1]) if a[1] is not None else None,
                          'payload_changed':before[venue]['payload_sha256']!=after[venue]['payload_sha256']}
   transitions.append(row)
 return {'schema_version':1,'pair_count':len(series),'successful_samples':sum(len(x) for x in series.values()),'failure_count':failures,
         'transition_count':len(transitions),'changed_transition_count':sum(any(v['payload_changed'] for v in x['venues'].values()) for x in transitions),
         'top_quote_changed_transition_count':sum(any(v['bid_before']!=v['bid_after'] or v['ask_before']!=v['ask_after'] for v in x['venues'].values()) for x in transitions),
         'transitions':transitions}
