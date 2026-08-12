import json
import tempfile
import unittest
from pathlib import Path

from arbs.ingestion.corpus import CorpusError, load_corpus
from arbs.matching.live import match_events, normalize_kalshi, normalize_polymarket

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests/fixtures/replay/mlb-public-2026-08-12"


class RawCorpusTests(unittest.TestCase):
    def test_raw_corpus_integrity_and_offline_replay(self):
        manifest, records = load_corpus(CORPUS)
        self.assertEqual(manifest["record_count"], 175)
        kalshi = [r["payload"] for r in records if r["venue"] == "kalshi"]
        poly = [r["payload"] for r in records if r["venue"] == "polymarket"]
        first = match_events(normalize_kalshi(kalshi), normalize_polymarket(poly))
        second = match_events(normalize_kalshi(kalshi), normalize_polymarket(poly))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 33)
        self.assertTrue(all(not item.pricing_eligible for item in first))

    def test_corpus_tampering_fails(self):
        manifest = (CORPUS / "manifest.json").read_text()
        records = (CORPUS / "records.jsonl").read_text()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(manifest)
            lines = records.splitlines()
            item = json.loads(lines[0]); item["payload"]["ticker"] = "TAMPERED"
            lines[0] = json.dumps(item, sort_keys=True)
            (root / "records.jsonl").write_text("\n".join(lines) + "\n")
            with self.assertRaises(CorpusError): load_corpus(root)

    def test_duplicate_identity_fails_even_with_valid_file_hash(self):
        manifest = json.loads((CORPUS / "manifest.json").read_text())
        records = (CORPUS / "records.jsonl").read_text()
        with tempfile.TemporaryDirectory() as temp:
            import hashlib
            root = Path(temp); doubled = records + records.splitlines()[0] + "\n"
            manifest["record_count"] += 1
            manifest["records_sha256"] = hashlib.sha256(doubled.encode()).hexdigest()
            (root / "manifest.json").write_text(json.dumps(manifest))
            (root / "records.jsonl").write_text(doubled)
            with self.assertRaises(CorpusError): load_corpus(root)


if __name__ == "__main__": unittest.main()
