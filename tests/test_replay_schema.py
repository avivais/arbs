import json
import tempfile
import unittest
from pathlib import Path

from arbs.ingestion.schema import SnapshotValidationError, validate_snapshot
from arbs.ingestion.snapshots import Capture, write_capture
from arbs.replay import ReplayError, load_match_report


ROOT = Path(__file__).resolve().parents[1]


class ReplayAndSchemaTests(unittest.TestCase):
    def test_pinned_report_replays_offline_with_integrity(self):
        report = load_match_report(ROOT / "data/reports/live-mlb-matches.json")
        self.assertEqual(len(report["matches"]), 33)
        self.assertTrue(all(not match["pricing_eligible"] for match in report["matches"]))

    def test_tampered_replay_fails(self):
        source = json.loads((ROOT / "data/reports/live-mlb-matches.json").read_text())
        source["counts"]["matched_events"] = 999
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaises(ReplayError): load_match_report(path)

    def test_partial_manifest_and_schema(self):
        capture = Capture()
        capture.fail("kalshi", RuntimeError("bounded failure"))
        with tempfile.TemporaryDirectory() as temp:
            path = write_capture(capture, Path(temp))
            result = validate_snapshot(path)
            self.assertEqual(result["status"], "failed")

    def test_unknown_schema_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "future.jsonl"
            path.write_text(json.dumps({"type": "manifest", "schema_version": 2, "record_count": 0}) + "\n")
            with self.assertRaises(SnapshotValidationError): validate_snapshot(path)


if __name__ == "__main__": unittest.main()
