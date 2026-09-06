import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('scan_health', Path(__file__).resolve().parents[1] / 'scripts/record_scan_health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class ScanHealthTests(unittest.TestCase):
    def test_start_is_not_success_and_finish_preserves_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = health.record(root, '20260906T010000Z', 'started')
            self.assertEqual(first['status'], 'STARTED_WITHOUT_COMPLETION')
            last = health.record(root, '20260906T010000Z', 'finished', 0)
            self.assertEqual(last['status'], 'SUCCESS')
            self.assertEqual(first['started'], last['started'])
            self.assertEqual(json.loads(next(root.glob('*.json')).read_text()), last)
            self.assertEqual(list(root.glob('*.tmp*')), [])

    def test_failure_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            result = health.record(Path(directory), '20260906T010000Z', 'finished', 7)
            self.assertEqual(result['status'], 'FAILED')
            self.assertEqual(result['exit_code'], 7)
            self.assertIn('NOT_CONTINUOUS_UPTIME', result['claim_scope'])

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            health.record(Path('/tmp'), '../escape', 'started')
