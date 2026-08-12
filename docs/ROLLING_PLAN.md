# Arbs — Kalshi ↔ Polymarket Sports Arbitrage — Rolling Plan

> **Canonical source:** [`docs/rolling-plan.json`](rolling-plan.json) · **Last verified:** 2026-08-12
> Edit the JSON first, run `python3 scripts/render_rolling_plan.py`, validate, and commit all generated views together.

## Live status

- **Progress:** 8/58 tasks source-verified complete (13%)
- **Current focus:** Phase 1 — build a representative, replayable production evidence corpus for field auditing and normalization.
- **Next action:** `P1-02: capture a bounded representative production corpus.`

| Done | In progress | Next | Blocked | Deferred |
|---:|---:|---:|---:|---:|
| 8 | 1 | 40 | 1 | 8 |

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

**Status:** In progress · **Progress:** 1/9

Turn initial ingestion into a complete, regression-safe evidence corpus for the MVP.

- [x] **P1-01 — Restore a green test baseline** `[Done]`
  - **Acceptance:** All declared unit tests pass; request counting behavior is asserted correctly.
  - **Evidence:** `tests/test_ingestion.py:43 corrected to the seven actual adapter requests`; `Verified 2026-08-12: 8/8 unittest cases pass`
- [ ] **P1-02 — Capture a bounded representative production corpus** `[In progress]`
  - **Acceptance:** Sanitized or ignored replay corpus covers at least 20 representative markets per venue for the initial league/family, plus malformed and edge cases.
- [ ] **P1-03 — Audit venue field coverage against equivalence requirements** `[Next]`
  - **Acceptance:** A checked matrix maps every canonical/material field to endpoint, source field, availability, and fallback; gaps have explicit REVIEW/UNSUPPORTED behavior.
- [ ] **P1-04 — Capture complete market rules and lifecycle evidence** `[Next]`
  - **Acceptance:** Adapters fetch the most authoritative exposed rule text/source and lifecycle fields, or record a typed unavailability reason.
- [ ] **P1-05 — Add deterministic replay fixture loader** `[Next]`
  - **Acceptance:** Tests run offline from pinned sanitized payloads with source metadata and hashes.
- [ ] **P1-06 — Harden pagination, rate-limit, malformed payload, and partial-capture behavior** `[Next]`
  - **Acceptance:** Adversarial tests prove bounded termination, explicit partial/failure manifests, retry limits, and no silent record loss.
- [ ] **P1-07 — Version and validate raw snapshot schema** `[Next]`
  - **Acceptance:** Schema validation rejects invalid manifests/records and a compatibility policy covers future versions.
- [ ] **P1-08 — Add quality tooling and canonical commands** `[Next]`
  - **Acceptance:** One documented command runs formatting/lint, type checks, unit tests, and schema/plan validation in a clean environment.
- [ ] **P1-09 — Document data retention and redaction policy** `[Next]`
  - **Acceptance:** Policy distinguishes ignored raw production captures, sanitized committed fixtures, retention, and prohibited secrets/PII.

### P2 — Canonical sports contracts

**Status:** Next · **Progress:** 0/9

Normalize source-specific payloads into typed, versioned, explainable contracts.

- [ ] **P2-01 — Define versioned canonical data models** `[Next]`
  - **Acceptance:** Typed models cover source identity, event, competition, participants/roles, predicate, grading period, lifecycle, and every material-rule field without float thresholds.
- [ ] **P2-02 — Implement exact time and decimal normalization** `[Next]`
  - **Acceptance:** UTC conversion retains original timezone/text; Decimal parsing preserves exact operators and thresholds; edge cases are tested.
- [ ] **P2-03 — Create league-scoped participant and competition registries** `[Next]`
  - **Acceptance:** Aliases map to stable canonical IDs; unknown/ambiguous aliases fail closed with evidence; unrestricted substring matching is absent.
- [ ] **P2-04 — Implement canonical event identity** `[Next]`
  - **Acceptance:** Identity handles participant roles, start windows, stage/game number, neutral sites, doubleheaders, reschedules, and authoritative IDs.
