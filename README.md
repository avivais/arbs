# arbs

Read-only market discovery and eventual deterministic sports-contract matching between Kalshi and Polymarket.

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

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Production endpoints currently used:

- Kalshi: `https://external-api.kalshi.com/trade-api/v2`
- Polymarket Gamma: `https://gamma-api.polymarket.com`
- Polymarket CLOB: `https://clob.polymarket.com`
