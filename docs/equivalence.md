# Cross-Venue Sports Contract Equivalence Specification

Status: Draft v0.1  
Policy ID: `sports-equivalence-v1`  
Scope: The union of sports markets and leagues discoverable on Kalshi or Polymarket  
Modes: pre-game and live/in-play  

## 1. Purpose

This specification decides whether one Kalshi contract and one Polymarket contract create complementary payouts on the same real-world outcome. It covers all sports leagues and market families through a common taxonomy. A market family is not automatically safe merely because it is listed here: a pair is trade-eligible only when every required field is parsed and every material rule is equivalent.

The matcher returns one of four decisions:

- `EXACT`: same event, outcome predicate, grading period, and material resolution rules. Eligible for pricing.
- `REVIEW`: plausible counterpart, but at least one material rule differs or cannot be proven equal. Never auto-trade.
- `NO_MATCH`: contracts concern different events, predicates, or incompatible outcomes.
- `UNSUPPORTED`: a market cannot yet be represented safely by the canonical schema. Never auto-trade.

This is a matching specification, not authorization to trade.

## 2. Governing principles

1. Full market rules govern; titles and summaries are discovery inputs only.
2. Equivalence means identical payout for every permitted real-world outcome, including cancellation and postponement cases.
3. Missing information never counts as equality.
4. Every decision must be reproducible from immutable source snapshots and a versioned policy.
5. `REVIEW` is not a weaker exact match. It is ineligible for automated arbitrage pricing until a reviewer approves a documented override.
6. The system ingests the union of venue sports catalogs. A market with no cross-venue candidate remains stored as `UNPAIRED`.
7. Live markets require stricter identity and freshness controls than pre-game markets.

## 3. Authoritative venue behavior

Kalshi states that each market has its own rules, verification source, and outcome conditions; its rule summary is not the complete rule text. Market close time may differ from determination time. Polymarket likewise states that every market has predefined resolution rules containing its source, end date, and edge-case handling, and resolves through the UMA Optimistic Oracle. These different settlement mechanisms are operational risk even when the outcome predicates are identical.

Therefore the system must capture, at minimum:

- full rule text or the most complete rule representation exposed by the venue;
- title, subtitle, outcome labels, source URL/name, and all relevant timestamps;
- event and market identifiers;
- venue lifecycle state and resolution state;
- snapshot retrieval time and content hash;
- parser and policy versions.

Official references:

- Kalshi market rules: https://help.kalshi.com/en/articles/13823822-market-rules
- Kalshi rules summary: https://help.kalshi.com/en/articles/13823823-rules-summary
- Kalshi market lifecycle: https://docs.kalshi.com/getting_started/market_lifecycle
- Polymarket resolution: https://docs.polymarket.com/concepts/resolution
- Polymarket markets and events: https://docs.polymarket.com/concepts/markets-events
- Polymarket sports/CLOB behavior: https://docs.polymarket.com/trading/orders/create

## 4. Canonical representation

### 4.1 Event identity

An event is represented by:

- `sport_id`
- `competition_id` (league, tour, tournament, or governing competition)
- `season_id`, when applicable
- canonical participant IDs and roles (home/away, player/team, driver, horse, etc.)
- scheduled start in UTC
- round, stage, heat, race, match, leg, map, set, or game number
- venue or neutral-site flag when it distinguishes events
- authoritative external event ID, when available

Participant order is ignored only for symmetric event identity. Roles remain material to predicates such as home-team scoring.

### 4.2 Contract predicate

A contract is normalized as:

`metric(subject, event_scope, grading_period) operator threshold`

Examples:

- `winner(Lakers, game, regulation_plus_overtime) == true`
- `points(total, game, regulation_plus_overtime) > 224.5`
- `points(LeBron James, game, full_participation_rule) >= 25`
- `winner(Arsenal, match, regulation_only) == true`
- `qualifies(driver_x, qualifying_session, official_classification) == true`

Required predicate fields:

- market family and subtype;
- subject and opponent/field, where relevant;
- statistic or result metric;
- operator and exact decimal threshold;
- selected outcome;
- grading period;
- inclusion of overtime, extra time, shootouts, tie-breaks, maps, sets, innings, laps, or stages;
- participation requirements;
- dead-heat/tie treatment;
- source and correction window;
- cancellation, postponement, abandonment, rescheduling, and venue-change treatment;
- exceptional settlement value behavior (including void, split, 0.5, or fair-value settlement).

## 5. Market-family taxonomy

All discovered sports markets must map to one of these families or become `UNSUPPORTED`:

| Family | Examples | Additional material fields |
|---|---|---|
| `HEAD_TO_HEAD` | game/match winner, moneyline | draw possible, overtime/extra time, best-of format |
| `MULTIWAY_WINNER` | tournament, race, league champion | field definition, each-way/dead heat, withdrawals |
| `HANDICAP` | spread, Asian handicap, puck/run line | line, push rule, quarter-line split |
| `TOTAL` | game/team/player over-under | metric, line, push rule, grading period |
| `BOTH_OR_EITHER` | both teams score, either finalist | Boolean subjects and scope |
| `MARGIN` | winning margin bands | interval endpoints, tie bucket |
| `EXACT_RESULT` | exact score, set score | regulation/final score definition |
| `PLAYER_PROP` | points, shots, touchdowns | participation/DNP and stat-correction rules |
| `TEAM_PROP` | corners, runs, first score | statistic source and period |
| `MILESTONE` | record broken, reaches playoffs | deadline, qualifying event set |
| `STAGE_ADVANCEMENT` | qualifies, reaches semifinal | bracket/stage definition, walkovers |
| `SEASON_FUTURE` | wins division, relegated | season definition, format changes |
| `AWARD` | MVP, top scorer | awarding body, shared awards |
| `COMBINATION` | parlay/combo/MVE | every component plus dependency and payout rule |
| `LIVE_STATE` | next score, current-game winner | event clock/state anchor, suspension behavior |
| `OTHER` | newly discovered type | always `UNSUPPORTED` pending schema extension |

