import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arbs.shadow_books import sample_pair,summarize


class ShadowBookTests(unittest.TestCase):
 def test_atomic_success_and_empirical_summary_stays_gated(self):
  sample={"schema_version":1,"pair_id":"x","receipt_skew_ms":12,"kalshi":{"request_elapsed_ms":20},"polymarket":{"request_elapsed_ms":40}}
  with tempfile.TemporaryDirectory() as d,patch('arbs.shadow_books.capture_pair',return_value=sample):
   p=Path(d)/'a.json';result=sample_pair('k','p',p);self.assertEqual(result['status'],'complete')
   summary=summarize([p]);self.assertEqual(summary['receipt_skew_ms']['p50'],12);self.assertEqual(summary['threshold_status'],'INSUFFICIENT_ELAPSED_EVIDENCE')

 def test_failure_record_has_no_error_message_or_secret(self):
  with tempfile.TemporaryDirectory() as d,patch('arbs.shadow_books.capture_pair',side_effect=RuntimeError('secret')):
   p=Path(d)/'bad.json';result=sample_pair('k','p',p);self.assertEqual(result['status'],'failed');self.assertNotIn('secret',json.dumps(result))


if __name__=='__main__':unittest.main()
