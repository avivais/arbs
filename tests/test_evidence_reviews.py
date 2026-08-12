import tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from arbs.decision_evidence import build,canonical_hash,write
from arbs.equivalence_cases import run_cases
from arbs.reviews import ReviewEvent,effective_pricing_eligible,validate

ROOT=Path(__file__).resolve().parents[1]

class EvidenceReviewTests(unittest.TestCase):
 def test_every_decision_is_versioned_hashed_and_pricing_disabled(self):
  report=build(ROOT/'tests/fixtures/replay/mlb-public-2026-08-12')
  self.assertEqual(report['counts'],{'records':175,'parse_decisions':137,'matches':38,'unpaired':61})
  self.assertEqual(len(report['decisions']),175)
  for d in report['decisions']:
   self.assertEqual(len(d['decision_id']),64);self.assertFalse(d['pricing_eligible']);self.assertTrue(d['source_payload_sha256'])
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'report.json';write(report,p);self.assertIn('report_sha256',p.read_text())
 def test_structured_cases_execute(self):
  cases=run_cases();self.assertTrue(cases);self.assertTrue(all(x['actual']==x['expected'] for x in cases))
 def test_review_expiry_and_override_never_enable_review(self):
  now=datetime.now(timezone.utc);event=ReviewEvent('c',1,'APPROVED_OVERRIDE','r',now,now+timedelta(days=1),'d','a'*64,('rules',),{'complete':True},('b'*64,),'reviewed')
  validate(event);self.assertFalse(effective_pricing_eligible('REVIEW',False,True,(event,)))
  with self.assertRaises(ValueError):validate(ReviewEvent('c',1,'APPROVED_OVERRIDE','r',now,now+timedelta(days=8),'d','a'*64,(),{},(),''))

if __name__=='__main__':unittest.main()
