# Arbs — Kalshi ↔ Polymarket Sports Arbitrage — Rolling Plan

> **Canonical source:** [`docs/rolling-plan.json`](rolling-plan.json) · **Last verified:** 2026-09-02
> Edit the JSON first, run `python3 scripts/render_rolling_plan.py`, validate, and commit all generated views together.

## Live status

- **Progress:** 47/58 tasks source-verified complete (81%)
- **Current focus:** P5-07 — sustained read-only shadow validation: accumulate representative elapsed-window movement, resolution, false-positive, uptime and modeled-result evidence.
- **Next action:** `P5-07: continue scheduled immutable collection beyond the 490.76-hour scan-artifact window and 489.97-hour paired-book window, independently review the five source-identifier date conflicts and the broader corpus, add host/process uptime evidence, and do not advance go/no-go until representative evidence exists.`

| Done | In progress | Next | Blocked | Deferred |
|---:|---:|---:|---:|---:|
| 47 | 1 | 0 | 3 | 7 |

## Mission

Build a deterministic, auditable, read-only-first system that discovers equivalent sports contracts on Kalshi and Polymarket, computes executable cross-venue opportunities conservatively, and graduates to trading only after measured safety gates and explicit owner approval.

## Operating rules

1. Precision before recall: an uncertain pair is REVIEW or UNSUPPORTED, never EXACT.
2. Raw source payloads and hashes remain immutable and replayable.
3. No credentials, account actions, funds, orders, or trading until the execution phase is explicitly approved.
4. Every completed task must cite durable repository evidence and pass its stated acceptance gate.
5. Only one task is in_progress; autonomous work proceeds in listed priority order unless Avi or Yoni redirects it.
6. Scope begins with pre-game binary head-to-head markets; broader families stay in the canonical model but are activated only through measured expansion gates.
7. Generated views must never be edited directly.

## Milestones

| ID | Milestone | Status | Exit gate |
|---|---|---|---|
| `M0` | Specification and repository foundation | **Done** | Equivalence policy, public adapters, immutable snapshot writer, and baseline documentation exist. |
| `M1` | Reliable raw discovery | **In progress** | Green tests; representative bounded captures; documented field coverage; replay fixtures; failure telemetry. |
| `M2` | Canonical contracts | **Next** | Versioned event, participant, predicate, lifecycle, and material-rule models parse the MVP corpus deterministically. |
| `M3` | Deterministic matcher | **Next** | Candidate generation and evidence-rich decisions meet the labeled precision gate on replay fixtures. |
| `M4` | Executable pricing | **Next** | Synchronized books, Decimal depth walking, fees, freshness, and safety buffers produce conservative opportunity records. |
| `M5` | Review surface and shadow run | **Next** | Operators can audit every signal; sustained shadow evidence meets reliability and profitability gates. |
| `M6` | Execution readiness | **Deferred** | Legal/account approval plus execution, reconciliation, limits, and kill-switch gates pass in sandbox/small-capital rollout. |

## Delivery phases

### P0 — Foundation and equivalence policy

**Status:** Done · **Progress:** 7/7

Establish the safety contract, public venue boundaries, and replayable raw evidence.

- [x] **P0-01 — Define cross-venue equivalence decisions and material-rule matrix** `[Done]`
  - **Acceptance:** Specification defines EXACT, REVIEW, NO_MATCH, UNSUPPORTED, lifecycle handling, and all material dimensions.
  - **Evidence:** `docs/equivalence.md`; `config/rules/sports-equivalence-v1.yaml`
- [x] **P0-02 — Create Python 3.12 package and public API adapters** `[Done]`
  - **Acceptance:** Kalshi and Polymarket public endpoints are represented behind testable clients.
  - **Evidence:** pyproject.toml; `src/arbs/adapters/`
- [x] **P0-03 — Implement bounded JSON HTTP behavior** `[Done]`
  - **Acceptance:** Timeouts, transient retry/backoff, JSON validation, request timing, and non-retryable errors are covered.
  - **Evidence:** `src/arbs/adapters/http.py`; `tests/test_adapters.py`
- [x] **P0-04 — Implement union sports catalog capture** `[Done]`
  - **Acceptance:** Kalshi sports series/markets and Polymarket sports/events/markets are captured with pagination safeguards and deduplication.
  - **Evidence:** `src/arbs/ingestion/snapshots.py`
