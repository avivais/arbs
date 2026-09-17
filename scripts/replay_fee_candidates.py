#!/usr/bin/env python3
"""Offline bounded fee-path sensitivity replay. NEVER emits an executable signal."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arbs.indicators import IndicatorLeg, evaluate_candidate, utc
from arbs.pricing import normalize_levels
from arbs.venue_fees import FeeFill, FeeSchedule, quote_fees, MODEL_VERSION

D = Decimal
PATHS = ('maker_maker', 'taker_taker', 'maker_taker', 'taker_maker',
         'partial_maker_taker_fallback', 'partial_adverse_fallback')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def depth_fills(levels, quantity, *, skip=D('0'), adverse=D('0')):
    """Walk retained asks, never replace depth with midpoint or unlimited fills."""
    remaining, fills = quantity, []
    for level in levels:
        removed = min(skip, level.quantity)
        skip -= removed
        take = min(remaining, level.quantity - removed)
        if take:
            price = level.price + adverse
            if price > 1:
                raise ValueError('adverse price exceeds unit payout')
            fills.append(FeeFill(price, take))
            remaining -= take
        if remaining == 0:
            return fills
    raise ValueError('insufficient captured ask depth')


def fee_schedule(leg, role, manifest, market, multiplier):
    source_key = 'kalshi-series' if leg.venue == 'kalshi' else 'polymarket-fees'
    source = manifest['sources'][source_key]
    is_poly = leg.venue == 'polymarket'
    # Kalshi numerical bases remain assumptions: the binding schedule returned 429.
    return FeeSchedule(
        venue=leg.venue, market_id=leg.instrument_id, side='buy:' + leg.outcome,
        role=role, product='sports' if is_poly else 'KXMLBGAME',
        rate=(D('0') if role == 'maker' else D(str(market['feeSchedule']['rate']))) if is_poly
             else D('0.0175') if role == 'maker' else D('0.07'),
        source_url=source['url'], source_hash=source['sha256'],
        retrieved_at=utc(source['retrieved_at']), effective_date=None,
        applicability=True if is_poly else None,
        applicability_provenance='Token-bound Gamma feeSchedule: exponent=1, takerOnly=true; effective date unknown.'
             if is_poly else 'Only fee_type/multiplier verified; numerical bases NOT verified: PDF HTTP 429.',
        multiplier=D('1') if is_poly else multiplier,
    )


def replay(root, limit=12):
    if not 1 <= limit <= 12:
        raise ValueError('replay limit must be 1..12; only 12 metadata captures are frozen')
    input_path = root / 'indicators-input.json'
    source_path = root / 'source-manifest.json'
    snapshot = json.loads(input_path.read_text())
    manifest = json.loads(source_path.read_text())
    if digest(input_path) != manifest['input_sha256']:
        raise ValueError('input hash changed')
    for source in manifest['sources'].values():
        if source.get('path'):
            # Basename-only within the frozen generation permits repository relocation.
            path = root / 'sources' / Path(source['path']).name
            if digest(path) != source['sha256']:
                raise ValueError('source hash changed: ' + path.name)
    series = json.loads((root / 'sources/kalshi-series.capture').read_text())['series']
    multiplier = D(str(series['fee_multiplier']))
    now = utc(snapshot['generated_at'])
    results = []
    for index, row in enumerate(snapshot['records'][:limit]):
        legs = [IndicatorLeg(x['venue'], x['outcome'], x['instrument_id'],
                 normalize_levels((v['price'], v['quantity']) for v in x['ask_levels']),
                 utc(x['received_at']), x['source_time_status'],
                 D(x['source_age_at_receipt_ms']) if x['source_age_at_receipt_ms'] is not None else None)
                for x in row['legs']]
        if [x.venue for x in legs] != ['kalshi', 'polymarket']:
            raise ValueError('unexpected venue order')
        markets = json.loads((root / f'sources/poly-market-{index:02}.capture').read_text())
        if len(markets) != 1:
            raise ValueError('ambiguous market applicability')
        market = markets[0]
        if legs[1].instrument_id not in json.loads(market['clobTokenIds']):
            raise ValueError('market token mismatch')
        fee = market.get('feeSchedule', {})
        if not (market.get('feesEnabled') is True and fee.get('exponent') == 1
                and fee.get('takerOnly') is True and D(str(fee.get('rate'))) == D('.05')):
            raise ValueError('unsupported or changed market fee schedule')
        event_fees = json.loads((root / ('sources/kalshi-event-' + row['event_id'] + '.capture')).read_text())
        candidate = evaluate_candidate(*legs, now=now, quantity_cap=D('10'))
        blockers = ['SETTLEMENT_EQUIVALENCE_NOT_PROVEN', 'KALSHI_NUMERICAL_SCHEDULE_HTTP_429',
                    'FEE_EFFECTIVE_DATES_UNKNOWN', 'KALSHI_ACCOUNT_BALANCE_PRECISION_UNKNOWN',
                    'FEE_MINIMA_UNVERIFIED', 'CURRENCY_ROUTING_UNVERIFIED',
                    'ACTUAL_FILL_SEGMENTATION_UNKNOWN',
                    'OTHER_COST_INPUTS_MISSING', 'POLY_MIN_ORDER_UNIT_REQUIRES_REVIEW',
                    'HISTORICAL_SNAPSHOT_NOT_LIVE_EXECUTABILITY']
        if candidate.status in ('NO_DEPTH', 'UNAVAILABLE_FRESHNESS'):
            blockers.append(candidate.status)
        base = {'event_id': row['event_id'], 'instrument_ids': [x.instrument_id for x in legs],
                'source_row_index': index, 'captured_freshness_status': candidate.status,
                'quote_age_ms_at_snapshot': candidate.quote_age_ms, 'pair_skew_ms': candidate.pair_skew_ms,
                'snapshot_receipts': [x.received_at.isoformat() for x in legs],
                'common_ask_depth': str(min(sum(v.quantity for v in x.asks) for x in legs)),
                'poly_market_id': market['id'], 'poly_fee_schedule': fee,
                'poly_order_min_size_raw': market.get('orderMinSize'),
                'kalshi_series_multiplier_observed_now': str(multiplier),
                'kalshi_event_fee_changes': event_fees,
                'fee_sources_manifest_sha256': digest(source_path),
                'source_effective_at': None,
                'other_costs': dict.fromkeys(('settlement', 'withdrawal', 'network', 'funding', 'conversion')),
                'guaranteed_rebates': '0', 'liquidity_rewards_credited': '0',
                'quantity_requested': '10', 'safety_buffer_per_pair_assumption': '.01'}
        for scenario in PATHS:
            item = dict(base, path=scenario, blockers=list(blockers), status='REVIEW',
                        verdict='INSUFFICIENT_EVIDENCE', pricing_eligible=False, net_profit=None,
                        maker_fill_guaranteed=False, conditional_arithmetic=None)
            if candidate.status in ('NO_DEPTH', 'UNAVAILABLE_FRESHNESS'):
                results.append(item)
                continue
            try:
                roles = {'maker_maker': ('maker','maker'), 'taker_taker': ('taker','taker'),
                         'maker_taker': ('maker','taker'), 'taker_maker': ('taker','maker')}
                total_cost, total_fee, executions = D('0'), D('0'), []
                for li, leg in enumerate(legs):
                    adverse = D('.02') if scenario == 'partial_adverse_fallback' else D('0')
                    if scenario.startswith('partial') and li == 0:
                        # Five hypothetical maker fills, then five fallback taker units.
                        chunks = [('maker', [FeeFill(max(D('.001'), leg.asks[0].price-D('.01')), D('5'))]),
                                  ('taker', depth_fills(leg.asks, D('5'), adverse=adverse))]
                    else:
                        role = roles.get(scenario, ('maker', 'taker'))[li]
                        chunks = [(role, [FeeFill(max(D('.001'), leg.asks[0].price-D('.01')), D('10'))]
                                  if role == 'maker' else depth_fills(leg.asks, D('10'), adverse=adverse))]
                    for role, fills in chunks:
                        schedule = fee_schedule(leg, role, manifest, market,
                                                D('1') if adverse else multiplier)
                        quote = quote_fees(schedule, fills, as_of=now.date(), allow_conditional=True)
                        cost = sum(f.price*f.quantity for f in fills)
                        total_cost += cost
                        total_fee += quote.total_fee
                        executions.append({'venue':leg.venue,'role':role,'fills':[
                            {'price':str(f.price),'quantity':str(f.quantity)} for f in fills],
                            'conditional_cost':str(cost),'conditional_fee_upper_bound':str(quote.total_fee),
                            'fee_blockers':list(quote.blockers),'fee_model':MODEL_VERSION,
                            'fee_schedule_evidence':{
                                'base_rate':str(schedule.rate),'multiplier':str(schedule.multiplier),
                                'product':schedule.product,'side':schedule.side,'minimum_assumption':str(schedule.minimum),
                                'source_url':schedule.source_url,'source_sha256':schedule.source_hash,
                                'retrieved_at':schedule.retrieved_at.isoformat(),'effective_date':None,
                                'applicability':schedule.applicability,
                                'applicability_provenance':schedule.applicability_provenance,
                                'rounding':'ceil_6dp_then_buy_balance_cent_grid_no_accumulator_credit' if leg.venue=='kalshi'
                                    else 'ceil_5dp_conservative_bound_not_exact_venue_rule'},
                            'fee_exact':quote.exact_venue_fee,
                            'liquidity_basis':'HYPOTHETICAL_NONCROSSING_LIMIT_NO_FILL_PROOF' if role=='maker'
                                else 'CAPTURED_ASK_DEPTH_PLUS_HYPOTHETICAL_ADVERSE_SHIFT' if adverse
                                else 'CAPTURED_EXECUTABLE_ASKS_AT_HISTORICAL_RECEIPT'})
                item['conditional_arithmetic'] = {
                    'normal_settlement_payout_assumption':'10', 'cost':str(total_cost),
                    'fee_upper_bound_under_unverified_Kalshi_base_rates':str(total_fee),
                    'safety_buffer_assumption':'.10',
                    'surplus_excluding_unknown_other_costs':str(D('10')-total_cost-total_fee-D('.10')),
                    'executions':executions,
                    'adverse_assumptions':{'ask_shift':str(adverse),'kalshi_multiplier':'1' if adverse else str(multiplier)},
                    'partial_path_unhedged_contracts_before_fallback':'5' if scenario.startswith('partial') else '0',
                    'fallback_guaranteed':False,
                    'unfilled_fallback_max_principal_at_risk':str(total_cost) if scenario.startswith('partial') else None}
            except (ValueError, TypeError, ArithmeticError) as exc:
                item['blockers'].append('PATH_UNAVAILABLE:' + str(exc))
            results.append(item)
    counts = Counter(r['captured_freshness_status'] for r in results[::len(PATHS)])
    return {'version':'fee-replay-1','fee_model_version':MODEL_VERSION, 'read_only':True,
            'verdict':'INSUFFICIENT_EVIDENCE','pricing_eligible':0,
            'snapshot_generated_at':snapshot['generated_at'], 'input_sha256':digest(input_path),
            'source_manifest_sha256':digest(source_path), 'catalog_scope':'Existing MLB captured directions, NOT broad discovery',
            'available_snapshot_directions':len(snapshot['records']), 'replayed_directions':min(limit,len(snapshot['records'])),
            'selection':'first 12 frozen indicator rows; purposive sorted monitor subset, not representative whole market',
            'paths_per_direction':len(PATHS), 'path_count':len(results),
            'conditional_arithmetic_count':sum(r['conditional_arithmetic'] is not None for r in results),
            'freshness_at_capture_counts':dict(counts), 'results':results}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    args = p.parse_args()
    result = replay(args.directory)
    output = args.directory/'replay.json'
    tmp = output.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    tmp.replace(output)
    print(json.dumps({k:v for k,v in result.items() if k != 'results'}, indent=2))

if __name__ == '__main__':
    main()
