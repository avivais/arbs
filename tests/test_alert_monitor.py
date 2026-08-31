import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "arbs_opportunity_alert.py"


class AlertMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.indicators = self.root / "indicators.json"
        self.state = self.root / "active.json"
        self.health = self.root / "health.json"
        self.environment = {
            **os.environ,
            "ARBS_ALERT_INDICATORS": str(self.indicators),
            "ARBS_ALERT_STATE": str(self.state),
            "ARBS_ALERT_HEALTH_STATE": str(self.health),
            "ARBS_ALERT_HEALTH_FAILURE_SCANS": "3",
        }

    def tearDown(self):
        self.temporary.cleanup()

    def payload(self, *, status="OBSERVED_RESERVED_GAP", second_price="0.57", generated_at=None):
        return {
            "generated_at": generated_at
            or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "records": [
                {
                    "event_id": "TEST-EVENT",
                    "participants": ["AAA", "BBB"],
                    "status": status,
                    "kalshi_url": "https://kalshi.com/test",
                    "polymarket_url": "https://polymarket.com/test",
                    "legs": [
                        {
                            "venue": "kalshi",
                            "outcome": "AAA",
                            "instrument_id": "K1",
                            "best_ask": "0.40",
                            "ask_levels": [{"price": "0.40", "quantity": "2"}],
                        },
                        {
                            "venue": "polymarket",
                            "outcome": "BBB",
                            "instrument_id": "P1",
                            "best_ask": second_price,
                            "ask_levels": [{"price": second_price, "quantity": "4"}],
                        },
                    ],
                }
            ],
        }

    def run_payload(self, payload):
        self.indicators.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            ["python3", str(SCRIPT)],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_opportunity_dedup_and_unavailable_scan_preserves_active_state(self):
        first = self.run_payload(self.payload())
        self.assertEqual(first.returncode, 0)
        self.assertIn("Arbitrage observation ≥3%", first.stdout)

        base = datetime.now(timezone.utc) - timedelta(seconds=10)
        unavailable = self.payload(
            status="UNAVAILABLE_FRESHNESS",
            generated_at=(base + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        )
        second = self.run_payload(unavailable)
        self.assertEqual(second.returncode, 0)
        self.assertNotIn("Arbitrage observation", second.stdout)
        self.assertTrue(json.loads(self.state.read_text(encoding="utf-8"))["active"])

        recovered = self.payload(
            generated_at=(base + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        )
        third = self.run_payload(recovered)
        self.assertEqual(third.returncode, 0)
        self.assertNotIn("Arbitrage observation", third.stdout)

    def test_sustained_coverage_loss_alerts_once_then_reports_recovery(self):
        base = datetime.now(timezone.utc) - timedelta(seconds=30)
        for index in range(2):
            result = self.run_payload(
                self.payload(
                    status="UNAVAILABLE_FRESHNESS",
                    generated_at=(base + timedelta(seconds=index)).isoformat().replace("+00:00", "Z"),
                )
            )
            self.assertEqual(result.stdout, "")

        degraded = self.run_payload(
            self.payload(
                status="UNAVAILABLE_FRESHNESS",
                generated_at=(base + timedelta(seconds=3)).isoformat().replace("+00:00", "Z"),
            )
        )
        self.assertIn("monitoring coverage degraded", degraded.stdout)

        repeated = self.run_payload(
            self.payload(
                status="UNAVAILABLE_FRESHNESS",
                generated_at=(base + timedelta(seconds=4)).isoformat().replace("+00:00", "Z"),
            )
        )
        self.assertEqual(repeated.stdout, "")

        recovered = self.run_payload(
            self.payload(
                second_price="0.58",
                generated_at=(base + timedelta(seconds=5)).isoformat().replace("+00:00", "Z"),
            )
        )
        self.assertIn("monitoring coverage recovered", recovered.stdout)
        self.assertNotIn("Arbitrage observation", recovered.stdout)


if __name__ == "__main__":
    unittest.main()