- [x] **P0-05 — Persist atomic immutable JSONL snapshots** `[Done]`
  - **Acceptance:** Manifest and records include complete payload, provenance, timing, and SHA-256; writes are atomic.
  - **Evidence:** `src/arbs/ingestion/snapshots.py:201`; `tests/test_ingestion.py:50`
- [x] **P0-06 — Verify unauthenticated production connectivity** `[Done]`
  - **Acceptance:** All four read-only checks return HTTP 200 without credentials.
  - **Evidence:** `src/arbs/connectivity.py`; `Verified 2026-08-12: Kalshi markets, Polymarket markets/sports/market-types all HTTP 200`
- [x] **P0-07 — Establish rolling-plan system** `[Done]`
  - **Acceptance:** Canonical JSON deterministically generates Markdown and standalone HTML, with validation and public publication.
  - **Evidence:** `docs/rolling-plan.json`; `scripts/render_rolling_plan.py`; `docs/ROLLING_PLAN.md`; `docs/rolling-plan.html`

### P1 — Reliable raw discovery and field audit

**Status:** In progress · **Progress:** 9/9

Turn initial ingestion into a complete, regression-safe evidence corpus for the MVP.

- [x] **P1-01 — Restore a green test baseline** `[Done]`
  - **Acceptance:** All declared unit tests pass; request counting behavior is asserted correctly.
  - **Evidence:** `tests/test_ingestion.py:43 corrected to the seven actual adapter requests`; `Verified 2026-08-12: 8/8 unittest cases pass`
- [x] **P1-02 — Capture a bounded representative production corpus** `[Done]`
  - **Acceptance:** Sanitized or ignored replay corpus covers at least 20 representative markets per venue for the initial league/family, plus malformed and edge cases.
  - **Evidence:** `data/reports/live-mlb-matches.json: bounded 2026-08-12 report includes 76 Kalshi markets, 173 Polymarket events, and 33 normalized pairs`; `tests/test_live_matching.py: malformed/unknown, ambiguity, variant, and time-window edge cases`
- [x] **P1-03 — Audit venue field coverage against equivalence requirements** `[Done]`
  - **Acceptance:** A checked matrix maps every canonical/material field to endpoint, source field, availability, and fallback; gaps have explicit REVIEW/UNSUPPORTED behavior.
  - **Evidence:** `docs/live-mlb-field-audit.md`
- [x] **P1-04 — Capture complete market rules and lifecycle evidence** `[Done]`
  - **Acceptance:** Adapters fetch the most authoritative exposed rule text/source and lifecycle fields, or record a typed unavailability reason.
  - **Evidence:** `src/arbs/matching/live.py retains venue rule/lifecycle evidence`; `docs/live-mlb-field-audit.md documents authoritative fields and typed fail-closed behavior`
- [x] **P1-05 — Add deterministic replay fixture loader** `[Done]`
  - **Acceptance:** Tests run offline from pinned sanitized payloads with source metadata and hashes.
  - **Evidence:** `tests/fixtures/replay/mlb-public-2026-08-12 pins 175 sanitized public raw records with URLs, receipt time, per-payload hashes, corpus hash/counts and redaction declaration; tests/test_raw_corpus.py replays 33 matches offline and rejects tampering/duplicates.`
- [x] **P1-06 — Harden pagination, rate-limit, malformed payload, and partial-capture behavior** `[Done]`
  - **Acceptance:** Adversarial tests prove bounded termination, explicit partial/failure manifests, retry limits, and no silent record loss.
  - **Evidence:** `src/arbs/ingest.py isolates venue failures, always writes retained records and returns distinct complete/partial/failed codes; bounded HTTP handling caps attempts, Retry-After and response bytes; adversarial tests cover retained later failure, exact retries, invalid JSON/size, sanitized errors and bounds.`
- [x] **P1-07 — Version and validate raw snapshot schema** `[Done]`
  - **Acceptance:** Schema validation rejects invalid manifests/records and a compatibility policy covers future versions.
  - **Evidence:** `src/arbs/ingestion/schema.py enforces exact manifest/record fields, versions, status/error contracts, types, venue/kind enums, HTTPS sources, HTTP/receipt bounds, counts and canonical hashes; future versions fail closed.`
