"""Deterministic offline tests; real capture is a separate CLI operation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from arbs.discovery_catalog import (
    atomic_json, category_for, collect_venue, discover, fetch_json, normalize_market,
)


def kalshi_event(identifier="KXTEST-1", category="Economics"):
    return {"category": category, "series_ticker": "KXTEST", "event_ticker": "KXTEST",
            "markets": [{"ticker": identifier, "title": "Test question?", "status": "active",
                         "market_type": "binary", "rules_primary": "Official primary rule",
                         "rules_secondary": "Secondary exceptions"}]}


def poly_event(identifier="1", category="Crypto"):
    return {"slug": "test-event", "tags": [{"label": category}], "markets": [
        {"id": identifier, "question": "Test?", "active": True, "closed": False,
         "description": "Resolves using official source.", "outcomes": '["Yes", "No"]'}]}


class CatalogTests(unittest.TestCase):
    def test_normalized_schema_and_rules(self):
        for venue, event in [("kalshi", kalshi_event()), ("polymarket", poly_event())]:
            row = normalize_market(venue, event["markets"][0], event, "https://source", "now")
            self.assertTrue(set("venue id title category description rules url close_time outcomes raw".split()) <= row.keys())
            self.assertEqual(row["outcomes"], ["Yes", "No"])
            self.assertEqual(row["raw"], event["markets"][0])
            self.assertTrue(row["rules_available"])
            self.assertEqual(row["source_url"], "https://source")
        self.assertIn("Secondary exceptions", normalize_market("kalshi", kalshi_event()["markets"][0], kalshi_event(), "u", "t")["rules"])

    def test_source_categories(self):
        for label, expected in [("Economics", "economics"), ("Elections", "politics"),
                                ("Crypto", "crypto"), ("Sports", "sports"), ("Weather", "other")]:
            self.assertEqual(category_for({"category": label}), expected)
            self.assertEqual(category_for({"tags": [{"label": label}]}), expected)

    def test_balanced_limit_and_counts(self):
        events = [kalshi_event(str(i)) for i in range(10)]
        events += [kalshi_event("s", "Sports"), kalshi_event("p", "Politics")]
        rows, coverage = collect_venue("kalshi", limit=3, max_pages=1,
            fetch=lambda _: {"events": events, "cursor": "next"})
        self.assertEqual(len(rows), 3)
        self.assertEqual(set(r["category"] for r in rows), {"economics", "sports", "politics"})
        self.assertEqual(coverage["sampled_out"], 9)
        self.assertEqual(coverage["next_position"], "next")
        self.assertFalse(coverage["complete_catalog"])
        self.assertIsNone(coverage["total_venue_markets"])

    def test_failed_page_keeps_last_good_cursor(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if len(calls) == 2:
                raise TimeoutError("offline")
            return {"events": [kalshi_event()], "cursor": "page2"}
        rows, coverage = collect_venue("kalshi", max_pages=3, fetch=fetch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(coverage["next_position"], "page2")
        self.assertEqual(coverage["status"], "partial_error")
        self.assertEqual(coverage["pages_fetched"], 1)

    def test_poly_keyset_rotation_end_and_closed_filter(self):
        event = poly_event()
        event["markets"].append(dict(event["markets"][0], id="closed", closed=True))
        calls = []
        def fetch(url):
            calls.append(parse_qs(urlparse(url).query))
            return {"events": [event], "next_cursor": "next"} if len(calls) == 1 else {"events": [], "next_cursor": ""}
        rows, coverage = collect_venue("polymarket", page_size=1, max_pages=3, position="old", fetch=fetch)
        self.assertEqual([c["after_cursor"] for c in calls], [["old"], ["next"]])
        self.assertEqual(len(rows), 1)
        self.assertEqual(coverage["inactive_markets_skipped"], 1)
        self.assertEqual(coverage["next_position"], "")
        self.assertTrue(coverage["end_of_catalog_reached"])

    def test_malformed_and_duplicate_rows(self):
        event = poly_event()
        event["markets"] += [event["markets"][0], dict(event["markets"][0], id="bad", outcomes="broken"), None]
        rows, coverage = collect_venue("polymarket", max_pages=1, fetch=lambda _: {"events": [event], "next_cursor": ""})
        self.assertEqual(len(rows), 1)
        self.assertEqual(coverage["duplicates"], 1)
        self.assertEqual(coverage["invalid_markets"], 2)

    def test_malformed_page_does_not_advance(self):
        _, coverage = collect_venue("kalshi", position="old", fetch=lambda _: {"events": []})
        self.assertEqual(coverage["next_position"], "old")
        self.assertEqual(coverage["pages_fetched"], 0)
        self.assertTrue(coverage["errors"])

    def test_nonadvancing_cursor(self):
        _, coverage = collect_venue("kalshi", position="same", fetch=lambda _: {"events": [], "cursor": "same"})
        self.assertEqual(coverage["pages_fetched"], 1)
        self.assertEqual(coverage["errors"][0]["type"], "PaginationError")

    def test_persisted_checkpoint_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.json"
            def fetch(url):
                return {"events": [kalshi_event()], "cursor": "next"} if "kalshi" in url else {"events": [poly_event()], "next_cursor": "poly-next"}
            first = discover(path, max_pages=1, page_size=1, fetch=fetch)
            urls = []
            def again(url):
                urls.append(url)
                return {"events": [], "cursor": ""} if "kalshi" in url else {"events": [], "next_cursor": ""}
            discover(path, max_pages=1, page_size=1, fetch=again)
            self.assertIn("cursor=next", urls[0])
            self.assertIn("after_cursor=poly-next", urls[1])
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                atomic_json(path, {"bad": float("nan")})
            self.assertEqual(before, path.read_bytes())
            with self.assertRaises(RuntimeError):
                discover(path, fetch=lambda _: (_ for _ in ()).throw(TimeoutError("offline")))
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(len(first["markets"]), 2)
            self.assertEqual(json.loads(before)["schema_version"], 1)

    def test_retry_budget_and_nonretryable_status(self):
        with patch("arbs.discovery_catalog.urlopen", side_effect=TimeoutError("timeout")) as opener, patch("arbs.discovery_catalog.time.sleep"):
            with self.assertRaises(TimeoutError):
                fetch_json("https://example.test", retries=2)
            self.assertEqual(opener.call_count, 3)
        with patch("arbs.discovery_catalog.urlopen", side_effect=HTTPError("u", 400, "bad", {}, None)) as opener:
            with self.assertRaises(HTTPError):
                fetch_json("https://example.test", retries=2)
            self.assertEqual(opener.call_count, 1)

    def test_bounds(self):
        with self.assertRaises(ValueError):
            discover("unused", max_pages=0)


if __name__ == "__main__":
    unittest.main()
