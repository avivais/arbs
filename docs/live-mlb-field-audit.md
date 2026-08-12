# Live MLB field-coverage audit

Verified against bounded public Kalshi and Polymarket payloads on **2026-08-12**.
Scope: pre-game MLB event-winner markets only. Unknown or ambiguous fields fail closed.

| Canonical/equivalence field | Kalshi source | Polymarket source | Availability | Matcher behavior |
|---|---|---|---|---|
| Venue event ID | `event_ticker` | event `id` | Present | Preserved with source URL |
| Competition | `KXMLBGAME` series | MLB tag `100381` / `sportsMarketType=moneyline` | Present for bounded route | Must equal MLB |
| Participants | event title plus each contract `yes_sub_title` | event title plus moneyline `outcomes` | Present | Exact league-scoped alias lookup; unknowns rejected |
| Scheduled start | Parsed from `rules_primary` text with ET timezone | moneyline market `gameStartTime` | Present | Converted to UTC; must be within 15 minutes |
| Market family | series is game winner | `sportsMarketType=moneyline`, ungrouped market | Present | Non-winner variants rejected |
| Outcome orientation | One binary YES contract per team | Two named outcome tokens | Present | Canonical team IDs must cover both participants |
| Active lifecycle | `status` | `active`, `closed`, `acceptingOrders` | Present | Closed/inactive records rejected |
| Primary rule text | `rules_primary` | event/market `description` | Present | Retained as evidence |
| Postponement/cancellation | `rules_secondary`: delayed/rescheduled within two days; otherwise fair-price resolution | description: remains open until completion; canceled/no makeup or tie resolves 50-50 | Present but materially different | `REVIEW`; pricing/trading ineligible |
| Resolution source | series settlement metadata/rules | `resolutionSource` and description | Partially present | Retained; not sufficient for EXACT |
| Authoritative fixture ID | Not exposed in the accepted market payload | `marketMetadata.opticOddsFixtureId` | One-sided | Participants + start + uniqueness required; no authoritative-ID equality claimed |
| Source payload hash | Available through raw snapshot capture; live checkpoint report has report hash | Same | Partial in checkpoint | Full per-record lineage remains planned; checkpoint cannot become EXACT |
| Executable order book | `/markets/{ticker}/orderbook` | `/book?token_id=...` | Available but out of checkpoint scope | Not fetched for REVIEW matches; no arbitrage claim |

## Fail-closed decisions

- Multiple candidate fixtures with the same participants/start window: reject.
- Unknown or ambiguous aliases: reject.
- Missing scheduled start, winner contract, named outcome tokens, or rule evidence: reject.
- Event identity match with unresolved material payout-rule difference: `REVIEW`, never `EXACT`.
- `REVIEW` records are not eligible for pricing, alerts, account actions, or orders.
