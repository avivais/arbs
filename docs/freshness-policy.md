# Empirical freshness policy — MLB read-only shadow

Version: `mlb-books-2026-08-12-v1`

This policy controls observation/pricing eligibility only. Semantic `REVIEW` decisions remain pricing-ineligible regardless of book freshness.

## Measured basis

The read-only collector accumulated at least 220 paired observations. The reviewed distribution showed:

- receipt-skew p50: 130 ms
- receipt-skew p95: 325.4 ms
- receipt-skew p99: 786.02 ms
- one 20.34 s outlier, which must fail closed
- request-latency p99: 645.47 ms excluding that outlier's effect on percentile

Polymarket source age was captured only after source-time extraction was added, so its initial sample remains too small to derive a stable limit. Kalshi exposes no source timestamp or sequence in this order-book payload.

The Polymarket timestamp represents the source book's latest exposed update, not the local HTTP receipt time. An unchanged but successfully fetched book can therefore carry an old source timestamp. It remains measured for review, while local receipt age and cross-leg receipt skew are the active fail-closed freshness controls.

## Conservative limits

- Pair receipt skew: **800 ms maximum** (rounded above observed p99).
- Local receipt age at calculation: **2,000 ms maximum**.
- Polymarket source age: **not yet enabled as a release threshold**; records retain measured source age and status.
- Kalshi source age: `null`, status `not_exposed`; never inferred.
- Any partial/failed response, invalid/future source timestamp, suspended/empty/crossed book, semantic non-`EXACT` decision, or exceeded limit is ineligible.
- Completed indicator artifacts are published before cumulative historical summarization, so growing retention work cannot age fresh captures out of the alert window.
- Cumulative percentile summaries are rebuilt by separate local maintenance; the five-minute scanner reuses the latest completed summary instead of holding its collection lock for a full historical rescan.

## Re-estimation

Re-estimate only from immutable samples after materially more source-age and movement observations. Tightening may happen automatically after review; loosening requires a new versioned policy and evidence report.
