# Fee-aware read-only validation — 17 September 2026

## Verdict and delivery boundary

**INSUFFICIENT EVIDENCE for fee-adjusted opportunity validation.** Continue bounded read-only research; no execution permission. This phase implements a standalone fee/path replay, not another readiness-only check. The implementation and captured evidence are delivered, but full schedule verification is blocked by Kalshi's binding schedule returning HTTP 429. Existing semantic eligibility, quote freshness, raw-gap alerts and trading-disabled behavior are unchanged.

The older generic notional `FeeModel` in `pricing.py` is a configurable test abstraction, **not** an evidenced current venue fee schedule. The new `venue_fees.py` is isolated from live alerts and the empty broad-pricing approval policy. It models nonlinear price-dependent charges and explicitly distinguishes conditional estimates from verified schedules. No synthetic fixture is represented as actual fees, fills or profits.

## Live authoritative findings

Original bytes, URLs, HTTP status, retrieval timestamps and SHA-256 hashes are retained under [`data/fee-validation/2026-09-17`](../data/fee-validation/2026-09-17/source-manifest.json). There are 46 bounded source requests: 45 HTTP 200, one HTTP 429. Page modification/retrieval timestamps are **not** fee effective dates; unknown dates remain JSON null. Capture provenance binds both input and source content hashes.