- [ ] **P2-05 — Implement Kalshi MVP contract parser** `[Next]`
  - **Acceptance:** Representative pre-game head-to-head contracts normalize deterministically; unsupported/missing fields emit reason codes.
- [ ] **P2-06 — Implement Polymarket MVP contract parser** `[Next]`
  - **Acceptance:** Same canonical and failure contract as Kalshi across the replay corpus.
- [ ] **P2-07 — Build normalization evidence records** `[Next]`
  - **Acceptance:** Every normalized value links to source snapshot hash, source field/excerpt, parser version, and transformations.
- [ ] **P2-08 — Make equivalence cases executable** `[Next]`
  - **Acceptance:** The labeled fixture corpus contains full structured inputs and tests every expected decision rather than descriptions only.
  - **Evidence:** `tests/fixtures/equivalence_cases.json currently contains descriptive cases only`
- [ ] **P2-09 — Gate MVP parser quality** `[Next]`
  - **Acceptance:** All labeled MVP fixtures parse reproducibly; unknown fields never become equality; parsing coverage and failure reasons are reported.

### P3 — Candidate generation and deterministic matching

**Status:** Next · **Progress:** 0/8

Produce high-precision, evidence-rich cross-venue equivalence decisions.

- [ ] **P3-01 — Implement broad, bounded candidate generation** `[Next]`
  - **Acceptance:** Candidates require sport/competition/participants and compatible start window, prefer authoritative event IDs, and retain rejection reasons.
- [ ] **P3-02 — Implement ordered equivalence decision engine** `[Next]`
  - **Acceptance:** Parseability, event, predicate, outcome-space, material-rule, lifecycle, uniqueness, and evidence checks run in policy order.
- [ ] **P3-03 — Implement complementary-outcome proof** `[Next]`
  - **Acceptance:** Paired legs guarantee intended combined payout across every resolution state; multiway/incomplete spaces fail closed.
- [ ] **P3-04 — Emit machine-readable decision evidence** `[Next]`
  - **Acceptance:** Every decision contains policy/parser versions, normalized comparisons, source hashes, excerpts, and stable reason codes.
- [ ] **P3-05 — Add ambiguity and uniqueness quarantine** `[Next]`
  - **Acceptance:** Multiple surviving events/contracts, reschedules, repeated fixtures, and unresolved aliases cannot become EXACT.
- [ ] **P3-06 — Add reviewer workflow and expiring overrides** `[Next]`
  - **Acceptance:** Review records capture identity, timestamp, snapshot hashes, scenario proof, differences, and expiry; overrides remain pricing-ineligible in this phase.
- [ ] **P3-07 — Build adversarial and property-based matcher suite** `[Next]`
  - **Acceptance:** Tests cover reversed teams, consecutive games, regulation vs advance, postponement, DNP, pushes, neutral sites, exhibitions, unknowns, and deterministic replay.
- [ ] **P3-08 — Meet matching release gate** `[Next]`
  - **Acceptance:** Zero known false-positive EXACT decisions and at least 99% precision on a sufficiently sized independently reviewed labeled corpus; recall is reported, not optimized at precision's expense.

### P4 — Order books and conservative opportunity pricing

**Status:** Next · **Progress:** 0/8

Turn semantic matches into freshness- and depth-aware executable opportunity records without trading.

- [ ] **P4-01 — Normalize venue order books to a $1 payout model** `[Next]`
  - **Acceptance:** YES/NO sides, price, quantity, tick, sequence/source time, and venue semantics are represented consistently using Decimal.
- [ ] **P4-02 — Capture matched books with timing evidence** `[Next]`
  - **Acceptance:** Book pairs record source and local receipt times, retrieval skew, failures, and atomic comparison identity.
- [ ] **P4-03 — Implement depth walking and common-fill quantity** `[Next]`
  - **Acceptance:** VWAP and maximum common executable quantity are calculated across levels with deterministic rounding tests.
