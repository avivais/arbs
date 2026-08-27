import unittest
from arbs.resolution_audit import audit_match, unique_historical_matches

MATCH={'participants':['A','B'],'kalshi':{'event_id':'ke','contracts':[{'id':'ka','selected_team':'A'},{'id':'kb','selected_team':'B'}]},'polymarket':{'event_id':'pe','contracts':[{'selected_team':'A','token_id':'pa'},{'selected_team':'B','token_id':'pb'}]}}

class ResolutionAuditTests(unittest.TestCase):
 def test_historical_matches_survive_catalog_rollover(self):
  old={**MATCH,'kalshi':{**MATCH['kalshi'],'event_id':'old'},'polymarket':{**MATCH['polymarket'],'event_id':'p-old'}}
  newer={**MATCH,'kalshi':{**MATCH['kalshi'],'event_id':'new'},'polymarket':{**MATCH['polymarket'],'event_id':'p-new'}}
  duplicate={**old,'participants':['A','B','latest-evidence']}
  rows=unique_historical_matches([{'matches':[old]},{'matches':[newer,duplicate]}])
  self.assertEqual([row['kalshi']['event_id'] for row in rows],['new','old'])
  self.assertEqual(rows[1]['participants'],['A','B','latest-evidence'])
 def test_final_agreement(self):
  k={'ka':{'market':{'status':'settled','result':'yes'}},'kb':{'market':{'status':'settled','result':'no'}}}
  p={'markets':[{'sportsMarketType':'moneyline','closed':True,'umaResolutionStatus':'resolved','outcomes':'["A", "B"]','outcomePrices':'["1", "0"]'}]}
  row=audit_match(MATCH,lambda x:k[x],lambda _:p);self.assertTrue(row['comparable']);self.assertTrue(row['agreement']);self.assertFalse(row['pricing_eligible'])
 def test_kalshi_finalized_is_final(self):
  k={'ka':{'market':{'status':'finalized','result':'yes'}},'kb':{'market':{'status':'finalized','result':'no'}}}
  p={'markets':[{'sportsMarketType':'moneyline','closed':True,'umaResolutionStatus':'resolved','outcomes':'["A", "B"]','outcomePrices':'["1", "0"]'}]}
  row=audit_match(MATCH,lambda x:k[x],lambda _:p);self.assertTrue(row['comparable']);self.assertEqual(row['kalshi_status'],'FINAL')
 def test_pending_never_compares(self):
  k={'ka':{'market':{'status':'inactive','result':''}},'kb':{'market':{'status':'inactive','result':''}}}
  p={'markets':[{'sportsMarketType':'moneyline','closed':False,'umaResolutionStatus':'proposed','outcomes':'["A", "B"]','outcomePrices':'["0.1", "0.9"]'}]}
  row=audit_match(MATCH,lambda x:k[x],lambda _:p);self.assertFalse(row['comparable']);self.assertIsNone(row['agreement'])

 def test_source_identifier_date_conflict_is_not_compared(self):
  match={**MATCH,'participants':['BOS','NYY'],'kalshi':{**MATCH['kalshi'],'event_id':'KXMLBGAME-26AUG291305BOSNYYG1'},'polymarket':{**MATCH['polymarket'],'source_url':'https://polymarket.com/event/mlb-bos-nyy-2026-06-06'}}
  def unexpected(_:str):
   self.fail('resolution fetch must not run for identity-review pairs')
  row=audit_match(match,unexpected,unexpected)
  self.assertFalse(row['comparable']);self.assertIsNone(row['agreement'])
  self.assertEqual(row['identity_cross_check'],'REVIEW_DATE_IDENTIFIER_CONFLICT')

if __name__=='__main__':unittest.main()