- [x] **P1-08 — Add quality tooling and canonical commands** `[Done]`
  - **Acceptance:** One documented command runs formatting/lint, type checks, unit tests, and schema/plan validation in a clean environment.
  - **Evidence:** `scripts/quality.sh is the documented canonical test/compile/plan/replay/diff gate; 32 tests pass.`
- [x] **P1-09 — Document data retention and redaction policy** `[Done]`
  - **Acceptance:** Policy distinguishes ignored raw production captures, sanitized committed fixtures, retention, and prohibited secrets/PII.
  - **Evidence:** `docs/data-retention.md defines raw, fixture, database and log retention plus prohibited secret/PII fields.`

### P2 — Canonical sports contracts

**Status:** Next · **Progress:** 9/9

Normalize source-specific payloads into typed, versioned, explainable contracts.

- [x] **P2-01 — Define versioned canonical data models** `[Done]`
  - **Acceptance:** Typed models cover source identity, event, competition, participants/roles, predicate, grading period, lifecycle, and every material-rule field without float thresholds.
  - **Evidence:** `src/arbs/domain.py defines versioned typed source, event, participant role, predicate, lifecycle and full material-rule models using Decimal.`
- [x] **P2-02 — Implement exact time and decimal normalization** `[Done]`
  - **Acceptance:** UTC conversion retains original timezone/text; Decimal parsing preserves exact operators and thresholds; edge cases are tested.
  - **Evidence:** `decimal_exact and utc_exact reject floats and naive timestamps; NormalizedTime retains original text/timezone; tested edge cases pass.`
- [x] **P2-03 — Create league-scoped participant and competition registries** `[Done]`
  - **Acceptance:** Aliases map to stable canonical IDs; unknown/ambiguous aliases fail closed with evidence; unrestricted substring matching is absent.
  - **Evidence:** `src/arbs/matching/live.py contains an exact league-scoped MLB alias registry; unknown aliases fail closed and are tested.`
- [x] **P2-04 — Implement canonical event identity** `[Done]`
  - **Acceptance:** Identity handles participant roles, start windows, stage/game number, neutral sites, doubleheaders, reschedules, and authoritative IDs.
  - **Evidence:** `src/arbs/event_identity.py compares role-aware participants, bounded starts, stage/game number, neutral-site state, reschedule evidence and shared authoritative-ID namespaces; adversarial tests prove explicit conflicts fail and unknown cross-venue dimensions remain REVIEW.`
- [x] **P2-05 — Implement Kalshi MVP contract parser** `[Done]`
  - **Acceptance:** Representative pre-game head-to-head contracts normalize deterministically; unsupported/missing fields emit reason codes.
  - **Evidence:** Pinned replay now parses all 76 Kalshi market records into 38 events after adding exact corpus-observed A's→ATH and Chicago WS→CWS aliases; every input is retained with lineage and no fuzzy matching.
- [x] **P2-06 — Implement Polymarket MVP contract parser** `[Done]`
  - **Acceptance:** Same canonical and failure contract as Kalshi across the replay corpus.
  - **Evidence:** `Pinned replay parses all 99 Polymarket events, requiring one supported moneyline market and retaining exact source lineage; structured home/away roles are observed but cannot equal unknown Kalshi roles.`
- [x] **P2-07 — Build normalization evidence records** `[Done]`
  - **Acceptance:** Every normalized value links to source snapshot hash, source field/excerpt, parser version, and transformations.
  - **Evidence:** `data/reports/replay-decision-evidence.json carries per-normalized-value payload hashes, source URLs, receipt times, source field paths, bounded excerpts, parser/version context and transformations for all 175 decisions.`
- [x] **P2-08 — Make equivalence cases executable** `[Done]`
  - **Acceptance:** The labeled fixture corpus contains full structured inputs and tests every expected decision rather than descriptions only.
  - **Evidence:** `src/arbs/equivalence_cases.py executes structured full canonical contracts through candidate/equivalence logic for EXACT, REVIEW and NO_MATCH scenarios; tests assert every expected decision.`
- [x] **P2-09 — Gate MVP parser quality** `[Done]`
  - **Acceptance:** All labeled MVP fixtures parse reproducibly; unknown fields never become equality; parsing coverage and failure reasons are reported.
  - **Evidence:** `Pinned raw corpus parses reproducibly: 175 records produce 137 accepted event parses, 38 REVIEW event links and 61 retained unpaired events; unknown dimensions stay REVIEW and all outcomes are reason-coded.`

