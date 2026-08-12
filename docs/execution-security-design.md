# Execution security design — deferred gate

This document is architecture only. It does not authorize credentials, funding, authenticated venue access, orders, or capital deployment.

## Preconditions

Execution remains disabled until owner-approved legal/account eligibility, sustained shadow evidence, signed go/no-go, explicit capital/loss limits, and a separate production-enablement change.

## Identity and secrets

- Separate read-only data and order identities per venue/environment.
- Secrets live in an external secret store or OS credential service, never Git, database, command line, reports, or logs.
- Rotate and revoke each identity independently; audit retrieval and use.
- Default process environment contains no trading secret.

## Isolated gateways

Each venue gateway exposes a fixed typed interface: validate, quote, submit idempotently, query, cancel, and reconcile. It enforces contract allowlists, maximum quantity/notional, price bounds, freshness, environment, and dry-run mode. Logs contain request IDs and hashes, never signatures or secrets.

## Two-leg state machine

`PLANNED → VALIDATED → LEG1_PENDING → LEG1_FILLED/PARTIAL/REJECTED → LEG2_PENDING → HEDGED`, with terminal `ABORTED`, `UNWIND_REQUIRED`, and `MANUAL_INTERVENTION`. Every transition is persisted atomically and idempotently. Non-atomic legging exposure has a short explicit timeout and bounded hedge/unwind policy.

## Risk controls

Fail closed on stale data, rule drift, unmatched semantics, insufficient balance, venue outage, reconciliation discrepancy, clock skew, duplicate request, or kill switch. Limits include per-trade, event, venue, day, balance, gross exposure, loss and unmatched-leg exposure. A global manual kill switch is external to the process.

## Reconciliation and recovery

Venue orders/fills/positions/cash/settlements are fetched independently and compared with the local ledger. Restart resumes from persisted state only after reconciliation. Any discrepancy disables new orders. Fault tests must cover network loss, stale data, one-leg fills, duplicate responses, process crash, venue downtime, and clock skew.

## Canary and scaling

A canary requires a fresh explicit owner approval specifying capital and loss limits, human confirmation, live monitoring and rollback. Every later limit increase is a separate reversible gate based on realized—not modeled—results and incident-free reconciliation.
