import json
import tempfile
import unittest
from pathlib import Path

from arbs.shadow_validation import operational_evidence


class OperationalEvidenceTests(unittest.TestCase):
    def test_reports_artifact_coverage_and_fail_closed_modeled_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, second in enumerate((0, 300, 900)):
                value = {
                    "generated_at": f"2026-08-12T00:{second // 60:02d}:00Z",
                    "matches": [
                        {
                            "decision": "REVIEW",
                            "pricing_eligible": False,
                            "kalshi": {"event_id": "k1"},
                            "polymarket": {"event_id": "p1"},
                        }
                    ],
                }
                (root / f"{index}.json").write_text(json.dumps(value))
            (root / "bad.json").write_text("not json")
            report = operational_evidence(sorted(root.glob("*.json")))
        cadence = report["artifact_cadence"]
        self.assertEqual(cadence["valid_unique_reports"], 3)
        self.assertEqual(cadence["invalid_report_count"], 1)
        self.assertEqual(cadence["expected_slots_between_first_and_last"], 4)
        self.assertEqual(cadence["occupied_schedule_slots"], 3)
        self.assertEqual(cadence["observed_slot_coverage"], 0.75)
        self.assertEqual(cadence["largest_observed_gap_seconds"], 600)
        self.assertIn("NOT_HOST", cadence["claim_scope"])
        audit = report["decision_audit"]
        self.assertEqual(audit["decision_counts"], {"REVIEW": 1})
        self.assertEqual(audit["pricing_eligible_pairs"], 0)
        self.assertEqual(audit["theoretical_fill_count"], 0)
        self.assertEqual(
            audit["modeled_net_result_status"],
            "NOT_COMPUTABLE_NO_PRICING_ELIGIBLE_PAIRS",
        )

    def test_nonpositive_schedule_rejected(self):
        with self.assertRaises(ValueError):
            operational_evidence([], 0)


if __name__ == "__main__":
    unittest.main()