### P3 — Candidate generation and deterministic matching

**Status:** Next · **Progress:** 7/8

Produce high-precision, evidence-rich cross-venue equivalence decisions.

- [x] **P3-01 — Implement broad, bounded candidate generation** `[Done]`
  - **Acceptance:** Candidates require sport/competition/participants and compatible start window, prefer authoritative event IDs, and retain rejection reasons.
  - **Evidence:** `src/arbs/matching/engine.py generates bounded sport/competition/participant/start candidates and retains uniqueness as an explicit gate.`
- [x] **P3-02 — Implement ordered equivalence decision engine** `[Done]`
  - **Acceptance:** Parseability, event, predicate, outcome-space, material-rule, lifecycle, uniqueness, and evidence checks run in policy order.
  - **Evidence:** Ordered engine checks candidate identity, predicate, lifecycle, complete material rules, equality, uniqueness and evidence fail-closed.
- [x] **P3-03 — Implement complementary-outcome proof** `[Done]`
  - **Acceptance:** Paired legs guarantee intended combined payout across every resolution state; multiway/incomplete spaces fail closed.
  - **Evidence:** `complementary_binary proves complete two-outcome spaces and rejects multiway/incomplete spaces.`
- [x] **P3-04 — Emit machine-readable decision evidence** `[Done]`
  - **Acceptance:** Every decision contains policy/parser versions, normalized comparisons, source hashes, excerpts, and stable reason codes.
  - **Evidence:** `Versioned machine-readable replay evidence retains all 137 parse decisions plus 38 cross-venue decisions with policy/parser/canonical/matcher versions, hashes, excerpts, comparisons, reason codes, scenario proof and explicit disabled pricing.`
- [x] **P3-05 — Add ambiguity and uniqueness quarantine** `[Done]`
  - **Acceptance:** Multiple surviving events/contracts, reschedules, repeated fixtures, and unresolved aliases cannot become EXACT.
  - **Evidence:** Multiple surviving candidates and unresolved aliases return REVIEW or are rejected; adversarial tests pass.
- [x] **P3-06 — Add reviewer workflow and expiring overrides** `[Done]`
  - **Acceptance:** Review records capture identity, timestamp, snapshot hashes, scenario proof, differences, and expiry; overrides remain pricing-ineligible in this phase.
  - **Evidence:** `src/arbs/reviews.py validates immutable sequenced review identity/evidence/expiry/differences/scenario proof; review_events are append-only and tests prove APPROVED_OVERRIDE cannot enable a REVIEW decision.`
- [x] **P3-07 — Build adversarial and property-based matcher suite** `[Done]`
  - **Acceptance:** Tests cover reversed teams, consecutive games, regulation vs advance, postponement, DNP, pushes, neutral sites, exhibitions, unknowns, and deterministic replay.
  - **Evidence:** `Engine/live tests cover reversed ordering, consecutive games, ambiguity, unknowns, predicate/rule differences and deterministic replay.`
- [ ] **P3-08 — Meet matching release gate** `[Blocked]`
  - **Acceptance:** Zero known false-positive EXACT decisions and at least 99% precision on a sufficiently sized independently reviewed labeled corpus; recall is reported, not optimized at precision's expense.
  - **Evidence:** `Requires a sufficiently sized independently reviewed labeled corpus; executable cases and the replay corpus verify deterministic decisions, but no independent reviewer has labeled a sufficiently sized corpus for the 99% precision gate. data/reports/source-identifier-audit.json adds an implementation-independent automated cross-check of 285 retained REVIEW pairs: identifiers corroborate 280 and retain five date conflicts requiring independent review. The report explicitly cannot satisfy the independent-label gate and enables no pricing.`

### P4 — Order books and conservative opportunity pricing

**Status:** Next · **Progress:** 8/8

Turn semantic matches into freshness- and depth-aware executable opportunity records without trading.

- [x] **P4-01 — Normalize venue order books to a $1 payout model** `[Done]`
  - **Acceptance:** YES/NO sides, price, quantity, tick, sequence/source time, and venue semantics are represented consistently using Decimal.
  - **Evidence:** `src/arbs/pricing.py represents $1-payout Decimal books with outcome, levels, tick, sequence, source/receipt time and venue.`