| Source | Observed facts | Remaining uncertainty |
|---|---|---|
| [Kalshi binding fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf) | HTTP 429; response retained as blocked evidence, not a PDF or fee schedule | Current numerical base rates, exceptions and effective date not verified |
| [Kalshi help](https://help.kalshi.com/trading/fees) | Some markets charge makers; makers pay only upon execution; cancelling resting orders has no fee | No universal maker-free assumption is valid |
| [Kalshi public KXMLBGAME series](https://external-api.kalshi.com/trade-api/v2/series/KXMLBGAME) | `quadratic_with_maker_fees`, multiplier **0.5**; last_updated_ts `2026-09-16T00:29:24.467894Z` | Last update is not a fee effective date; overrides can supersede series parameters |
| [Kalshi event fee changes](https://docs.kalshi.com/api-reference/events/get-event-fee-changes) | Captured event-specific scheduled overrides; e.g. SD–COL multiplier **1**, `quadratic_with_maker_fees`, scheduled `2026-09-17T19:10:00Z` | Do not apply future overrides retrospectively; empty series future-change list is not historical schedule proof |
| [Kalshi rounding](https://docs.kalshi.com/getting_started/fee_rounding) | Model fee rounds up to $0.000001; balances align to $0.0001 direct/$0.01 non-direct; per-order accumulator rebates rounding overpayment | Account precision/order accumulator state unavailable; these mechanical rebates are distinct from liquidity incentives |
| [Polymarket fees](https://docs.polymarket.com/trading/fees) | Prediction-market sports rate .05; formula C × rate × p × (1−p); documented maker zero within applicable product; fees rounded to five decimals | Effective date and exact tie rule absent; prediction-market policy is not a universal statement about other products such as perps |
| [Polymarket market details](https://docs.polymarket.com/market-data/market-details) | Twelve token-bound live Gamma responses all expose sports_fees_v3, rate .05, exponent 1, takerOnly true, rebateRate .15 | CLOB `/fee-rate` reports base_fee=1000 and legacy makerBaseFee/takerBaseFee are 1000: do not reinterpret these as an unconditional 10% charge or maker fee without formula semantics |
| [Maker rebates](https://docs.polymarket.com/programs/maker-rebates) | Performance-based market-pool allocation, discretionary percentage; minimum $1 pUSD accrued payout | Neither rebate allocation nor persistence is guaranteed; credited benefit is zero |

Polymarket's fee page denominates fees in USDC while the rebate page uses pUSD. This source/product denomination discrepancy is retained, not silently assumed convertible at zero cost. The fee page says no Polymarket deposit/withdrawal fee, but intermediary/network/conversion costs and account routing are not established. Taker rebate source is also captured; no membership/tier or rebate is assumed. Kalshi incentives and all conditional rebates are excluded from credits.

## Replay methodology

Commands:

```sh
python3 scripts/capture_fee_evidence.py --directory <new-generation-with-indicators-input.json>
python3 scripts/replay_fee_candidates.py --directory data/fee-validation/2026-09-17
./scripts/quality.sh
```

The capture command refuses to overwrite an existing source manifest. Replay is offline, validates original input/source hashes, is bounded to 12 retained directions, and atomically replaces its single replay JSON only on success. Unit tests use fixed fixtures, not rolling history or network calls.

Input: frozen existing MLB indicator generation `2026-09-17T05:46:40.798683Z`, 78 available directions; replay deliberately selects the first 12 stored rows, **not** an exhaustive or representative whole-market sample. These have full per-leg ask ladders, immutable instrument IDs and receipt/source timing. Both event directions are retained when they occur in the selected population; no claim of complete orientation coverage is made. Broad discovery currently has no settlement-approved candidates or generic quote provider, so this is explicitly a real MLB quote replay, not invented broad-market book coverage.

For each selected direction the replay covers maker/maker, taker/taker, maker/taker, taker/maker, half-maker then taker fallback, and adverse fallback. Requested quantity is 10 contracts; partial paths model five hypothetical maker contracts and five taker fallback contracts. Taker legs walk captured ask depth. Maker prices are hypothetical noncrossing limit prices one cent below the captured ask, **not executable guaranteed fills or queue-position evidence**. Delayed fallback uses historical depth only as a sensitivity assumption; no future liquidity is promised. Adverse stress adds two cents to consumed asks and uses Kalshi multiplier 1 rather than .5. Unfilled-fallback exposure and gross principal at risk are separately recorded, not hidden inside a complete-set profit estimate.

Kalshi base curve rates .07 taker/.0175 maker are explicitly **unverified sensitivity inputs**, not sourced current numerical assertions: the binding PDF is inaccessible. Series multiplier .5 is observed; applicability/effective-date gates remain closed. Polymarket uses exact token-bound feeSchedule evidence, but missing effective dates still block verification. Fee estimates round conservatively per assumed fill; actual trade segmentation and rounding accumulators may change charged fees.

Freshness is recomputed at the original snapshot timestamp using existing 90-second receipt-age/800ms skew policy, without loosening source-age semantics. Replay does not turn old quotes into current quotes. Missing settlement equivalence, historical effective dates, market applicability, account precision, fee minima, order-minimum unit interpretation or required other costs remain REVIEW/INSUFFICIENT EVIDENCE. Settlement, withdrawal, network, funding and conversion costs are separate null inputs; the one-cent-per-pair safety buffer is a sensitivity assumption, not a substitute for those costs. `net_profit` remains null and `pricing_eligible` false for every path, even when conditional arithmetic is positive.

## Discovery and AI operations

See [recovery evidence](broad-recovery-2026-09-17.md). Gamma's official schema permits omitted `next_cursor` on a terminal page; the collector now retains that page and resets the cursor, while malformed/nonadvancing responses still fail closed. A real exact production-wrapper capture was independently executed after the repair: exit 0, generation `2026-09-17T05:58:56.381273Z`, Kalshi 829 events/5,333 active markets seen/1,000 sampled; Polymarket 64 events/333 sampled markets. No request errors. The 10,000-record bounded cache generated 150 REVIEW proposals, zero priced/eligible pairs. This is fresh bounded catalog evidence, **not executable broad coverage** or a whole-market census.

AI job `ce9ae7ee7b70` is still blocked by expired/reused Codex OAuth refresh credentials (HTTP 401). Original diagnostic lines were independently inspected. No new AI call, authentication/account modification, paid fallback or guard bypass was attempted. Owner/operator reauthentication is required to resume that worker; this is the one genuine access action outside the task's authority. Existing collection/review schedules were not changed. After the manual wrapper exercise, the ordinary scheduled discovery run also succeeded at `2026-09-17T09:12:29.703261+03:00`; the scoped evidence is preserved in `broad-recovery/scheduled-recovery.json`. This confirms scheduled collector recovery, not AI authentication recovery.

## Verified replay and tests

Full canonical gate: **243 tests passed, 21 subtests passed**; bytecode compilation,
64-task canonical-plan/generated-view validation, pinned 33-published/38-raw-match
replay checks and whitespace validation passed. The gate now uses pytest to run
both the existing unittest classes and parameterized fee tests; pytest is a declared
optional `test` dependency. No network or rolling-history scan is required by tests.

Real replay: **12 directions × 6 paths = 72 path records**. Nine directions passed
the original capture-time freshness policy: two raw-gap observations and seven
without a raw gap. Three directions failed freshness, so **18 paths were excluded**
and **54 conditional calculations** were produced. **Zero are pricing eligible**.

For the nine freshness-valid directions, the conditional surplus for a ten-contract
complete set, after assumed fees and the $0.10 safety buffer but **before unknown
other costs**, was:

| Path | Calculated | Positive conditional arithmetic | Range per 10-contract set |
|---|---:|---:|---:|
| Hypothetical maker/maker | 9 | 9 | $0.0400 to $0.1000 |
| Hypothetical maker/taker | 9 | 0 | −$0.1884 to −$0.11375 |
| Taker/hypothetical maker | 9 | 0 | −$0.1200 to −$0.0600 |
| Taker/taker | 9 | 0 | −$0.3484 to −$0.26375 |
| Partial maker → taker fallback | 9 | 0 | −$0.2784 to −$0.19375 |
| Adverse partial fallback | 9 | 0 | −$0.62592 to −$0.52855 |

The positive maker/maker figures depend on **two invented fill assumptions at
noncrossing limit prices** and unverified Kalshi base fees. They are not observed
fills, guaranteed executable prices, fee-adjusted profits or GO evidence. Every
record retains `net_profit: null`, excluded costs, source lineage and blockers.
The arithmetic is deterministic sensitivity analysis on real captured asks.

## Evidence needed next

1. Recover the binding numerical Kalshi schedule through normal authorized public access; resolve event overrides, account precision and actual validity intervals.
2. Resolve source currency/minimum/fee endpoint semantics and budget required non-trading costs; retain no guessed zero defaults.
3. Restore authorized AI runtime authentication and verify source-bound review application; find a truly payout-equivalent broad family, with independent review.
4. Only then rerun real books and all path stresses for eligible read-only net-result research. Existing MLB settlement NO-GO is not repaired by fees.
