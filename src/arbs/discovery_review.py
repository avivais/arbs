"""Evidence-bound AI annotations. Suggestions never confer settlement eligibility."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def fingerprint(market):
    """Hash semantic source content, excluding volatile quotes/receipt timestamps."""
    fields = {k: market.get(k) for k in ('venue', 'id', 'title', 'description', 'rules',
              'close_time', 'outcomes', 'settlement_sources')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_reviews(payload, proposals):
    if not isinstance(payload, dict) or not isinstance(payload.get('reviews'), list):
        raise ValueError('reviews array required')
    indexed = {p['id']: p for p in proposals}
    result, seen = [], set()
    for row in payload['reviews']:
        if not isinstance(row, dict) or row.get('id') not in indexed or row['id'] in seen:
            raise ValueError('unknown or duplicate proposal')
        p = indexed[row['id']]
        if row.get('left_fingerprint') != fingerprint(p['left']) or row.get('right_fingerprint') != fingerprint(p['right']):
            raise ValueError('source fingerprint changed')
        if row.get('verdict') not in ('REVIEW', 'REJECT'):
            raise ValueError('AI may only request review or reject')
        if row.get('orientation') not in ('same', 'reversed', 'unknown'):
            raise ValueError('invalid orientation')
        if not isinstance(row.get('reason'), str) or not 20 <= len(row['reason']) <= 5000:
            raise ValueError('reason must be substantive and bounded')
        if not isinstance(row.get('differences'), list) or not all(isinstance(x, str) for x in row['differences']):
            raise ValueError('differences required')
        for side in ('left', 'right'):
            excerpt = row.get(side + '_excerpt')
            corpus = '\n'.join(str(p[side].get(k, '')) for k in ('title', 'description', 'rules'))
            if not isinstance(excerpt, str) or len(excerpt) < 8 or excerpt not in corpus:
                raise ValueError('evidence must be a verbatim source excerpt')
        result.append({k: row[k] for k in ('id', 'left_fingerprint', 'right_fingerprint',
                      'verdict', 'orientation', 'reason', 'differences', 'left_excerpt', 'right_excerpt')} |
                      {'pricing_eligible': False, 'reviewer_type': 'AI-assisted, not independent human validation',
                       'reviewed_at': datetime.now(timezone.utc).isoformat()})
        seen.add(row['id'])
    return result


def attach_reviews(proposals, reviews):
    by_id = {r['id']: r for r in reviews}
    for p in proposals:
        r = by_id.get(p['id'])
        if r and r.get('left_fingerprint') == fingerprint(p['left']) and r.get('right_fingerprint') == fingerprint(p['right']):
            p['ai_review'] = r
            if r['verdict'] == 'REJECT':
                p['status'] = 'REJECT'
        p['pricing_eligible'] = False
    return proposals
