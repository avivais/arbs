#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from arbs.replay import load_match_report
from arbs.shadow_books import sample_pair,summarize

root=Path('data/shadow/books');stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
report=load_match_report(Path('data/shadow/latest.json') if Path('data/shadow/latest.json').exists() else Path('data/reports/live-mlb-matches.json'))
for m in report['matches'][:10]:
 k=m['kalshi']['contracts'][0]['id'];p=m['polymarket']['contracts'][0]['token_id']
 sample_pair(k,p,root/f'{stamp}-{k}.json')
summary=summarize(sorted(root.glob('*.json')))
Path('data/shadow/book-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,sort_keys=True))
