"""Deterministic retrieval for AI review, NOT a settlement-equivalence classifier."""
from collections import Counter, defaultdict
import hashlib
import math
import re

STOP = set('will the a an be in on at by of to for is and or from before after yes no above below over under than more less not end year price win winner'.split())
ALIASES = {'btc': 'bitcoin', 'eth': 'ethereum', 'fed': 'federal reserve', 'ipo': 'public offering',
           'presidential': 'president', 'elections': 'election', 'rates': 'rate'}
DIMENSIONS = ('underlying_event', 'threshold', 'boundary', 'observation_time', 'timezone',
              'resolution_source', 'outcome_definition', 'exceptions', 'revision_policy')


def tokens(m):
    text = m.get('title', '') + ' ' + m.get('description', '')[:200]
    words = re.findall(r'[a-z0-9]+', text.lower())
    return {v for w in words for v in str(ALIASES.get(w, w)).split() if v not in STOP and len(v) > 1}


def verify_proposal(p):
    left, right = p['left'], p['right']
    checks = {}
    # This is a completeness/comparison screen, not an authoritative interpretation.
    for key in DIMENSIONS:
        a, b = left.get('semantic_fields', {}).get(key), right.get('semantic_fields', {}).get(key)
        checks[key] = {'left': a, 'right': b, 'status': 'MISSING' if a is None or b is None else ('AGREES' if a == b else 'DIFFERS')}
    reasons = [key + ': ' + check['status'] for key, check in checks.items() if check['status'] != 'AGREES']
    for side, m in [('left', left), ('right', right)]:
        if not m.get('rules'):
            reasons.append(side + ': binding rules unavailable')
        if {str(x).lower() for x in m.get('outcomes', [])} != {'yes', 'no'}:
            reasons.append(side + ': binary YES/NO outcome mapping unproven')
    p.update(verification=checks, rejection_reasons=reasons,
             differences=['Catalog close time differs (not necessarily resolution time)'] if left.get('close_time') != right.get('close_time') else [],
             status='REJECT' if any(c['status'] == 'DIFFERS' for c in checks.values()) else 'REVIEW',
             pricing_eligible=False)
    return p


def build_proposals(markets, limit=100):
    left = [m for m in markets if m['venue'] == 'kalshi']
    right = [m for m in markets if m['venue'] == 'polymarket']
    token_sets = [tokens(m) for m in right]
    index, frequency = defaultdict(list), Counter()
    for i, words in enumerate(token_sets):
        frequency.update(words)
        for word in words:
            index[word].append(i)
    pools = defaultdict(list)
    for a in left:
        words = tokens(a)
        # Bound per-market comparisons even when generic terms occur everywhere.
        overlap = Counter(i for word in words for i in index.get(word, []))
        candidates = [i for i, n in overlap.most_common(100) if n >= 2]
        ranked = []
        for i in candidates:
            b = right[i]
            if a['category'] != b['category'] and 'other' not in (a['category'], b['category']):
                continue
            shared = words & token_sets[i]
            # One name with no other overlap is too weak even for this review queue.
            if len(shared) < 2:
                continue
            weights = {w: math.log(1 + len(right) / (1 + frequency[w])) for w in words | token_sets[i]}
            score = sum(weights[w] for w in shared) / max(1, sum(weights.values()))
            if score >= 0.16:
                ranked.append((score, b, sorted(shared)))
        for score, b, shared in sorted(ranked, key=lambda x: (-x[0], x[1]['id']))[:3]:
            identity = a['venue'] + ':' + a['id'] + '|' + b['venue'] + ':' + b['id']
            p = {'id': hashlib.sha256(identity.encode()).hexdigest()[:24], 'left': a, 'right': b,
                 'category': a['category'], 'score': round(score, 6), 'orientation': 'unknown',
                 'retrieval_method': 'weighted lexical aliases v1; AI reviews meaning and inversion',
                 'shared_terms': shared,
                 'evidence': {'left': a.get('rules', '')[:2000], 'right': b.get('rules', '')[:2000]}}
            pools[a['category']].append(verify_proposal(p))
    for rows in pools.values():
        rows.sort(key=lambda x: (-x['score'], x['id']))
    result = []
    # Category-balanced review budget instead of sports monopolizing the queue.
    while len(result) < limit and any(pools.values()):
        for category in ('economics', 'crypto', 'politics', 'sports', 'other'):
            if pools[category] and len(result) < limit:
                result.append(pools[category].pop(0))
    return result
