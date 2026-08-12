# Operations and shadow-validation runbook

## Safety boundary

The service is read-only. It must not receive account credentials, wallets, funds, or order permissions. Every current live MLB match is `REVIEW` and therefore pricing-ineligible.

## Single-owner scanner

Use a systemd timer or equivalent scheduler to run one bounded process. Acquire an exclusive `flock` before scanning; if held, exit successfully without overlap. Apply `RuntimeMaxSec`, memory and CPU limits. Write output atomically, then validate before replacing the latest report.

Canonical one-shot command:

```bash
flock -n data/arbs.lock env PYTHONPATH=src python3 -m arbs.match_live --output data/reports/live-mlb-matches.json
```

## Health checks

A healthy run has a recent completed run record, zero adapter errors, schema-valid captures, policy/parser versions, and bounded latency. Alert operationally on stale last-success time, repeated partial captures, schema drift, parser-coverage drops, or duplicate scheduler ownership.

## Restart and failure behavior

- SIGTERM: finish or abort the current atomic write, then exit.
- Timeout/network failure: preserve a typed partial manifest; never publish it as complete.
- Crash: stale temporary files are non-authoritative; next run validates the last complete artifact.
- Rollback: deploy the previous Git commit; canonical schema versions keep old evidence readable.

## Shadow gate

Remain read-only until **all** are evidenced:

1. Independently reviewed labeled corpus passes the matching precision gate.
2. Several hundred reviewed events over a representative operating window.
3. Measured quote-age, pair-skew and price-movement distributions justify thresholds.
4. Post-resolution agreement and every divergence are investigated.
5. Theoretical fills and net results include depth, fees, safety buffers and invalidation.
6. Signed go/no-go review documents unresolved risks.

## Incident checklist

Stop scheduling, preserve hashes/logs/database, identify the first affected run, classify adapter/parser/policy/book/storage failure, reproduce offline, add a regression fixture, and only then restart. No incident response may introduce credentials or trading permissions.
