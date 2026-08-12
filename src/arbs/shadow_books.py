"""Atomic public paired-book samples and empirical timing summaries."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arbs.books import capture_pair


def sample_pair(kalshi_ticker:str,polymarket_token_id:str,output:Path)->dict[str,Any]:
 try:
  value=capture_pair(kalshi_ticker,polymarket_token_id);value["status"]="complete";value["errors"]=[]
 except Exception as exc:
  value={"schema_version":1,"status":"failed","captured_at":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
         "kalshi_ticker":kalshi_ticker,"polymarket_token_id":polymarket_token_id,
         "errors":[{"reason_code":"PAIR_CAPTURE_FAILED","error_type":type(exc).__name__}]}
 output.parent.mkdir(parents=True,exist_ok=True);tmp=output.with_suffix(output.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.replace(output);return value


def _quantile(values:list[float],q:float)->float|None:
 if not values:return None
 ordered=sorted(values);position=(len(ordered)-1)*q;lo=math.floor(position);hi=math.ceil(position)
 return ordered[lo] if lo==hi else ordered[lo]+(ordered[hi]-ordered[lo])*(position-lo)


def summarize(paths:list[Path])->dict[str,Any]:
 samples=[];failures=0
 for path in paths:
  value=json.loads(path.read_text())
  if value.get('status')=='complete':samples.append(value)
  else:failures+=1
 skews=[float(x['receipt_skew_ms']) for x in samples]
 latency=[float(x[v]['request_elapsed_ms']) for x in samples for v in ('kalshi','polymarket')]
 return {"schema_version":1,"sample_count":len(samples),"failure_count":failures,
         "receipt_skew_ms":{"p50":_quantile(skews,.5),"p95":_quantile(skews,.95),"max":max(skews) if skews else None},
         "request_elapsed_ms":{"p50":_quantile(latency,.5),"p95":_quantile(latency,.95),"max":max(latency) if latency else None},
         "threshold_status":"INSUFFICIENT_ELAPSED_EVIDENCE" if len(samples)<100 else "READY_FOR_REVIEW"}
