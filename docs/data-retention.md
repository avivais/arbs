# Data retention and redaction policy

## Data classes

| Class | Git | Retention | Rules |
|---|---|---|---|
| Raw production captures (`data/raw/*.jsonl`) | Prohibited/ignored | 30 days locally, then delete | Public market data only; preserve URL, receipt time, status, duration and hash. |
| Sanitized replay fixtures/reports | Allowed | Repository lifetime | Must contain no headers, cookies, credentials, account IDs, IP addresses, or user PII. Payload integrity hash required. |
| Derived audit database | Prohibited/ignored | 180 days | Contains lineage and decisions; no secrets. Backups follow the same retention. |
| Logs/metrics | Prohibited/ignored | 30 days | Structured reason codes; redact request headers and bodies that can contain secrets. |

## Absolute prohibitions

Never commit or log API keys, bearer tokens, cookies, private keys, wallet seeds, account identifiers, funding information, personal data, or authenticated request/response headers. Public market IDs and public URLs are allowed.

## Sanitization gate

Before a fixture is committed:

1. Restrict it to documented public endpoint fields needed by replay.
2. Search case-insensitively for `authorization`, `cookie`, `api_key`, `secret`, `private_key`, `seed`, `wallet`, `account` and personally identifying fields.
3. Validate its schema and canonical SHA-256.
4. Review `git diff` and run `scripts/quality.sh`.

Raw captures remain immutable while retained. Corrections create a new capture; they never rewrite evidence.