- [ ] **P4-04 — Implement versioned venue fee models** `[Next]`
  - **Acceptance:** Fee schedules, rounding, settlement/withdrawal assumptions, and effective dates are configurable and evidenced.
- [ ] **P4-05 — Measure and set freshness thresholds** `[Next]`
  - **Acceptance:** Quote-age and pair-skew limits derive from observed latency/movement distributions; stale/suspended books are excluded.
- [ ] **P4-06 — Implement conservative opportunity engine** `[Next]`
  - **Acceptance:** Both venue directions compute payout minus depth cost, fees, settlement assumptions, and configurable safety buffer; negative/uncertain cases do not signal.
- [ ] **P4-07 — Add opportunity expiry and invalidation** `[Next]`
  - **Acceptance:** Signals expire on age, book movement, lifecycle change, rule/evidence change, or match supersession.
- [ ] **P4-08 — Verify pricing invariants** `[Next]`
  - **Acceptance:** Adding fees/slippage cannot improve profit; reducing depth cannot increase executable quantity; replay is deterministic; displayed midpoint is never treated as executable.

### P5 — Review surface, operations, and shadow validation

**Status:** Next · **Progress:** 0/8

Make every decision inspectable and measure real-world reliability before any execution work.

- [ ] **P5-01 — Implement persistent audit storage** `[Next]`
  - **Acceptance:** Raw references, normalized contracts, decisions, books, opportunities, reviews, and resolutions have migrations, indexes, lineage, and retention rules.
- [ ] **P5-02 — Build read-only operator review surface** `[Next]`
  - **Acceptance:** Operators can inspect source links/rules, normalized comparisons, reason codes, freshness, book depth, fees, and opportunity math without mutation ambiguity.
- [ ] **P5-03 — Add health, quality, and drift metrics** `[Next]`
  - **Acceptance:** Metrics cover adapter latency/errors, catalog volume, parser coverage, unsupported/review rates, candidate/match rates, stale books, and policy/parser drift.
- [ ] **P5-04 — Run continuously under single-owner scheduling** `[Next]`
  - **Acceptance:** One supervised collector/scanner instance has locks, bounded resources, graceful shutdown, restart safety, health checks, and no overlapping capture corruption.
- [ ] **P5-05 — Create alert policy and deduplication** `[Next]`
  - **Acceptance:** Only fresh qualifying opportunities alert; updates/deduplication/rate limits prevent spam; every alert links to audit evidence.
- [ ] **P5-06 — Audit post-resolution agreement** `[Next]`
  - **Acceptance:** Both venue resolutions are compared to canonical outcomes; every divergence is investigated and feeds policy/fixture updates.
- [ ] **P5-07 — Complete sustained shadow run** `[Next]`
  - **Acceptance:** At least several hundred reviewed events and a representative operating window record theoretical fills, subsequent movement, resolutions, false positives, uptime, and net results after modeled costs.
- [ ] **P5-08 — Pass go/no-go review for execution design** `[Next]`
  - **Acceptance:** A signed evidence summary demonstrates matching precision, data reliability, modeled profitability, failure behavior, and unresolved risks; otherwise remain read-only.

### P6 — Execution and controlled rollout

**Status:** Deferred · **Progress:** 0/9

Design trading as an isolated, explicitly approved subsystem after shadow gates pass.

- [ ] **P6-01 — Confirm legal, jurisdiction, venue, tax, and account requirements** `[Blocked]`
  - **Acceptance:** Owners explicitly approve documented eligibility and operational constraints before credentials or funds are introduced.
  - **Blocker:** Requires owner decisions and real venue/account context.
- [ ] **P6-02 — Design secret, identity, and least-privilege controls** `[Deferred]`
  - **Acceptance:** Credentials are external to Git/logs, scoped minimally, rotatable, audited, and separated between environments.
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

---

The HTML view adds navigation and browser-local working checkboxes. Those local selections are not shared evidence and never change this source-verified plan.