- [x] **P4-02 — Capture matched books with timing evidence** `[Done]`
  - **Acceptance:** Book pairs record source and local receipt times, retrieval skew, failures, and atomic comparison identity.
  - **Evidence:** `Atomic collector records complete/failure pairs, shared identity, hashes, local receipt times/skew, Polymarket source timestamp/hash/age, and explicit Kalshi source_time_status=not_exposed; 220 samples retained.`
- [x] **P4-03 — Implement depth walking and common-fill quantity** `[Done]`
  - **Acceptance:** VWAP and maximum common executable quantity are calculated across levels with deterministic rounding tests.
  - **Evidence:** Depth walking computes exact Decimal VWAP and maximum common quantity; multi-level tests pass.
- [x] **P4-04 — Implement versioned venue fee models** `[Done]`
  - **Acceptance:** Fee schedules, rounding, settlement/withdrawal assumptions, and effective dates are configurable and evidenced.
  - **Evidence:** Versioned FeeModel includes effective date, rounding, minimum, settlement and withdrawal assumptions.
- [x] **P4-05 — Measure and set freshness thresholds** `[Done]`
  - **Acceptance:** Quote-age and pair-skew limits derive from observed latency/movement distributions; stale/suspended books are excluded.
  - **Evidence:** `docs/freshness-policy.md and config/freshness/mlb-books-2026-08-12-v1.json derive a conservative 800ms pair-skew limit from the original 220-observation checkpoint; the 2026-09-02 elapsed checkpoint has 236,727 successful samples across 562 pairs over 489.97h, p99 590ms and a retained 30.79s fail-closed outlier. Polymarket source-age p99 is 3,321.50s and remains measurement-only, so the existing reviewed limits are not loosened or expanded pending a new policy version.`
- [x] **P4-06 — Implement conservative opportunity engine** `[Done]`
  - **Acceptance:** Both venue directions compute payout minus depth cost, fees, settlement assumptions, and configurable safety buffer; negative/uncertain cases do not signal.
  - **Evidence:** `Conservative engine gates semantic eligibility, age/skew/depth, fees and safety buffer; negative/uncertain cases do not qualify.`
- [x] **P4-07 — Add opportunity expiry and invalidation** `[Done]`
  - **Acceptance:** Signals expire on age, book movement, lifecycle change, rule/evidence change, or match supersession.
  - **Evidence:** `Age/skew and semantic changes invalidate opportunities; src/arbs/alerts.py adds explicit signal expiry and evidence-key dedup.`
- [x] **P4-08 — Verify pricing invariants** `[Done]`
  - **Acceptance:** Adding fees/slippage cannot improve profit; reducing depth cannot increase executable quantity; replay is deterministic; displayed midpoint is never treated as executable.
  - **Evidence:** `Tests prove fees cannot improve profit, reduced depth cannot increase quantity, and displayed/indicative prices are not executable inputs.`

### P5 — Review surface, operations, and shadow validation

**Status:** Next · **Progress:** 6/8

Make every decision inspectable and measure real-world reliability before any execution work.

- [x] **P5-01 — Implement persistent audit storage** `[Done]`
  - **Acceptance:** Raw references, normalized contracts, decisions, books, opportunities, reviews, and resolutions have migrations, indexes, lineage, and retention rules.
  - **Evidence:** `src/arbs/audit.py now applies versioned SQLite migrations with foreign keys/indexes, append-only triggers and complete lineage tables; tests verify immutable decisions plus integrity-checked backup/restore counts.`
- [x] **P5-02 — Build read-only operator review surface** `[Done]`
  - **Acceptance:** Operators can inspect source links/rules, normalized comparisons, reason codes, freshness, book depth, fees, and opportunity math without mutation ambiguity.
  - **Evidence:** `docs/operator-review.html is a mutation-free 33-row source-linked operator view; browser QA found no controls or overflow and all opportunities disabled.`
- [x] **P5-03 — Add health, quality, and drift metrics** `[Done]`
  - **Acceptance:** Metrics cover adapter latency/errors, catalog volume, parser coverage, unsupported/review rates, candidate/match rates, stale books, and policy/parser drift.
  - **Evidence:** `src/arbs/metrics.py covers requests/errors/latency, volume, coverage, unsupported/review/exact rates, stale books and version drift.`
