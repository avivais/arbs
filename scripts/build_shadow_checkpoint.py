#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from arbs.shadow_books import summarize
from arbs.shadow_movement import report

p=argparse.ArgumentParser();p.add_argument('--books',type=Path,default=Path('data/shadow/books'));p.add_argument('--output',type=Path,default=Path('data/reports/shadow-validation-checkpoint.json'))
a=p.parse_args();paths=sorted(a.books.glob('*.json'));timing=summarize(paths);movement=report(paths)
times=[]
for path in paths:
 x=json.loads(path.read_text())
 if x.get('status')=='complete':times.append(datetime.fromisoformat(x['started_at'].replace('Z','+00:00')))
value={'schema_version':1,'generated_at':datetime.now().astimezone().isoformat(),'evidence_window':{'first':min(times).isoformat() if times else None,'last':max(times).isoformat() if times else None,'elapsed_seconds':(max(times)-min(times)).total_seconds() if times else 0},'timing':timing,'movement':{k:v for k,v in movement.items() if k!='transitions'},'semantic_eligibility':'ALL_REVIEW_PRICING_DISABLED','gate_status':'PARTIAL_EVIDENCE_ONLY'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');print(json.dumps(value['movement'],sort_keys=True))