import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from arbs.alerts import AlertGate, Signal
from arbs.audit import connect, insert_decision, insert_run
from arbs.metrics import ScanMetrics


class OperationsTests(unittest.TestCase):
    def test_audit_lineage_and_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / "audit.db")
            insert_run(db, {"id":"r1", "started_at":"2026-08-12T00:00:00Z", "status":"complete",
                            "parser_version":"1", "policy_version":"1", "counts":{}})
            insert_decision(db, {"id":"d1", "run_id":"r1", "created_at":"2026-08-12T00:00:01Z",
                                 "decision":"REVIEW", "pricing_eligible":False, "participants":["A","B"],
                                 "start_utc":"2026-08-12T01:00:00Z", "evidence":{"code":"RULE_UNKNOWN"}})
            self.assertEqual(db.execute("select count(*) from decisions").fetchone()[0], 1)
            with self.assertRaises(Exception):
                insert_decision(db, {"id":"d2", "run_id":"missing", "created_at":"x", "decision":"REVIEW",
                                     "pricing_eligible":False, "participants":["A","B"], "start_utc":"y", "evidence":{}})

    def test_alert_expiry_and_dedup(self):
        now = datetime.now(timezone.utc)
        gate = AlertGate(timedelta(minutes=5))
        signal = Signal("d", "hash", "1.0", now + timedelta(minutes=1), "audit://d")
        self.assertEqual(gate.qualify(signal, now), (True, "SEND"))
        self.assertEqual(gate.qualify(signal, now), (False, "DEDUPLICATED"))
        self.assertEqual(gate.qualify(signal, now + timedelta(minutes=2)), (False, "EXPIRED"))

    def test_metrics_rates(self):
        metrics = ScanMetrics(2, 0, 50, 100, 80, 20, 10, 30, 0, "p1", "v1").as_dict()
        self.assertEqual(metrics["parser_coverage"], .8)
        self.assertEqual(metrics["exact_rate"], .75)


if __name__ == "__main__": unittest.main()
