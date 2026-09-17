"""Explicit public artifact allowlist; never publish runtime credentials or logs."""
from __future__ import annotations

import html
import fcntl
import json
import os
from pathlib import Path
import tempfile

PUBLIC_ROOT = Path('/srv/arbs-public')
REPORTS = (
    ('dashboard.html', 'Unified live dashboard', 'All categories in one view; observed quote gaps and unpriced review proposals remain distinct.'),
    ('discovery.html', 'Broad discovery', 'Rotating, bounded cross-venue candidate queue; not verified arbitrage.'),
    ('rolling-plan.html', 'Project status', 'Canonical delivery plan and evidence gates.'),
    ('fee-aware-validation.html', 'Fee-aware validation', 'Dated experimental replay and fee-source limitations; not a live net-profit feed.'),
    ('validation-verdict.html', 'Validation verdict', 'Dated validation decision; observe report timestamps.'),
    ('settlement-eligibility-review.html', 'Settlement review', 'Dated payout-equivalence and exception-rule assessment.'),
    ('matching-independent-review.html', 'Matching review', 'Dated identity review; not proof of live or full-catalog matching.'),
    ('operator-review.html', 'Operator evidence review', 'Historical review evidence, not a live opportunity scanner.'),

)
STATIC_PATHS = tuple('docs/' + name for name, _, _ in REPORTS) + (
    'docs/reports.html', 'docs/live-dashboard.html', 'docs/live-matches.html', 'docs/broad-discovery.md',
    'docs/fee-aware-validation.md', 'docs/validation-verdict.md',
    'docs/settlement-eligibility-review.md', 'docs/matching-independent-review.md',
    'docs/ROLLING_PLAN.md', 'docs/unified-dashboard.md',
    'docs/operations-runbook.md', 'docs/broad-recovery-2026-09-17.md',
    'data/reports/matching-independent-review.json',
    'data/reports/settlement-eligibility-review.json',
    'data/reports/resolution-audit.json',
    'data/reports/shadow-validation-checkpoint.json',
    'data/reports/review-evidence/MLBGAME.pdf',
)
DATA_PATHS = (
    'data/discovery/report-latest.json',
    'data/discovery/ai-worker-state.json',
    'data/shadow/latest-indicators.json',
    'data/shadow/validation/latest.json',
)
STYLE = 'body{max-width:1100px;margin:0 auto;padding:24px;font:16px/1.6 system-ui;background:#101725;color:#e7edf8}a{color:#8ec5ff}article{background:#1b2639;padding:18px;border-radius:12px;margin:14px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h1{line-height:1.2}nav{display:flex;gap:16px;flex-wrap:wrap}'


def page(title: str, body: str) -> str:
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Arbs · ' + html.escape(title) + '</title><style>' + STYLE + '</style></head><body><nav><a href="dashboard.html">Unified dashboard</a><a href="reports.html">All reports</a></nav><h1>' + html.escape(title) + '</h1>' + body + '</body></html>'


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def render_directory(root: Path) -> None:
    """Generate report directory and escaped view of the canonical fee report."""
    fee = root / 'docs/fee-aware-validation.md'
    if fee.is_file():
        body = '<p>Dated research report, not live net-profit pricing. <a href="fee-aware-validation.md">Canonical Markdown</a></p><pre>' + html.escape(fee.read_text()) + '</pre>'
        atomic_write(root / 'docs/fee-aware-validation.html', page('Fee-aware validation', body).encode())
    cards = []
    for name, title, description in REPORTS:
        if (root / 'docs' / name).is_file():
            cards.append('<article><h2><a href="' + name + '">' + html.escape(title) + '</a></h2><p>' + html.escape(description) + '</p></article>')
    body = '<p>Live feeds and dated research are labeled separately. No page authorizes trading. Telegram opportunity and health alerts are off; collection continues.</p>' + ''.join(cards)
    body += '<h2>Methods and machine-readable data</h2><ul>'
    for target, title in (
        ('broad-discovery.md', 'How broad candidate discovery works'),
        ('unified-dashboard.md', 'Unified dashboard scope and data semantics'),
        ('../data/discovery/report-latest.json', 'Current broad discovery evidence JSON'),
        ('../data/shadow/latest-indicators.json', 'Current captured quote observations JSON'),
        ('../data/discovery/ai-worker-state.json', 'AI worker last successful run JSON'),
        ('../data/shadow/validation/latest.json', 'Daily validation generation manifest JSON'),
    ):
        body += '<li><a href="' + target + '">' + title + '</a></li>'
    body += '</ul>'
    atomic_write(root / 'docs/reports.html', page('Dashboards and reports', body).encode())


def _publish_unlocked(root: Path, public: Path, *, include_docs: bool) -> list[str]:
    """Copy allowlisted completed snapshots atomically; never refresh source timestamps.

    Missing inputs retain the previous public artifact with its ORIGINAL age.
    Clients must enforce age/eligibility gates. Only explicitly approved public
    source artifacts are copied; account state, logs and raw archives are excluded.
    """
    if not public.is_dir():
        return []
    paths = DATA_PATHS + (STATIC_PATHS if include_docs else ())
    copied = []
    for relative in paths:
        source = root / relative
        if not source.is_file():
            continue
        data = source.read_bytes()
        if relative.endswith('.json'):
            json.loads(data)  # refuse malformed publication; preserve previous file
        atomic_write(public / relative, data)
        copied.append(relative)
    return copied


def publish_public(root: Path, public: Path = PUBLIC_ROOT, *, include_docs: bool = True) -> list[str]:
    """Serialize snapshot reads and atomic copies across independent producers.

    Reading only after acquiring this lock prevents a delayed publisher from
    overwriting a newer public snapshot with bytes read before another publisher.
    The lock lives in private runtime data, outside the public artifact root.
    """
    if not public.is_dir():
        return []
    lock_path = root / 'data/publication.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _publish_unlocked(root, public, include_docs=include_docs)