## 6. Candidate generation

Candidate generation is intentionally broader than acceptance.

1. Normalize the sport and competition using versioned aliases.
2. Resolve participants to canonical IDs. Never match unknown participants by substring alone.
3. Prefer a shared authoritative sports-data event ID.
4. Otherwise require compatible participant sets plus competition plus a configurable start-time window.
5. Use stage/game number to separate repeated fixtures, doubleheaders, legs, maps, heats, and tournament rounds.
6. Generate candidates only within the same market family, except for explicit logical-complement mappings.
7. Retain all candidates and rejection reasons.

The initial default start-time tolerance is 15 minutes for scheduled contests. This is a candidate-generation tolerance, not evidence that times are equal. Rescheduled events require rule comparison and usually review.

## 7. Equivalence decision procedure

Apply checks in this order:

1. **Parseability:** both contracts map completely to the canonical representation. Otherwise `UNSUPPORTED`.
2. **Event identity:** sport, competition, participants, stage/game number, and event identity agree. A hard conflict is `NO_MATCH`; unresolved ambiguity is `REVIEW`.
3. **Predicate identity:** metric, subject, scope, operator, threshold, selected result, and grading period agree exactly. Otherwise `NO_MATCH`, unless a proven complement transform applies.
4. **Outcome-space completeness:** paired legs must guarantee the intended combined payout across all possible resolutions. Multi-outcome markets require explicit exhaustive coverage.
5. **Material rule equality:** compare every rule dimension in section 8. Any difference or unknown produces `REVIEW`.
6. **Lifecycle eligibility:** both markets must be tradeable under the chosen pre-game/live mode. Failure means `NO_MATCH_FOR_PRICING`, without destroying the underlying semantic match.
7. **Uniqueness:** if multiple candidates survive, return `REVIEW`.
8. **Evidence:** emit every normalized value, source excerpt/hash, and reason code.

Only a pair passing checks 1–5 with no unknowns receives `EXACT`.

## 8. Material rule matrix

The following fields must be equal for `EXACT`:

| Dimension | Examples of differences that force review |
|---|---|
| Event scope | one scheduled game vs series; first leg vs aggregate |
| Grading period | regulation vs overtime; 90 minutes vs extra time/shootout |
| Official source | league final statistics vs another provider |
| Corrections | immediate result vs revisions accepted through a deadline |
| Postponement | must occur within 24 hours vs seven days |
| Cancellation/abandonment | void vs grade on official result vs alternate payout |
| Venue/opponent change | action stands vs market voided |
| Participation | must start vs any appearance vs no minimum |
| DNP/withdrawal | void vs No vs fair-value settlement |
| Tie/push/dead heat | refund/0.5 vs No vs split payout |
| Format changes | shortened game counts vs requires scheduled length |
| Stat definition | official box score definitions differ |
| Deadline/timezone | UTC cutoff vs local-time cutoff |
| Exceptional authority | venue discretion or emergency rule differs |

Text does not need to be identical. The normalized consequence for every material scenario must be identical.

## 9. Live/in-play requirements

Live matching is allowed by scope but is never assumed equivalent to pre-game matching. In addition to all normal checks, require:

- identical canonical event and live phase;
- source timestamps and local receipt timestamps;
- maximum configurable quote and state age;
- matching period/map/set/inning/quarter and clock state where the predicate depends on them;
- confirmation that neither venue is suspended, delayed, or stale;
- explicit handling of venue order delays and automatic order cancellation behavior;
- a larger configurable execution safety buffer.

If a live predicate was created from different game-state anchors, return `NO_MATCH` even when titles match.

Until quote-age, state-age, and execution safety-buffer thresholds have been selected from measured venue data, live contracts may be ingested and semantically matched but are ineligible for opportunity reporting.

## 10. Manual review

A reviewer may change `REVIEW` to `APPROVED_OVERRIDE` only by recording:

- reviewer identity and timestamp;
- source snapshots examined;
- each differing/unknown rule field;
- a scenario-based explanation proving payout equivalence;
- override expiry, normally at the earlier market close;
- policy and parser versions.

An override applies only to the exact contract pair and snapshots reviewed. It must not silently establish a global alias or rule.

In this phase, `APPROVED_OVERRIDE` remains evidence-only and is not eligible for automated pricing or trading. That eligibility is explicitly deferred to a later project phase.

## 11. Initial acceptance criteria

- Every discovered sports market is stored, including markets offered by only one venue.
- Every parsed market has a canonical family or an explicit `UNSUPPORTED` reason.
- No pair with missing material rules is classified `EXACT`.
- All deterministic decisions include machine-readable evidence and policy version.
- Threshold comparisons use exact decimal values.
- Time comparisons use UTC while retaining original timezone and text.
- Automated tests include all market families and edge cases in the fixture file.
- Precision is prioritized over recall; automated trading remains outside this step.

## 12. Open implementation dependencies

Step 1 defines what must be captured but cannot finalize venue-field mappings until API discovery is completed. Step 2 must verify which endpoints expose full rules, source information, sports metadata, live state, and exceptional settlement terms. Any unavailable required field keeps the corresponding contract out of `EXACT` status.
