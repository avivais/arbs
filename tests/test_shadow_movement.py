import json,unittest
from pathlib import Path
from arbs.shadow_movement import report

class MovementTests(unittest.TestCase):
 def test_real_shadow_samples_produce_transitions_without_eligibility(self):
  paths=sorted(Path('data/shadow/books').glob('*.json'))
  if len(paths)<2:self.skipTest('shadow evidence not yet accumulated')
  value=report(paths,include_transitions=False);self.assertGreater(value['transition_count'],0);self.assertGreater(value['top_quote_changed_transition_count'],0);self.assertEqual(value['transitions'],[]);self.assertNotIn('pricing_eligible',json.dumps(value))

if __name__=='__main__':unittest.main()
