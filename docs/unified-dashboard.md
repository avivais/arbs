# Unified Arbs dashboard

The category-neutral live dashboard is `dashboard.html`. It combines every current published quote-observation direction with the broad cross-venue proposal queue. Categories are filters, not separate products. This is bounded read-only research, not an exhaustive exchange census and not verified trading advice.

## Data and refresh

- Browser polls snapshots every 30 seconds; this does not create new quotes.
- Quote collection runs every 5 minutes. Quotes can therefore become stale between captures under the unchanged 90-second quote-age limit and 800ms cross-leg receipt-skew limit.
- Current captured order-book coverage is the existing bounded MLB sample. Other categories are discovery proposals with no executable prices, not assumed zero-profit markets. UI unification does not secretly expand collection or approve settlement equivalence.
- Broad catalog capture runs every 30 minutes, rotating bounded pages. Retrieval uses a 24-hour, 10,000-market capped cache, and publishes up to 150 category-balanced proposals.
- AI review is scheduled every 120 minutes, up to 10 pending proposals per invocation. The browser shows the last successful worker heartbeat; a recent heartbeat is not a guarantee every proposal was reviewed.
- Source snapshots retain their original timestamps when published. Failed/missing data must never be presented as fresh.

## What is a match?

Broad discovery is candidate retrieval, NOT a proven same-event matching engine. It tokenizes titles plus the first 200 description characters; expands a few aliases (BTC/bitcoin, ETH/ethereum, Fed/Federal Reserve); removes common words; requires at least two shared tokens; ranks using rarity-weighted token overlap; and considers compatible categories. Up to three candidates per Kalshi market survive the lexical threshold, then category-balanced selection caps the queue at 150.

That retrieval score is not a probability of equivalence, profit, or an AI confidence score. Close names can still refer to different dates, meetings, thresholds or settlement rules. For example, a December Bank of England decision and a November decision are different events even if most title words match.

The deterministic screen compares nine semantic fields: underlying event, threshold, boundary, observation time, timezone, resolution source, outcome definition, exceptions, and revision policy. Missing fields require REVIEW; conflicting supplied values require REJECT. Binary outcome mapping and binding rules are also required. These semantic fields are not generally populated from all catalog texts, so lexical proposals must not be interpreted as verified matches.

AI reads supplied rules, distinguishes same/reversed/unknown orientation, and may only REVIEW or REJECT. It must cite verbatim evidence from both markets. Reviews are bound to source fingerprints and no longer attach if source terms change. AI cannot approve pricing or settlement equivalence. Different event dates must be rejected, not treated as complementary legs.

## Money and actionability

Raw quote cost is based on captured asks, not catalog metadata or last-trade prices. Fee schedules and exceptional settlement equivalence remain unverified; net profit is not established. A raw gap is not an arbitrage guarantee. All records remain NON_ACTIONABLE and no order/account/trading action is exposed.

## Publication and reports

`reports.html` is the complete public directory. Research reports are dated snapshots and separately labeled from live feeds. The publisher copies an explicit allowlist to `/srv/arbs-public`; it never publishes account credentials, AI logs, private runtime state or full book archives. Quote collection, discovery publication and successful AI review refresh their public artifacts automatically.

Telegram opportunity alerts and broad-discovery health alerts have been removed at the user's request. Collection, local reporting and AI review schedules continue.

## Release verification — 17 September 2026

- Canonical quality command: `./scripts/quality.sh` — 260 tests and 21 subtests passed; rolling-plan and pinned replay checks passed.
- Public HTTP verification: all 25 unique internal dashboard/report/evidence links checked returned HTTP 200; the larger publication allowlist also passed its initial endpoint checks.
- Real public-page browser tests at 1440px, 390px and 320px: no horizontal document overflow or JavaScript errors; category/search/price filtering, pagination, expanded evidence, legacy redirect and failed-feed last-good retention passed.
- Current feed at verification included 78 captured quote directions plus 150 discovery proposals. These are observation/review rows, not 228 verified opportunities; values vary as collectors run.
- Public quote/discovery JSON was compared against actual producer snapshots, including a subsequent scheduled quote generation; timestamps and contents matched without a manual quote-data refresh.
- AI access restored after human device approval: the actual production wrapper completed at 2026-09-17T15:58:41Z with ten validated, persisted and publicly verified source-bound reviews. All ten rejected different propositions. The two-hour schedule remains enabled; the recovery verification was a direct wrapper run, not a scheduler-run success claim. No login codes, credentials or private AI logs are published here.
