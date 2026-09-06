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

## Deterministic empirical refresh (September 2026)

The daily refresh is now `bash scripts/refresh_validation.sh` (Hermes job
`0e835c92dd33`, daily 03:00 scheduler-local time, local delivery). It uses no
inference and never edits source, commits, or advances acceptance gates. The old
agent job failed before inference because its unpinned model configuration had
drifted; this removes that dependency rather than overriding the spend guard.

- Unit quality: `bash scripts/quality.sh`; fixed fixtures, not the growing live corpus.
- Full evidence: checkpoint captures a publication-mtime cutoff and detects input
  metadata changes before atomic publication. Metadata hashes are not content hashes.
- Runtime generations: `data/shadow/validation/<UTC-generation>/`; `latest.json`
  points to a complete generation with content hashes. A failed run preserves the
  previous pointer. Checkpoint and resolution fetches have distinct timestamps.
- Committed `data/reports/` remains a reviewed release checkpoint, not the daily
  mutable output. The canonical plan is updated deliberately, not auto-promoted.
- Collector telemetry: `data/shadow/health/<run>.json` records boot identity,
  sampled host uptime, scan start/completion and exit status. Missing completion
  is not success. This starts prospectively; historical process uptime cannot be
  reconstructed from artifact cadence alone.
- Public preview repair: `/srv/preview` had mode 0700, causing all existing
  Arbs links to return HTTP 403. Caddy now has a named execute-only ACL on that
  mount root (no directory listing or other-user access); `.openclaw` permissions
  were not broadened. Roll back with `chmod 700 /srv/preview`. A future chmod by
  the workspace owner can mask the ACL again; check actual public HTTP status.
  Atomic public checkpoint files are explicitly 0644 rather than tempfile 0600.
- Resolution audit maps Polymarket winners by exact token ID, never array order.
  Missing/changed/duplicate token IDs cannot establish agreement.

## Incident checklist

Stop scheduling, preserve hashes/logs/database, identify the first affected run, classify adapter/parser/policy/book/storage failure, reproduce offline, add a regression fixture, and only then restart. No incident response may introduce credentials or trading permissions.
