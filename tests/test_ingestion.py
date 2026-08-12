import json
import tempfile
import unittest
from pathlib import Path

from arbs.adapters.http import JsonResponse
from arbs.ingestion.snapshots import Capture, IngestionError, capture_kalshi, capture_polymarket, write_capture


def response(data, url="https://example.test"):
    return JsonResponse(data=data, url=url, status=200, elapsed_ms=1.25, received_at_unix_ms=1)


class FakeKalshi:
    def list_series(self, **kwargs):
        cursor = kwargs.get("cursor")
        return response({"series": [{"ticker": "S1"}] if cursor is None else [{"ticker": "S2"}], "cursor": "next" if cursor is None else ""})

    def list_series_markets(self, ticker, **kwargs):
        return response({"markets": [{"ticker": ticker + "-M"}], "cursor": ""})


class FakePoly:
    def list_sports(self):
        return response([{"sport": "nba", "primaryTagId": 1}, {"sport": "nfl", "primaryTagId": 2}])

    def list_sports_events(self, tag_id, **kwargs):
        return response({"events": [{"id": f"E{tag_id}", "markets": [{"id": f"M{tag_id}"}]}], "next_cursor": ""})


class IngestionTests(unittest.TestCase):
    def test_union_capture(self):
        capture = Capture()
        capture_kalshi(FakeKalshi(), capture)
        capture_polymarket(FakePoly(), capture)
        ids = [
            record["payload"].get("ticker")
            or record["payload"].get("id")
            or record["payload"].get("sport")
            for record in capture.records
        ]
        self.assertEqual(ids, ["S1", "S1-M", "S2", "S2-M", "nba", "E1", "M1", "nfl", "E2", "M2"])
        self.assertEqual(capture.request_count, 7)

    def test_bounded_capture(self):
        capture = Capture()
        capture_kalshi(FakeKalshi(), capture, max_series=1)
        self.assertEqual([r["payload"]["ticker"] for r in capture.records], ["S1", "S1-M"])

    def test_atomic_jsonl_write(self):
        capture = Capture(records=[{"venue": "x", "kind": "market", "payload": {"id": 1}}])
        with tempfile.TemporaryDirectory() as directory:
            target = write_capture(capture, Path(directory))
            lines = [json.loads(line) for line in target.read_text().splitlines()]
            self.assertEqual(lines[0]["type"], "manifest")
            self.assertEqual(lines[1]["payload"]["id"], 1)

    def test_repeated_cursor_fails(self):
        class LoopingKalshi:
            def list_series(self, **kwargs):
                return response({"series": [], "cursor": "same"})
        with self.assertRaises(IngestionError):
            capture_kalshi(LoopingKalshi(), Capture())


if __name__ == "__main__":
    unittest.main()
