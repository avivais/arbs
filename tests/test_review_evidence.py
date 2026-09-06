"""Dated audit evidence checks; no live market/network access."""
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReviewEvidenceTests(unittest.TestCase):
    def test_preserved_source_hashes(self):
        for name in ('matching-independent-review', 'settlement-eligibility-review'):
            r = json.loads((ROOT / f'data/reports/{name}.json').read_text())
            b = (ROOT / 'data/reports' / r['source_archive']).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(), r['source_archive_sha256'])
            self.assertTrue(json.loads(gzip.decompress(b)))
        self.assertEqual(hashlib.sha256((ROOT / 'data/reports' / r['binding_terms_file']).read_bytes()).hexdigest(), r['binding_terms_sha256'])

    def test_reports_do_not_promote_eligibility(self):
        m = json.loads((ROOT / 'data/reports/matching-independent-review.json').read_text())
        s = json.loads((ROOT / 'data/reports/settlement-eligibility-review.json').read_text())
        self.assertEqual(m['human_independent_precision_gate'], 'NOT_SATISFIED')
        self.assertFalse(s['eligible_subset'])
        for row in m['records'] + s['records']:
            self.assertFalse(row['pricing_eligible'])

    def test_offline_replay_uses_only_preserved_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'scripts').mkdir()
            (root / 'docs').mkdir()
            shutil.copytree(ROOT / 'data/reports/review-evidence', root / 'data/reports/review-evidence')
            shutil.copyfile(ROOT / 'scripts/replay_validation_reviews.py', root / 'scripts/replay_validation_reviews.py')
            subprocess.run([sys.executable, str(root / 'scripts/replay_validation_reviews.py')], check=True, capture_output=True, timeout=20)
            for name in ('matching-independent-review', 'settlement-eligibility-review'):
                actual = json.loads((root / f'data/reports/{name}.json').read_text())
                expected = json.loads((ROOT / f'data/reports/{name}.json').read_text())
                actual.pop('generated_at'); expected.pop('generated_at')
                self.assertEqual(actual, expected)
