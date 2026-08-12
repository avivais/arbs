import json
import tempfile
import unittest
from pathlib import Path

from arbs.normalization import classify_family, coverage, load_and_normalize


class NormalizationTests(unittest.TestCase):
    def test_family_classification(self):
        self.assertEqual(classify_family("Will both teams score over 2.5 goals?"), "TOTAL")
        self.assertEqual(classify_family("Team A vs. Team B"), "HEAD_TO_HEAD")

    def test_normalizes_both_venues_and_reports_overlap(self):
        rows = [
            {"type": "manifest"},
            {"type":"record","venue":"kalshi","kind":"series","parent_id":None,"sha256":"s","payload":{"ticker":"KS","title":"NBA game","tags":["Basketball"],"settlement_sources":[{"name":"NBA"}]}},
            {"type":"record","venue":"kalshi","kind":"market","parent_id":"KS","sha256":"k","payload":{"ticker":"KM","event_ticker":"KE","title":"A vs B","status":"active","close_time":"2026-01-01","rules_primary":"winner"}},
            {"type":"record","venue":"polymarket","kind":"sport","parent_id":None,"sha256":"s","payload":{"sport":"basketball","name":"NBA","resolution":"nba.com"}},
            {"type":"record","venue":"polymarket","kind":"event","parent_id":"basketball","sha256":"e","payload":{"id":"PE","title":"A vs B","startDate":"2026-01-01"}},
            {"type":"record","venue":"polymarket","kind":"market","parent_id":"PE","sha256":"p","payload":{"id":"PM","question":"A vs B","active":True,"closed":False,"endDate":"2026-01-01","description":"winner","outcomes":"[\"A\",\"B\"]"}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"x.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in rows))
            markets=load_and_normalize(path)
        self.assertEqual(len(markets),2)
        self.assertEqual(coverage(markets)["sport_overlap"],["basketball"])


if __name__ == "__main__": unittest.main()