- [x] **P5-04 — Run continuously under single-owner scheduling** `[Done]`
  - **Acceptance:** One supervised collector/scanner instance has locks, bounded resources, graceful shutdown, restart safety, health checks, and no overlapping capture corruption.
  - **Evidence:** A locked bounded read-only scanner is scheduled every 5 minutes as cron job d0baed088b0b; a forced run succeeded and wrote a validated 33-match shadow artifact.
- [x] **P5-05 — Create alert policy and deduplication** `[Done]`
  - **Acceptance:** Only fresh qualifying opportunities alert; updates/deduplication/rate limits prevent spam; every alert links to audit evidence.
  - **Evidence:** `src/arbs/alerts.py enforces fresh signal expiry, evidence-hash dedup and cooldown; alert records carry audit URLs.`
- [x] **P5-06 — Audit post-resolution agreement** `[Done]`
  - **Acceptance:** Both venue resolutions are compared to canonical outcomes; every divergence is investigated and feeds policy/fixture updates.
  - **Evidence:** `src/arbs/resolution_audit.py and scripts/audit_resolutions.py retain deduplicated historical matches after catalog rollover, cross-check source identifiers before fetching outcomes, hash public venue evidence, recognize Kalshi finalized status, select one Polymarket moneyline, require unambiguous winners, and fail closed. Live 2026-09-02 audit covered 285 historical matches from 4,304 validated reports: 233 are comparable finals with 233 agreements and 0 divergences, while 52 pending, unknown or identifier-conflicted matches remain fail-closed; data/reports/resolution-audit.json is READY_FOR_REVIEW and remains pricing-ineligible.`
- [ ] **P5-07 — Complete sustained shadow run** `[In progress]`
  - **Acceptance:** At least several hundred reviewed events and a representative operating window record theoretical fills, subsequent movement, resolutions, false positives, uptime, and net results after modeled costs.
  - **Evidence:** `data/reports/shadow-validation-checkpoint.json records 236,727 successful paired-book observations across 562 pairs over 1,763,884 seconds (489.97h), with 236,165 subsequent transitions, 40,358 top-quote changes and 13 fail-closed samples. data/reports/resolution-audit.json covers 285 retained historical matches, with 233/233 comparable final-outcome agreements, 0 divergences and 52 pending, unknown or identifier-conflicted matches kept fail-closed. Operational tooling measures 4,306 valid scan artifacts over 1,766,722 seconds (490.76h), 3,954/5,890 occupied five-minute slots (67.13%) and a 9,211.95s largest observed gap, explicitly scoped as artifact coverage rather than host/process uptime; it confirms all 285 unique event pairs remain REVIEW, zero are pricing-eligible, and modeled net results are not computable. An independent parser implementation cross-checks source identifiers for all 285 pairs, corroborating 280 while quarantining five date conflicts; the resolution audit excludes those conflicts, and this automated evidence is explicitly not independent review. This is durable partial latency, movement, resolution, parser-decision and collection-continuity evidence, but not yet a representative window or several hundred independently reviewed events; independent false-positive review, host/process uptime and eligible modeled net results remain unavailable.`
- [ ] **P5-08 — Pass go/no-go review for execution design** `[Blocked]`
  - **Acceptance:** A signed evidence summary demonstrates matching precision, data reliability, modeled profitability, failure behavior, and unresolved risks; otherwise remain read-only.
  - **Evidence:** `Blocked: P3-08 lacks a sufficiently sized independently reviewed corpus and P5-07 still lacks a representative window, several hundred independently reviewed events, host/process uptime, false-positive review and eligible modeled net results. Artifact coverage is only 3,954/5,890 observed five-minute slots with a 9,211.95s maximum gap; all 285 unique event pairs remain REVIEW/pricing-disabled, and five source-identifier date conflicts require independent review. P5-06 has 233/233 comparable final agreements with 52 retained matches pending, unknown or identity-conflicted, but no signed go/no-go summary exists.`

### P6 — Execution and controlled rollout

**Status:** Deferred · **Progress:** 1/9

Design trading as an isolated, explicitly approved subsystem after shadow gates pass.

- [ ] **P6-01 — Confirm legal, jurisdiction, venue, tax, and account requirements** `[Blocked]`
  - **Acceptance:** Owners explicitly approve documented eligibility and operational constraints before credentials or funds are introduced.
  - **Blocker:** Requires owner decisions and real venue/account context.
