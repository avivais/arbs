# Broad cross-venue discovery

## Live scope

[Live report](https://203157714.clawbud.ai/arbs/docs/discovery.html) · [Evidence JSON](https://203157714.clawbud.ai/arbs/data/discovery/report-latest.json)

This is a **read-only discovery and AI-assisted review pipeline**, not an assertion that matching titles form arbitrage. MLB remains an existing test corpus and monitor, not the product boundary. No order endpoint, capital, account authority, or settlement gate changed.

### Running components

- **Every 30 minutes:** Kalshi open-event catalogs and Polymarket active/open-event keyset catalogs. Each bounded run fetches up to ten pages per venue, category-samples up to 1,000 markets per venue, and persists the next cursor. Cache: at most 10,000 markets received within 24 hours. Every report exposes per-venue request errors, category counts, and incomplete/rotating coverage. This is not exhaustive catalog coverage, market availability, liquidity, or uptime.
- **Candidate retrieval:** weighted title/entity token overlap, bounded cross-venue comparisons, category balancing, stable pair IDs, original rules and source URLs. A maximum of 150 candidate pairs appears in each current report. Retrieval similarity is not a calibrated probability or settlement approval.
- **Every two hours:** up to ten previously unreviewed current pairs are compared by the installed Codex AI runtime in read-only sandbox. Schema-constrained JSON must bind exact current semantic source fingerprints and contain verbatim evidence from both venues. The trusted validator rejects fabricated excerpts, changed sources, unknown/duplicate IDs, and attempted approvals. The model identifies different events, dates, thresholds, boundaries, sources, exception clauses and opposite outcome formulations; it can only label REVIEW or REJECT. A title match can still be rejected after reading the rules.
- **Watchdog:** transition-only alerts for missing/error/stale catalogs (90 minutes) and missing/stale AI heartbeat (six hours). Healthy runs remain silent. A current heartbeat does not establish precision or venue uptime.
- **Artifacts:** atomic latest catalog/report/annotations, seven-day compressed capture archives, bounded annotation/cache storage, and an artifact-only public directory. Private workspace permissions and unrelated web routes are not broadened.

## Pricing and semantic gate

All live broad proposals remain **pricing ineligible**. Deterministic checks enumerate event identity, threshold, boundary, deadline, timezone, resolution source, outcome meaning, exceptional rules and revisions; missing terms are unresolved, never implicitly equal. AI cannot supply trusted policy approvals. Reviewed source text is retained for inspection, and changed source fingerprints invalidate old annotations.

`arbs.broad_pricing.evaluate_proposals` bridges to the existing Decimal/depth `price_pair` engine only when an external trusted policy supplies a version, review evidence, current source fingerprints, every material check, an explicit same/reversed orientation, and reviewed fee models. The API supports injected read-only books and checks book identity/outcome, future/stale/skewed receipt timestamps, depth, fees and a safety buffer. The shipped pipeline supplies **no approvals and no quote provider**. Therefore broad-market live net-profit calculation is deliberately not running; the approved fixture pricing path is exercised with clearly labeled synthetic unit tests only. Existing MLB raw-gap/book monitoring is untouched.

Current bridge direction is left YES plus right NO for same propositions, or left YES plus right YES for reversed propositions. Other leg directions, generic venue-specific live book wiring and reviewed fee schedules belong with an actually validated contract family before broad pricing is activated. A missing qualification is not evidence of zero market opportunity.

AI review is not independent human validation or a measured precision study. Category labels and token retrieval are heuristics; discovery can miss paraphrases, cross-category equivalents, closed/reopened markets, or pairs beyond bounded queues. The next research gate is identifying a genuinely payout-equivalent family, not collecting ordinary MLB finals indefinitely.

## Commands

From the repository root:

```sh
python3 scripts/broad_discovery.py --capture
python3 scripts/broad_discovery.py --queue
python3 scripts/broad_ai_worker.py
python3 scripts/broad_discovery.py --apply /absolute/path/to/reviews.json
python3 scripts/broad_discovery_health.py
bash scripts/quality.sh
```

The `--queue` output is public market data with untrusted source text. Review JSON schema: `config/discovery-ai-schema.json`. Worker output is separately validated before persistence. Queue/capture collisions fail closed under a nonblocking lock; a model response against replaced source material is rejected rather than force-applied. Capture exits nonzero on partial request errors even when it publishes usable partial evidence. Local logs are evidence, not Telegram delivery. Scheduled workers are external configuration, not enabled merely by cloning Git.

### Deployed schedules

- `0c3993b2f1f2`: catalog, every 30 minutes, `~/.hermes/scripts/arbs-broad-capture.sh`, local output.
- `ce9ae7ee7b70`: AI review, every two hours, `~/.hermes/scripts/arbs-broad-ai-run.sh`, local output. The scheduler is script-only, but this script explicitly invokes AI via Codex; it is not deterministic matching presented as AI.
- Health uses `~/.hermes/scripts/arbs-broad-health.sh`; inspect the live scheduler inventory for its exact ID.

The initial Hermes nonstreaming child lane timed out. Direct Codex invocation was smoke-tested, then the complete schema-constrained review and trusted apply path succeeded. Polymarket offset pagination now returns 422 past its ceiling: the implementation uses `/events/keyset` and **`after_cursor`**, not `cursor` or `next_cursor` query parameters (those were observed to repeat the initial page). A nonadvancing cursor produces a visible error.

### Public deployment and rollback

Caddy serves only `/arbs/*` from `/srv/arbs-public`; the pipeline copies an explicit allowlist of non-secret artifacts there. The older workspace preview route can return 403 when OpenClaw restores private directory permissions; the new report does not depend on it. Caddy config was validated and reloaded without restarting unrelated applications. Scoped pre-change backup: `/root/arbs-pre-discovery-Caddyfile.backup`, mode 0600.

To stop this new feature, pause/remove only its three scheduler entries. Existing MLB jobs must remain. To remove web publication, remove only the dedicated `/arbs/*` handler, validate and reload Caddy; do not blindly restore an old whole-host config after unrelated changes. Runtime discovery files may be retained for audit. Never make the raw workspace world-readable to repair preview access.
