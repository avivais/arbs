import json
from pathlib import Path

import pytest

from arbs.publication import publish_public, render_directory


def test_publication_allowlist_and_original_timestamp(tmp_path):
    root, public = tmp_path / 'repo', tmp_path / 'public'
    public.mkdir()
    data = root / 'data/shadow/latest-indicators.json'
    data.parent.mkdir(parents=True)
    value = {'generated_at': '2026-01-01T00:00:00Z', 'records': []}
    data.write_text(json.dumps(value))
    (root / 'auth.json').write_text('private')
    (root / 'data/shadow/private.log').write_text('private')
    assert publish_public(root, public) == ['data/shadow/latest-indicators.json']
    assert json.loads((public / 'data/shadow/latest-indicators.json').read_text()) == value
    assert not (public / 'auth.json').exists()
    assert not (public / 'data/shadow/private.log').exists()
    assert (public / 'data/shadow/latest-indicators.json').stat().st_mode & 0o777 == 0o644


def test_malformed_input_preserves_previous_artifact(tmp_path):
    root, public = tmp_path / 'repo', tmp_path / 'public'
    source = root / 'data/shadow/latest-indicators.json'
    dest = public / 'data/shadow/latest-indicators.json'
    source.parent.mkdir(parents=True)
    dest.parent.mkdir(parents=True)
    source.write_text('{broken')
    dest.write_text('{"generated_at":"old"}')
    with pytest.raises(json.JSONDecodeError):
        publish_public(root, public)
    assert dest.read_text() == '{"generated_at":"old"}'


def test_skip_docs_and_missing_root(tmp_path):
    root, public = tmp_path / 'repo', tmp_path / 'public'
    (root / 'docs').mkdir(parents=True)
    (root / 'docs/dashboard.html').write_text('dashboard')
    assert publish_public(root, public) == []
    public.mkdir()
    assert publish_public(root, public, include_docs=False) == []
    assert publish_public(root, public) == ['docs/dashboard.html']


def test_report_directory_and_fee_html_escape(tmp_path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/fee-aware-validation.md').write_text('# Test <script>alert(1)</script>')
    (tmp_path / 'docs/dashboard.html').write_text('dashboard')
    render_directory(tmp_path)
    fee = (tmp_path / 'docs/fee-aware-validation.html').read_text()
    assert '<script>' not in fee
    assert '&lt;script&gt;' in fee
    directory = (tmp_path / 'docs/reports.html').read_text()
    assert 'dashboard.html' in directory
    assert 'fee-aware-validation.html' in directory
    assert 'href="discovery.html"' not in directory