- [x] **P6-02 — Design secret, identity, and least-privilege controls** `[Done]`
  - **Acceptance:** Credentials are external to Git/logs, scoped minimally, rotatable, audited, and separated between environments.
  - **Evidence:** `docs/execution-security-design.md specifies external secrets, separate least-privilege identities, rotation, auditing and environment separation.`
- [ ] **P6-03 — Implement isolated order gateways** `[Deferred]`
  - **Acceptance:** Authenticated venue clients enforce idempotency, limits, validation, dry-run/sandbox modes, and complete request/response audit without secret leakage.
- [ ] **P6-04 — Implement two-leg execution state machine** `[Deferred]`
  - **Acceptance:** Partial fills, rejection, timeout, cancel/replace, hedge/unwind, and non-atomic legging risk have explicit bounded states and tests.
- [ ] **P6-05 — Add pre-trade risk controls and kill switches** `[Deferred]`
  - **Acceptance:** Per-trade/day/venue/event exposure, balance, loss, staleness, divergence, and manual/global kill switches fail closed.
- [ ] **P6-06 — Implement reconciliation and incident recovery** `[Deferred]`
  - **Acceptance:** Orders, fills, positions, cash, and settlements reconcile independently; restart and discrepancy runbooks are exercised.
- [ ] **P6-07 — Complete sandbox and fault-injection campaign** `[Deferred]`
  - **Acceptance:** Network loss, stale data, one-leg fills, duplicate responses, venue downtime, process crash, and clock skew pass deterministic recovery tests.
- [ ] **P6-08 — Run owner-approved small-capital canary** `[Deferred]`
  - **Acceptance:** Explicit capital/loss limits, human confirmation, live monitoring, and rollback are approved; results are reviewed before scaling.
- [ ] **P6-09 — Scale only through measured gates** `[Deferred]`
  - **Acceptance:** Each increase requires sustained reconciliation, realized profitability, incident-free operation, and owner sign-off; limits remain reversible.

## Decisions

| ID | Date | Decision | Why |
|---|---|---|---|
| `D-001` | 2026-08-12 | Use one canonical JSON plan and generate Markdown plus standalone interactive HTML from it. | Prevents drift while serving implementation and stakeholder needs. |
| `D-002` | 2026-08-12 | Implement a narrow pre-game head-to-head vertical slice first while preserving the all-sports taxonomy. | Produces measurable precision sooner without discarding the broader equivalence design. |
| `D-003` | 2026-08-12 | Keep all work read-only through shadow validation; trading is a separately approved phase. | No real-account or money risk is needed to validate ingestion, matching, and pricing. |
| `D-004` | 2026-08-12 | Treat exact material-rule evidence as mandatory for EXACT. | Similar titles or missing rule fields cannot prove payout equivalence. |
| `D-005` | 2026-08-12 | Treat deterministic event-identity matches as REVIEW until cancellation and postponement payout equivalence is proven. | Live MLB payloads expose materially different fair-price versus 50-50/carry-forward behavior; matched titles and starts alone are not trade-safe. |

## Risk register

| ID | Severity | Risk | Mitigation |
|---|---|---|---|
| `R-001` | **CRITICAL** | Venue APIs may not expose enough authoritative rule detail to prove exact payout equivalence. | Field audit; fail closed to REVIEW/UNSUPPORTED; investigate official rule endpoints before matching. |
| `R-002` | **CRITICAL** | Cross-venue fills are non-atomic and can leave an unhedged position. | No execution before P6; model legging risk, state machine, exposure limits, and kill switches. |
| `R-003` | **HIGH** | Catalog, schema, fee, or resolution behavior can drift without code changes. | Version evidence, schema checks, volume/drift metrics, replay tests, and post-resolution audits. |
| `R-004` | **HIGH** | Quote skew, stale books, fees, rounding, and insufficient depth can turn apparent edge into loss. | Synchronized timing evidence, Decimal depth walking, measured freshness limits, all-cost pricing, and safety buffer. |
| `R-005` | **HIGH** | Ambiguous participants, reschedules, repeated fixtures, and market variants can create false matches. | Canonical IDs, authoritative event mapping, stage/game identity, ambiguity quarantine, adversarial fixtures. |
| `R-006` | **MEDIUM** | Human/public plan views can drift from implementation status. | Canonical JSON, deterministic generation, CI-style validation, evidence requirement, and same-commit updates. |
| `R-007` | **MEDIUM** | Quality tooling remains incomplete despite a green baseline test suite. | P1-08 will establish one canonical verification command covering formatting/lint, types, tests, schemas, and plan generation. |

