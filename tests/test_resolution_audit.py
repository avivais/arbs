import unittest
from arbs.resolution_audit import audit_match

MATCH={'participants':['A','B'],'kalshi':{'event_id':'ke','contracts':[{'id':'ka','selected_team':'A'},{'id':'kb','selected_team':'B'}]},'polymarket':{'event_id':'pe','contracts':[{'selected_team':'A','token_id':'pa'},{'selected_team':'B','token_id':'pb'}]}}

class ResolutionAuditTests(unittest.TestCase):
 def test_final_agreement(self):
  k={'ka':{'market':{'status':'settled','result':'yes'}},'kb':{'market':{'status':'settled','result':'no'}}}
  p={'markets':[{'sportsMarketType':'moneyline','closed':True,'umaResolutionStatus':'resolved','outcomes':'["A", "B"]','outcomePrices':'["1", "0"]'}]}
  row=audit_match(MATCH,lambda x:k[x],lambda _:p);self.assertTrue(row['comparable']);self.assertTrue(row['agreement']);self.assertFalse(row['pricing_eligible'])
 def test_pending_never_compares(self):
  k={'ka':{'market':{'status':'inactive','result':''}},'kb':{'market':{'status':'inactive','result':''}}}
  p={'markets':[{'sportsMarketType':'moneyline','closed':False,'umaResolutionStatus':'proposed','outcomes':'["A", "B"]','outcomePrices':'["0.1", "0.9"]'}]}
  row=audit_match(MATCH,lambda x:k[x],lambda _:p);self.assertFalse(row['comparable']);self.assertIsNone(row['agreement'])

if __name__=='__main__':unittest.main()