#!/usr/bin/env python3
"""Bounded unauthenticated GET fee evidence capture; no account/order endpoints."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import argparse

SOURCES = {
    'kalshi-schedule': 'https://kalshi.com/docs/kalshi-fee-schedule.pdf',
    'kalshi-help': 'https://help.kalshi.com/trading/fees',
    'kalshi-rounding': 'https://docs.kalshi.com/getting_started/fee_rounding.md',
    'kalshi-series-doc': 'https://docs.kalshi.com/api-reference/market/get-series.md',
    'kalshi-event-fees-doc': 'https://docs.kalshi.com/api-reference/events/get-event-fee-changes.md',
    'kalshi-series': 'https://external-api.kalshi.com/trade-api/v2/series/KXMLBGAME',
    'kalshi-series-changes': 'https://external-api.kalshi.com/trade-api/v2/series/fee_changes?series_ticker=KXMLBGAME',
    'polymarket-fees': 'https://docs.polymarket.com/trading/fees.md',
    'polymarket-market-details': 'https://docs.polymarket.com/market-data/market-details.md',
    'polymarket-maker-rebates': 'https://docs.polymarket.com/programs/maker-rebates.md',
    'polymarket-taker-rebates': 'https://docs.polymarket.com/programs/taker-rebates.md',
}

def capture(url, target):
    started = datetime.now(timezone.utc).isoformat()
    try:
        with urlopen(Request(url, headers={'User-Agent': 'arbs-read-only-fee-research/1'}), timeout=25) as response:
            status, body, final = response.status, response.read(2_000_001), response.url
        if len(body) > 2_000_000:
            raise ValueError('source too large')
    except HTTPError as exc:
        status, body, final = exc.code, exc.read(100_000), url
    except (URLError, TimeoutError, ValueError) as exc:
        return {'url': url, 'retrieved_at': started, 'status': None, 'error': type(exc).__name__, 'effective_at': None}
    target.write_bytes(body)
    return {'url': url, 'final_url': final, 'retrieved_at': started,
            'completed_at': datetime.now(timezone.utc).isoformat(), 'status': status,
            'path': str(target), 'sha256': hashlib.sha256(body).hexdigest(),
            'effective_at': None, 'effective_date_note': 'Not inferred from retrieval or page modification date.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    root = args.directory
    target = root / 'sources'
    target.mkdir(parents=True, exist_ok=True)
    if (root / 'source-manifest.json').exists():
        raise SystemExit('Refusing to replace frozen source generation')
    sources = dict(SOURCES)
    inputs = json.loads((root / 'indicators-input.json').read_text())
    # Deterministic bounded population, not whole-market coverage.
    rows = inputs['records'][:12]
    for i, row in enumerate(rows):
        token = next(x['instrument_id'] for x in row['legs'] if x['venue'] == 'polymarket')
        sources[f'poly-market-{i:02}'] = 'https://gamma-api.polymarket.com/markets?clob_token_ids=' + token
        sources[f'poly-rate-{i:02}'] = 'https://clob.polymarket.com/fee-rate?token_id=' + token
    for event in sorted({r['event_id'] for r in rows}):
        sources['kalshi-event-' + event] = 'https://external-api.kalshi.com/trade-api/v2/events/fee_changes?event_ticker=' + event
    results = {key: capture(url, target / (key + '.capture')) for key, url in sources.items()}
    manifest = {'version': 'fee-source-capture-v1', 'sources': results,
                'effective_at': None, 'read_only': True,
                'input_sha256': hashlib.sha256((root / 'indicators-input.json').read_bytes()).hexdigest()}
    temporary = root / 'source-manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(root / 'source-manifest.json')
    print(json.dumps({k: v['status'] for k, v in results.items()}, indent=2))

if __name__ == '__main__':
    main()
