# Broad discovery recovery — 2026-09-17

## Outcome

- **Capture defect repaired in the worktree:** Gamma omits its optional `next_cursor` on the terminal page. The collector incorrectly rejected that valid response and retried from the previous cursor on subsequent captures.
- **AI remains blocked, not repaired or verified online:** the existing Codex worker log proves OAuth refresh-token reuse / expired authentication and HTTP 401. No AI invocation, login, credential inspection, provider switch, paid fallback, or authentication workaround was attempted.
- No scheduler entries were added, edited, paused, or triggered. Both specified jobs were enabled at inspection. The AI job will continue failing until an authorized operator resolves or contains it. Core scanning, alerts, pricing eligibility and trading paths were unchanged.

Baseline: repository HEAD `67105dddcfcdfdae4e21fea24b7e1904e3d145d6`. Evidence collected around `2026-09-17T05:53Z`. No commit created.

## Observed failures

### Capture — `0c3993b2f1f2`

Wrapper: `/root/.hermes/scripts/arbs-broad-capture.sh` → `timeout 600 python3 scripts/broad_discovery.py --capture`.

Latest inspected scheduler run: `2026-09-17T08:41:17.060176+03:00`, exit 2. Its stdout contains only aggregate counts; the detailed failure is in `data/discovery/catalog-latest.json` (generation `2026-09-17T05:40:58.694904Z`):

- Kalshi: ten pages, 1,000 events, 1,000 sampled markets, no errors.
- Polymarket: one accepted page, then `ValueError: missing/invalid keyset cursor`.

A bounded unauthenticated GET at the persisted Polymarket cursor returned a valid JSON object with `$schema` and 36 events, **without** `next_cursor`. Its official schema at <https://gamma-api.polymarket.com/schemas/EventsKeysetListResponse.json> declares only `events` required; `next_cursor` is optional and string-typed when present. This was a parser/terminal-pagination defect, not a demonstrated API access denial.

The fix accepts omitted terminal cursors, retaining the final page and resetting the next capture position to the beginning. Existing null/empty cursor handling is retained. Invalid cursor types, malformed event payloads, fetch errors, nonadvancing cursors, locking, request bounds, sampling and incomplete-coverage labels remain fail-closed/unchanged. Reaching the end of a rotating sample does **not** set `complete_catalog=true`.

### AI — `ce9ae7ee7b70`

Wrapper: `/root/.hermes/scripts/arbs-broad-ai-run.sh` → `timeout 600 python3 scripts/broad_ai_worker.py`.

Latest inspected scheduler run: `2026-09-17T08:15:16.314241+03:00`, exit 1, `RuntimeError: Codex review failed; see private ai-worker-last.log`.

Relevant existing log diagnostics, without credential material:

- `Your access token could not be refreshed because your refresh token was already used. Please log out and sign in again.`
- `HTTP error: 401 Unauthorized` from the Codex responses connection.
- `Provided authentication token is expired. Please try signing in again.`

`data/discovery/ai-worker-state.json` still reports last success `2026-09-14T22:46:14.192953+00:00`, ten reviewed proposals, engine `codex-cli`. The heartbeat was not rewritten and no review was fabricated. Scheduler `no_agent=true` does not eliminate model calls: this wrapper explicitly launches Codex.

An authorized operator should consider pausing only this AI job while resolving the installed Codex runtime's authentication. That action is **not performed here**. After approved authentication recovery, verify a bounded no-delivery review and trusted apply, then inspect scheduler status/heartbeat. Do not switch to paid API credentials or use another account as a workaround without explicit authorization.

## Verification and local artifacts

Artifacts are private/local under `/tmp/arbs-broad-recovery-2026-09-17/` (not published, not durable across temporary-directory cleanup):

| Artifact | Evidence |
|---|---|
| `polymarket-response.json`, `kalshi-response.json` | Actual public GET responses, one page each |
| `polymarket-schema.json` | Official optional-cursor schema |
| `replay-comparison.json` | Same actual Polymarket response: HEAD → zero rows, `partial_error`; repaired code → 177 rows, `ok` |
| `capture.json`, `capture-summary.json` | Fresh isolated capture from a copied live checkpoint: one page per venue, no retries, 12-second per-request timeout, 60-second outer timeout |
| `scheduler-snapshot.json` | Scoped job state and errors; no delivery destinations or credentials |
| `catalog-tests.log` | 15 catalog tests passing, including four added regression tests |
| `full-tests.log` | Full offline suite: 139 tests passing |
| `hermes-cron-docs.html` | Authoritative Hermes scheduler documentation fetched read-only |

