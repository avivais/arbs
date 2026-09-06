#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from arbs.replay import load_match_report
from arbs.resolution_audit import audit_report

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/shadow/latest.json'));p.add_argument('--history',type=Path,default=Path('data/shadow'));p.add_argument('--output',type=Path,default=Path('data/reports/resolution-audit.json'))
a=p.parse_args()
paths=sorted(a.history.glob('20*.json')) if a.history.exists() else []
# latest.json is an alias copied from the newest immutable timestamped report. Do
# not count that alias as an additional observed report when history is present.
is_history_alias = a.input == a.history / 'latest.json' and bool(paths)
if a.input.exists() and a.input not in paths and not is_history_alias: paths.append(a.input)
# Keep only the latest row per event, not every repeated historical report.
retained={};report_count=0
for path in paths:
 try: report=load_match_report(path)
 except (OSError,ValueError,json.JSONDecodeError): continue
 report_count+=1
 for match in report.get('matches',[]):
  retained[(str(match['kalshi']['event_id']),str(match['polymarket']['event_id']))]=match
matches=[retained[key] for key in sorted(retained)]
value=audit_report(matches);value['report_count']=report_count
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');print(json.dumps({k:value[k] for k in ('report_count','match_count','comparable_count','agreement_count','divergence_count','gate_status')},sort_keys=True))