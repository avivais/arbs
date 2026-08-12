import unittest
from datetime import datetime,timezone
from arbs.event_identity import EventIdentity,compare


def event(venue='k',roles=(),game=None,neutral=None,start='2026-08-12T17:40:00+00:00',ids=(),reschedule='NONE'):
 return EventIdentity(venue,venue,'baseball','mlb',('ATH','CWS'),roles,datetime.fromisoformat(start),'regular',game,neutral,ids,reschedule)


class EventIdentityTests(unittest.TestCase):
 def test_unknown_cross_venue_dimensions_are_review(self):
  result=compare(event(),event('p',roles=(('ATH','away'),('CWS','home')),game=1,neutral=False,ids=(('optic','1'),)))
  self.assertEqual(result.decision,'REVIEW');self.assertIn('PARTICIPANT_ROLE_UNKNOWN',result.reasons)
 def test_explicit_game_role_and_authoritative_conflicts_fail(self):
  self.assertEqual(compare(event(game=1),event('p',game=2)).decision,'NO_MATCH')
  self.assertEqual(compare(event(roles=(('ATH','away'),)),event('p',roles=(('ATH','home'),))).decision,'NO_MATCH')
  self.assertEqual(compare(event(ids=(('shared','1'),)),event('p',ids=(('shared','2'),))).decision,'NO_MATCH')
 def test_start_window_and_reschedule(self):
  self.assertEqual(compare(event(),event('p',start='2026-08-12T18:00:01+00:00')).decision,'NO_MATCH')
  self.assertIn('RESCHEDULE_EVIDENCE_PRESENT',compare(event(),event('p',reschedule='SUSPECTED')).reasons)


if __name__=='__main__':unittest.main()
