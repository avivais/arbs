# arbs

Read-only market discovery and eventual deterministic sports-contract matching between Kalshi and Polymarket.

## Rolling delivery plan

The live project plan is maintained from one canonical source and published in two generated views:

- [Human-readable rolling plan](docs/ROLLING_PLAN.md)
- [Interactive rolling plan](docs/rolling-plan.html)
- Canonical implementation source: [`docs/rolling-plan.json`](docs/rolling-plan.json)

Update `docs/rolling-plan.json` first, then regenerate and validate both views:

```bash
python3 scripts/render_rolling_plan.py
python3 scripts/render_rolling_plan.py --check
```

Browser-local checks in the interactive view are personal working notes; committed JSON status and evidence remain authoritative.

## Requirements

- Python 3.12+
- A current CA bundle (`certifi`, installed with the project)
- Network access to the public production APIs
- No credentials for the current read-only phase

## Connectivity check

From the repository root:

```bash
PYTHONPATH=src python3 -m arbs.connectivity
```

This performs bounded GET requests for three open markets from each venue and fetches Polymarket sports metadata. It does not authenticate or trade.

## Sports catalog snapshot

Run a small production capture while developing:

```bash
PYTHONPATH=src python3 -m arbs.ingest --max-kalshi-series 3 --max-polymarket-sports 3
```

Run a complete capture by omitting both limits:

```bash
PYTHONPATH=src python3 -m arbs.ingest
```

Snapshots are written atomically to `data/raw/sports-<UTC timestamp>.jsonl`. Each begins with a manifest, followed by immutable records containing the complete public payload, source URL, retrieval timing, and SHA-256 content hash.

## Quality gate

Run the canonical offline verification command:

```bash
./scripts/quality.sh
```

It executes unit and adversarial tests, bytecode compilation, rolling-plan/schema checks, pinned replay integrity, and whitespace validation. The pinned replay requires no network access.

## Live matching checkpoint

```bash
PYTHONPATH=src python3 -m arbs.match_live --require-match --output data/reports/live-mlb-matches.json
python3 scripts/render_live_matches.py data/reports/live-mlb-matches.json docs/live-matches.html
```

Event identity, payout-rule equivalence, conservative pricing, and execution are separate gates. Current live MLB matches remain `REVIEW` and pricing-ineligible because postponement/cancellation semantics differ.

Operational and safety documentation:

- [Field audit](docs/live-mlb-field-audit.md)
- [Data retention/redaction](docs/data-retention.md)
- [Operations/shadow runbook](docs/operations-runbook.md)
- [Deferred execution security design](docs/execution-security-design.md)

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Production endpoints currently used:

- Kalshi: `https://external-api.kalshi.com/trade-api/v2`
- Polymarket Gamma: `https://gamma-api.polymarket.com`
- Polymarket CLOB: `https://clob.polymarket.com`
