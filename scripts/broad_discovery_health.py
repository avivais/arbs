#!/usr/bin/env python3
"""Quiet-on-healthy watchdog; alerts on transitions, never calls a trading API."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arbs.discovery_catalog import atomic_json
DATA = ROOT / 'data/discovery'


def problems(catalog, worker, now):
    issues = []
    for label, stamp, maximum in [('catalog', catalog.get('generated_at'), 90*60),
                                   ('AI review worker', worker.get('last_success'), 6*3600)]:
        try:
            age = (now - datetime.fromisoformat(stamp.replace('Z', '+00:00'))).total_seconds()
            if age < -60 or age > maximum:
                issues.append(label + ' stale or future-dated')
        except (ValueError, TypeError, AttributeError):
            issues.append(label + ' missing valid timestamp')
    for venue in ('kalshi', 'polymarket'):
        coverage = catalog.get('coverage', {}).get(venue, {})
        if coverage.get('errors') or not coverage.get('markets_returned'):
            issues.append(venue + ' catalog errors or no markets in last slice')
    return issues


def main():
    def load(name):
        try:
            return json.loads((DATA / name).read_text())
        except (OSError, ValueError):
            return {}
    issues = problems(load('catalog-latest.json'), load('ai-worker-state.json'), datetime.now(timezone.utc))
    old = load('health-state.json').get('issues', [])
    if issues != old:
        if issues:
            print('Arbs broad discovery alert: ' + '; '.join(issues) + '. Read-only; no trading. https://203157714.clawbud.ai/arbs/docs/discovery.html')
        else:
            print('Arbs broad discovery recovered: catalog and AI-review heartbeat are current. No pricing eligibility implied.')
    atomic_json(DATA / 'health-state.json', {'issues': issues, 'checked_at': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    main()