Fresh isolated capture results:

| Venue | Pages | Events | Normalized markets | Status | Terminal page |
|---|---:|---:|---:|---|---|
| Kalshi | 1 | 100 | 846 | ok, no errors | no |
| Polymarket | 1 | 36 | 177 | ok, no errors | yes, next position empty |

The run used `arbs.discovery_catalog.discover` with a copied checkpoint and an output path in `/tmp`. It did **not** run the publishing orchestrator, modify live discovery data, republish the plan, or trigger a scheduler job. Thus this is verified collector recovery, **not a claimed successful production scheduler run**. The existing capture wrapper loads this worktree, so its next normal run can exercise the fix; historical scheduler errors remain until a successful scheduled run occurs.

Commands exercised:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_discovery_catalog.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src/arbs/discovery_catalog.py tests/test_discovery_catalog.py
git diff --check
```

Regression coverage: omitted/null/empty cursors on empty and nonempty final pages; malformed payload/invalid cursor rejection; next-run restart without `after_cursor`; unchanged nonadvancing cursor error. Existing retry/checkpoint/atomic preservation tests also pass.

## Parent verification and production-wrapper exercise

After the isolated review above, the parent independently fetched the official
Gamma schema, inspected the actual source diff and the original AI diagnostic
lines, and ran the exact existing production wrapper:

```sh
bash /root/.hermes/scripts/arbs-broad-capture.sh
```

It returned **exit 0**, generating `2026-09-17T05:58:56.381273Z`:
Kalshi 9 pages / 829 events / 5,333 active markets seen / 1,000 sampled;
Polymarket 1 terminal page / 64 events / 333 sampled markets. Both had no errors.
This restored fresh bounded catalog evidence, not whole-market or executable-book
coverage. The 10,000-record cache yielded 150 REVIEW candidates, zero priced pairs.
The wrapper intentionally refreshed its existing allowlisted discovery publication.
No AI worker or messaging delivery was invoked.

The source schema, scoped scheduler snapshot, isolated reproduction summary and
compressed actual production catalog/report were preserved durably under
`data/fee-validation/2026-09-17/broad-recovery/`. `wrapper-success.json` binds both
uncompressed and archive hashes. This is manual wrapper success, **not a forced
scheduler run**; the original historical scheduler error must not be overwritten
or described as automatically cleared. AI authentication remains blocked.

The parent subsequently ran the complete canonical gate after integrating the
fee work: 243 tests and 21 subtests passed, plus plan/replay/compile/diff checks.

## Subsequent scheduled recovery

The next **ordinary scheduled capture** also succeeded: job `0c3993b2f1f2`
recorded `last_status: ok`, `last_error: null`, completion
`2026-09-17T09:12:29.703261+03:00` (06:12:29 UTC). Its catalog generation
`2026-09-17T06:12:06.250918Z` fetched ten pages/1,000 events per venue and sampled
1,000 markets per venue with no errors. Both retain `complete_catalog: false`.
The bounded cache yielded 150 proposals: 144 REVIEW, six REJECT, zero priced pairs.
The six attached reviews are previously stored source-matching annotations, **not
proof of a recovered AI worker**. AI's last scheduler status remains error.

Scoped runtime state and counts are retained in
`data/fee-validation/2026-09-17/broad-recovery/scheduled-recovery.json`.
No schedule was changed or new job created; this scheduled success occurred
naturally after the manual wrapper exercise described above.

## Scope and limitations

Files changed by this task:

- `src/arbs/discovery_catalog.py`
- `tests/test_discovery_catalog.py`
- `docs/broad-recovery-2026-09-17.md`

No fee files, rolling plan, AI worker, wrappers, scheduler state, runtime secrets, accounts, alerts or live scan configuration changed. Concurrent fee-related untracked work was observed and left alone. The existing untracked `docs/pinnacle-read-only-integration-plan.html` remained byte-identical; SHA-256 before/after: `2480dd16eb665aadaed0c38f8d60b61df679924c440a672f3abc5aa0c83dbad5`.

The requested `hermes-agent` skill was unavailable (`Skill not found`). `agent-runtime-operations` was loaded; current authoritative docs were fetched at <https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/>. In particular, script-only cron reports a nonzero script exit as failure; historical status is not automatically cleared by a code repair.

Rollback is limited to reverting the optional-cursor change and its four tests from this task's diff; do not reset the shared worktree or unrelated fee/plan changes. Retain this incident record for audit. No new reusable skill was written because this task's writable scope is discovery source/tests and this document only.
