"""Fail-closed bridge to the existing executable-depth/Decimal pricing engine.

Review queue output is never sufficient authorization. An externally reviewed,
versioned policy must bind source fingerprints and every material check. This
release ships an empty policy: no live broad-market pair is pricing eligible.
Book fetching occurs ONLY after semantic and fee-policy gates pass.
"""
from datetime import datetime, timezone
from decimal import Decimal
from arbs.discovery_review import fingerprint
from arbs.candidate_discovery import DIMENSIONS
from arbs.pricing import price_pair


def evaluate_proposals(proposals, *, approvals=None, quote_provider=None, now=None):
    approvals = approvals or {}
    now = now or datetime.now(timezone.utc)
    results = []
    for p in proposals:
        a = approvals.get(p['id'], {})
        reason = 'SETTLEMENT_REVIEW_REQUIRED'
        result = {'id': p['id'], 'eligible': False, 'reason': reason}
        valid = (p.get('status') != 'REJECT' and a.get('reviewer_type') == 'independent_policy_review'
                 and a.get('version') and a.get('evidence_url') and a.get('orientation') in ('same', 'reversed')
                 and a.get('left_fingerprint') == fingerprint(p['left'])
                 and a.get('right_fingerprint') == fingerprint(p['right'])
                 and all(a.get('checks', {}).get(k) is True for k in DIMENSIONS))
        if valid:
            fees = a.get('fees', {})
            if not all(fees.get(side) and fees[side].version and
                       fees[side].rate.is_finite() and fees[side].rate >= 0 and
                       all(v.is_finite() and v >= 0 for v in (fees[side].minimum, fees[side].settlement_cost, fees[side].withdrawal_cost))
                       for side in ('left', 'right')):
                result['reason'] = 'REVIEWED_FEE_MODEL_REQUIRED'
            elif quote_provider is None:
                result['reason'] = 'EXECUTABLE_QUOTES_UNAVAILABLE'
            else:
                try:
                    # Same proposition: buy YES at left + NO at right.
                    # Opposite proposition: buy YES at left + YES at right.
                    right_outcome = 'No' if a['orientation'] == 'same' else 'Yes'
                    left = quote_provider(p['left'], 'Yes')
                    right = quote_provider(p['right'], right_outcome)
                    expected = ((left, p['left'], 'Yes'), (right, p['right'], right_outcome))
                    if any(book.venue != m['venue'] or book.contract_id != m['id'] or book.outcome.lower() != outcome.lower()
                           or book.received_at.tzinfo is None or book.received_at > now for book, m, outcome in expected):
                        raise ValueError('book identity/outcome/receipt invalid')
                    opportunity = price_pair(left, right, semantic_pricing_eligible=True, now=now,
                        max_age_ms=30000, max_skew_ms=5000, first_fee=fees['left'], second_fee=fees['right'],
                        safety_buffer_per_contract=Decimal('0.01'), quantity=Decimal('1'))
                    result.update({k: str(v) if isinstance(v, Decimal) else v for k, v in opportunity.__dict__.items()})
                except (ValueError, TypeError, ArithmeticError, OSError) as exc:
                    result['reason'] = 'QUOTE_VALIDATION_FAILED:' + type(exc).__name__
        results.append(result)
    return {'proposals': len(results), 'evaluable': sum('net_profit' in r for r in results),
            'qualifying': sum(r['eligible'] for r in results), 'results': results,
            'read_only': True, 'scope': 'No orders. Unreviewed proposals never fetch books or quote net profit.'}