## Change log

- **2026-08-12** — Created evidence-backed rolling plan; marked repository foundation complete, raw discovery in progress, and execution deferred.
- **2026-08-12** — Corrected the stale union-capture request assertion; all eight baseline tests now pass; advanced active work to representative production corpus capture.
- **2026-08-12** — Captured and published a bounded live MLB checkpoint: 33 unique cross-venue event-identity matches from 76 Kalshi markets and 173 Polymarket events; all remain REVIEW and pricing-ineligible due to material rule differences.
- **2026-08-14** — Extended shadow evidence to 33.59 hours and 5,650 paired-book observations; fixed catalog-rollover/finalized-status gaps in the historical resolution audit and verified 21/21 comparable final-outcome agreements with zero divergences.
- **2026-08-15** — Extended shadow evidence to 57.57 hours and 21,650 paired-book observations across 146 pairs; measured fail-closed scan-artifact coverage and semantic eligibility/modeling blockers; verified 25/25 comparable final-outcome agreements with zero divergences.
- **2026-08-16** — Extended shadow evidence to 81.58 hours and 39,162 paired-book observations across 172 pairs; measured 6,153 top-quote changes and verified 43/43 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-17** — Extended shadow evidence to 105.53 hours and 56,094 paired-book observations across 204 pairs; measured 9,684 top-quote changes and verified 67/67 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-18** — Extended shadow evidence to 129.58 hours and 72,922 paired-book observations across 224 pairs; measured 11,391 top-quote changes and verified 69/69 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-19** — Extended shadow evidence to 153.57 hours and 88,547 paired-book observations across 240 pairs; measured 13,111 top-quote changes and verified 79/79 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-20** — Extended shadow evidence to 177.70 hours and 102,823 paired-book observations across 258 pairs; measured 16,534 top-quote changes and verified 99/99 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-22** — Extended shadow evidence to 225.56 hours and 117,630 paired-book observations across 258 pairs; measured 18,607 top-quote changes and verified 119/119 comparable final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-23** — Extended scan-artifact evidence to 250.34 hours and paired-book evidence to 231.04 hours with 118,332 observations across 258 pairs; measured 19,151 top-quote changes and verified all 133/133 retained final-outcome agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-24** — Extended fail-closed scan-artifact evidence to 274.48 hours and 2,691 validated reports, reverified 133/133 final-outcome agreements with zero divergences, and recorded that paired-book evidence remains at 231.04 hours while preserving REVIEW/pricing-disabled gates.
- **2026-08-26** — Adapted the fail-closed Kalshi parser to the observed outcome-level title schema, restored paired-book accumulation, and extended evidence to 321.69 paired-book hours/131,486 samples across 372 pairs and 322.50 scan-artifact hours; verified 143/143 comparable final agreements with zero divergences while preserving REVIEW/pricing-disabled gates.
- **2026-08-27** — Extended evidence to 345.56 paired-book hours/145,361 samples across 408 pairs and 346.36 scan-artifact hours; verified 162/162 identity-corroborated comparable final agreements and independently cross-checked source identifiers for 208 REVIEW pairs, quarantining three date conflicts from resolution comparison without advancing independent-review or pricing gates.
- **2026-08-28** — Extended evidence to 369.56 paired-book hours/159,341 samples across 442 pairs and 370.35 scan-artifact hours; verified 173/173 identity-corroborated comparable final agreements and cross-checked source identifiers for 225 REVIEW pairs, retaining three date conflicts without advancing independent-review or pricing gates.
- **2026-09-01** — Extended evidence to 465.87 paired-book hours/217,634 samples across 538 pairs and 466.67 scan-artifact hours; verified 222/222 identity-corroborated comparable final agreements and cross-checked source identifiers for 273 REVIEW pairs, retaining four date conflicts without advancing independent-review or pricing gates.
- **2026-09-02** — Extended evidence to 489.97 paired-book hours/236,727 samples across 562 pairs and 490.76 scan-artifact hours; verified 233/233 identity-corroborated comparable final agreements and cross-checked source identifiers for 285 REVIEW pairs, retaining five date conflicts without advancing independent-review or pricing gates.

---

The HTML view adds navigation and browser-local working checkboxes. Those local selections are not shared evidence and never change this source-verified plan.
