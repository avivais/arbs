#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from arbs.replay import load_match_report
from arbs.resolution_audit import audit_report, unique_historical_matches

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/shadow/latest.json'));p.add_argument('--history',type=Path,default=Path('data/shadow'));p.add_argument('--output',type=Path,default=Path('data/reports/resolution-audit.json'))
a=p.parse_args()
paths=sorted(a.history.glob('20*.json')) if a.history.exists() else []
if a.input.exists() and a.input not in paths: paths.append(a.input)
reports=[]
for path in paths:
 try: reports.append(load_match_report(path))
 except (OSError,ValueError,json.JSONDecodeError): continue
matches=unique_historical_matches(reports)
value=audit_report(matches);value['report_count']=len(reports)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');print(json.dumps({k:value[k] for k in ('report_count','match_count','comparable_count','agreement_count','divergence_count','gate_status')},sort_keys=True))