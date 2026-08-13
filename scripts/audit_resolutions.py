#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from arbs.replay import load_match_report
from arbs.resolution_audit import audit_report

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/shadow/latest.json'));p.add_argument('--output',type=Path,default=Path('data/reports/resolution-audit.json'))
a=p.parse_args();report=load_match_report(a.input);value=audit_report(report['matches']);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');print(json.dumps({k:value[k] for k in ('match_count','comparable_count','agreement_count','divergence_count','gate_status')},sort_keys=True))