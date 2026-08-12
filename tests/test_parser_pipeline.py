import unittest
from pathlib import Path

from arbs.ingestion.corpus import load_corpus
from arbs.parsers import parse_kalshi, parse_polymarket, replay_decisions

ROOT=Path(__file__).resolve().parents[1]


class ParserPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.records=load_corpus(ROOT/'tests/fixtures/replay/mlb-public-2026-08-12')

    def test_reason_coded_corpus_pipeline_retains_every_input(self):
        k=[r for r in self.records if r['venue']=='kalshi']; p=[r for r in self.records if r['venue']=='polymarket']
        kd=parse_kalshi(k); pd=parse_polymarket(p)
        self.assertEqual(sum(len(x.source_ids) for x in kd),len(k))
        self.assertEqual(len(pd),len(p))
        for decision in kd+pd:
            self.assertTrue(decision.source_hashes and decision.source_urls and decision.received_at)
            self.assertTrue(decision.event is not None or decision.reason_codes)

    def test_replay_emits_matches_unpaired_and_parse_decisions(self):
        result=replay_decisions(self.records)
        self.assertEqual(len(result['matches']),33)
        self.assertTrue(result['unpaired'])
        self.assertTrue(all(not x['pricing_eligible'] for x in result['matches']))
        self.assertEqual(result,replay_decisions(self.records))

    def test_missing_fields_emit_reason_codes(self):
        base=self.records[0].copy(); base['payload']=dict(base['payload']); base['payload'].pop('event_ticker',None)
        result=parse_kalshi([base])[0]
        self.assertEqual(result.decision,'UNSUPPORTED'); self.assertIn('MISSING_EVENT_ID',result.reason_codes)


if __name__=='__main__':unittest.main()
