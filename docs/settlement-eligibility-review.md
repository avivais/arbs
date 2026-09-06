# Exceptional-settlement eligibility review — 6 September 2026

## Verdict: NO-GO for guaranteed cross-venue MLB payout

**41/41 event pairs in the `20260906T045510Z` snapshot have materially different exceptional-settlement rules. Eligible subset: empty.** This is a technical agent review, not owner/legal sign-off. All production pairs remain REVIEW.

The source collection contains **124 HTTP-200 responses**: 82 Kalshi contracts, 41 Polymarket events and the Kalshi series metadata. I inspected the saved original responses, replayed the per-pair checks, and independently fetched the series-linked binding PDF. Its SHA-256 matches the preserved copy: `c08ab9be0b9c9869be07e75674a84def8e0f017d4bb301da3898b25c33fd892b`.

## Sources and scope

- [Kalshi series](https://api.elections.kalshi.com/trade-api/v2/series/KXMLBGAME) links the [binding contract terms](https://assets.kalshi.com/contract_terms/MLBGAME.pdf).
- Every contract/event URL, complete rule excerpt, retrieval time and captured response is preserved in [review JSON](../data/reports/settlement-eligibility-review.json) and its compressed source archive.
- [Preserved PDF](../data/reports/review-evidence/MLBGAME.pdf).
- Replay: `python3 scripts/replay_validation_reviews.py`. All dated inputs are committed, including the historical reports; replay needs neither live APIs nor the rolling retention directory. The script generates the JSON reviews and matching narrative. This settlement narrative records interpretation of the PDF, beyond the phrase checks.

The current terms cannot be silently backdated to historical trades. No assertion is made about past fair-price payouts or actual exceptional settlements.

## Contract differences

| Scenario | Kalshi linked terms | Polymarket captured moneyline description | Assessment |
|---|---|---|---|
| Normal completed game | Official winner; extra innings included | Winning named team | Ordinary result agreement observed, not an all-state guarantee |
| Postponed, started within 48 hours | Remains open for official final | Remains open until completed | Potential agreement, subject to other terms |
| Not started within 48 hours | Last fair market price determined by exchange | Remains open until completed | Material payout/horizon mismatch |
| Cancelled with no makeup | Fair-price treatment under exceptional rules | 50–50 | Fair price is not guaranteed to equal 50 cents |
| Suspended and not resumed within 48 hours | Last fair market price | No equally explicit 48-hour bound in captured description | Equivalence not established |
| Tie, two team strikes and no tie strike | 50 cents each | 50–50 | This isolated case can agree; it does not cure other mismatches |
| Pre-start forfeit | Last fair market price | No equivalent explicit clause in captured description | Unresolved; no normal-result assumption |
| Home/away reversal or delayed venue change | Can trigger fair price | No equivalent explicit clause in captured description | Unresolved |
| Disqualification/corrected result | Specific timing and exchange-review rules | Equivalent detailed treatment not established | Unresolved |

**Important precision:** Kalshi's API summary says the rescheduled game has finished “within two days.” The linked binding PDF distinguishes **started within 48 hours** for postponements and **resumed within 48 hours** for suspensions. Do not turn the API summary into a finish-time rule. Both formulations still fail to establish equivalence with Polymarket's open-ended postponement description.

## Payout counterexamples

For one Kalshi YES on team A plus one Polymarket winner token on team B, let entry cost be `c`, aggregate fees/costs be `f`, and Kalshi's exceptional fair-price payout be `q`.

- Normal A/B winner: combined payout can be 1, giving `1 − c − f`.
- Cancellation/no makeup: combined payout is `q + 0.5`, giving `q + 0.5 − c − f`, not a guaranteed dollar.
- Delay beyond Kalshi's horizon, followed by team A winning: Kalshi can already have paid `q`, while the opposing Polymarket token pays zero. Net is `q − c − f`.

**Illustrative stress case, not a real quote or settlement:** `q = 0.50` and `c = 0.97` in the delayed-A-win case gives **−0.47 before fees**, despite a normal-case three-cent gross gap. The actual fair price is unknown; the point is that the rules do not guarantee the normal combined payout.

No fees or fill model can turn a missing payout guarantee into one. Kalshi series fee metadata was captured, but event overrides and historical fee versions still matter. There are zero eligible cases on which to claim all-cost modeled profitability.

## What is closed and what is not

The immediate question is answered: **we do not merely lack more ordinary finals; we have evidence of materially different exceptional terms across the entire reviewed current set.** More ordinary finals alone cannot promote this set.

Independent labeled precision, prospective reliability, fee/fill completeness and any owner sign-off remain separate gates. The timed-out delegated reviews are not represented as completed independent approval; I finished this review directly from their preserved collection plus my own source verification.
