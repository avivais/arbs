# Arbs validation verdict — 6 September 2026

## Decision

**NO-GO for promoting the current cross-venue MLB pairs to proven net-profit arbitrage or execution design. Continue read-only observation only.**

This is an agent-authored technical evidence review, not owner/legal sign-off. No credentials, accounts, orders or funds were used. No acceptance criterion was weakened and no pair was promoted from REVIEW.

## Refreshed evidence

The committed full-corpus checkpoint freezes publication time at `2026-09-06T05:00:21.837350+00:00`:

| Measure | Verified result |
|---|---:|
| Successful paired-book observations | 311,225 |
| Paired-book evidence window | 590.47 hours |
| Outcome-book pair identities | 688 |
| Historical cross-venue event pairs | 348 |
| Subsequent top-quote changes | 53,598 |
| Failed paired-book samples | 15 |
| Valid scan artifacts | 5,150 |
| Occupied five-minute slots | 4,798 / 7,096 (67.62%) |
| Largest observed scan gap | 2.76 hours |
| Pricing-eligible event pairs | 0 |

The separate public resolution audit, fetched through `2026-09-06T05:17:56.778240Z`, found **302 comparable finals, 302 agreements and zero divergences**. Another 41 pairs remained pending/unknown and five source-date conflicts stayed excluded from resolution comparisons. Different report stages have different cutoffs; they are not one simultaneous market snapshot.

Artifact coverage is **not service uptime**. New collector records now preserve sampled host boot identity/uptime, scan start, completion and exit status; this adds prospective evidence, not invented historical uptime.

## Why normal final-outcome agreement is insufficient

The source-backed review of all **41 current pairs** found materially different exceptional terms in **41/41**. Actual Kalshi contract summaries say cancellation or rescheduling beyond two days resolves to a fair price. The series-linked binding PDF more precisely uses **started within 48 hours** for postponements and **resumed within 48 hours** for suspensions—not necessarily finished within that period. Polymarket's corresponding description carries postponements until completion and uses 50–50 for outright cancellation/no makeup or a tie. These contracts do not promise an identical combined payout in every exceptional state.

A purely illustrative stress case (not an observed settlement or trade): at a 97-cent combined entry cost, a 50-cent Kalshi fair-price payout followed by a losing opposing Polymarket token returns only 50 cents, a **47-cent loss before any fees**. The actual fair-price value is not assumed known. The example shows why a normal-game one-dollar payout cannot be guaranteed from these contract rules.

Fees and realistic partial-fill modeling cannot repair a missing payout-equivalence proof. With zero eligible pairs, the eligible modeled net-result population is empty—not zero profit, not a profitable backtest. Raw-gap alerts remain observations excluding fees and exceptional-settlement risk.

## Repairs delivered

- Replaced the failed model-dependent daily evaluator with a locked deterministic script-only refresh. Its original failure was a pre-inference model-drift spend guard, not a market-data outage. The repaired scheduler run completed successfully with no inference call.
- Daily runtime evidence publishes a complete, content-hashed generation and only then replaces its latest pointer. Failures preserve the previous generation; offline tests exercise failed second-stage and invalid-eligibility paths.
- Removed the unbounded live-corpus scan from the unit quality gate; full empirical rebuild remains separately exercised on real accumulated artifacts.
- Streamed large summary inputs, froze rebuild cutoffs, added metadata-drift checks, and made checkpoint publication atomic. Metadata fingerprints are explicitly not raw-content hashes.
- Hardened the matcher against reverse ambiguity, malformed outcome arrays and fractional-second tolerance overflow. Existing bounded small-page discovery changes were retained and tested.
- Changed resolution attribution from array position to exact Polymarket token identity; missing, changed or duplicate IDs fail closed.
- Added prospective collector lifecycle telemetry and verified a real completed scan.
- Restored existing public Arbs links that returned HTTP 403 with Caddy-only traversal permission on the preview mount, not broader permissions on private OpenClaw directories.
- Corrected the dashboard notice: read-only raw-gap alerts are active, while execution remains disabled.

## Five date conflicts independently corroborated against MLB

I separately fetched the official MLB schedule for each conflicted current date.
All five are consistent with makeup games: MLB's `rescheduledFromDate` equals
the older Polymarket slug date, and the listed game start equals the Kalshi fixture.
A stale URL date was therefore not sufficient evidence of a false match.

| Pair | Original date | Makeup date | MLB gamePk |
|---|---|---|---:|
| STL–CIN | 2026-05-24 | 2026-08-17 | 824514 |
| ATL–CWS | 2026-06-11 | 2026-08-20 | 824589 |
| BOS–NYY | 2026-06-06 | 2026-08-29 | 823539 |
| SF–ATL | 2026-06-18 | 2026-08-31 | 824911 |
| DET–CLE | 2026-06-14 | 2026-09-04 | 824424 |

Original source: `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=<makeup-date>`.
All five requests returned HTTP 200. This resolves the narrow date-discrepancy
question at the evidence-review level; it does not change the production audit's
conservative quarantine or prove exceptional payout equivalence.

## Acceptance gates

P3-08 (independent precision), P5-07 (full representative shadow evidence) and P5-08 (signed execution-design go/no-go) are not declared passed. An agent-assisted corroboration review must not be relabeled as a human-independent labeled release corpus. Historical uptime and eligible modeled profitability remain unproven.

The correct product status is **a functioning read-only cross-venue price-gap monitor**, not a proven risk-free arbitrage strategy. More ordinary-game observations alone cannot solve materially different settlement terms.

## Verification

Final quality gate: **100 tests passed**; 58-task plan validation passed; replay checked 33 published matches and 38 raw-replay matches. Offline review replay reproduced 26 corroborated identities and 41 non-equivalent settlement pairs from the preserved source archives. Public report and dashboard access were exercised after repair. No trading or production eligibility was enabled.

## Evidence links

- [Canonical rolling plan](rolling-plan.html)
- [Full checkpoint](../data/reports/shadow-validation-checkpoint.json)
- [Resolution audit](../data/reports/resolution-audit.json)
- [Operations runbook](operations-runbook.md)
- [Live dashboard](live-matches.html)

The separate identity review corroborated **26/26 purposively selected cases**, including all five date conflicts, using official MLB fixtures and original venue IDs/tokens. No sampled identity mismatch was demonstrated. This was an agent-assisted review, not a blind/human-independent precision benchmark; it does not pass P3-08.

- [Matching review](matching-independent-review.md) · [replayable JSON](../data/reports/matching-independent-review.json)
- [Exceptional-settlement review](settlement-eligibility-review.md) · [per-pair JSON](../data/reports/settlement-eligibility-review.json)

All three delegated reviewers timed out before returning completed reports. I inspected their saved work and source captures, finished the two review reports directly, and independently verified the pipeline through real runs. No timeout was treated as a successful independent sign-off.
