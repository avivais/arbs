import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('broad_health', Path(__file__).resolve().parents[1]/'scripts/broad_discovery_health.py')
assert spec is not None and spec.loader is not None
health=importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        self.catalog={'generated_at':self.now.isoformat(),'coverage':{v:{'markets_returned':2,'errors':[]} for v in ('kalshi','polymarket')}}
        self.worker={'last_success':self.now.isoformat()}

    def test_healthy_no_alert(self):
        self.assertEqual(health.problems(self.catalog,self.worker,self.now),[])

    def test_missing_data_visible(self):
        self.assertEqual(len(health.problems({}, {}, self.now)),4)

    def test_catalog_stale(self):
        self.catalog['generated_at']=(self.now-timedelta(hours=2)).isoformat()
        self.assertIn('catalog stale or future-dated',health.problems(self.catalog,self.worker,self.now))

    def test_worker_stale(self):
        self.worker['last_success']=(self.now-timedelta(hours=7)).isoformat()
        self.assertIn('AI review worker stale or future-dated',health.problems(self.catalog,self.worker,self.now))

    def test_partial_capture_not_healthy(self):
        self.catalog['coverage']['polymarket']['errors']=[{'type':'HTTPError'}]
        self.assertEqual(health.problems(self.catalog,self.worker,self.now),['polymarket catalog errors or no markets in last slice'])

    def test_future_and_naive_timestamps_fail(self):
        self.catalog['generated_at']=(self.now+timedelta(hours=1)).isoformat()
        self.worker['last_success']='2026-09-07T00:00:00'
        self.assertEqual(len(health.problems(self.catalog,self.worker,self.now)),2)
