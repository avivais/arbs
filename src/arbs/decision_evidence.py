"""Machine-readable decision evidence generated from immutable raw replay lineage."""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from arbs.ingestion.corpus import load_corpus
from arbs.parsers import PARSER_VERSION,replay_decisions

POLICY_VERSION="sports-equivalence-v1"
EVIDENCE_SCHEMA="1.0.0"


def canonical_hash(value:Any)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def build(corpus:Path)->dict[str,Any]:
 manifest,records=load_corpus(corpus);replay=replay_decisions(records)
 decisions=[]
 for parsed in replay['parse_decisions']:
  event=parsed.get('event');comparisons=[]
  if event:
   for field in ('event_id','participants','start_utc','title'):
    comparisons.append({'field':field,'normalized':event[field] if field!='start_utc' else str(event[field]),'status':'KNOWN'})
  evidence={'evidence_schema_version':EVIDENCE_SCHEMA,'policy_version':POLICY_VERSION,'parser_version':PARSER_VERSION,
            'canonical_schema_version':'1.0.0','matcher_version':'mlb-event-link-1.0.0','decision':parsed['decision'],
            'reason_codes':parsed['reason_codes'],'source_ids':parsed['source_ids'],'source_urls':parsed['source_urls'],
            'source_payload_sha256':parsed['source_hashes'],'received_at':parsed['received_at'],
            'source_field_paths':parsed['source_fields'],'bounded_excerpts':[],
            'transformations':parsed['transformations'],'normalized_comparisons':comparisons,
            'normalized_values':[{'value_path':c['field'],'value':c['normalized'],'source_payload_sha256':parsed['source_hashes'],
                                  'source_urls':parsed['source_urls'],'received_at':parsed['received_at'],
                                  'source_field_paths':parsed['source_fields'],'bounded_excerpts':[],
                                  'transformations':parsed['transformations']} for c in comparisons],
            'pricing_eligible':False,'pricing_disabled_reason':'PARSER_RESULT_NOT_EXACT_RULE_EQUIVALENCE'}
  evidence['decision_id']=canonical_hash(evidence);decisions.append(evidence)
 for m in replay['matches']:
  source_hashes=[];urls=[];received=[]
  ids={m['kalshi']['event_id'],m['polymarket']['event_id']}
  for parsed in replay['parse_decisions']:
   event=parsed.get('event')
   if event and event['event_id'] in ids:
    source_hashes.extend(parsed['source_hashes']);urls.extend(parsed['source_urls']);received.extend(parsed['received_at'])
  evidence={'evidence_schema_version':EVIDENCE_SCHEMA,'policy_version':POLICY_VERSION,'parser_version':PARSER_VERSION,
            'canonical_schema_version':'1.0.0','matcher_version':'mlb-event-link-1.0.0','decision':'REVIEW',
            'reason_codes':m['review_reasons'],'checks':m['checks'],'source_ids':[m['kalshi']['event_id'],m['polymarket']['event_id']],
            'source_urls':urls,'source_payload_sha256':source_hashes,'received_at':received,
            'source_field_paths':['event_ticker','markets[].gameStartTime','rules_primary','resolutionSource'],
            'bounded_excerpts':[m['kalshi']['rules'][:500],m['polymarket']['rules'][:500]],
            'transformations':['exact alias registry','UTC normalization','unique candidate gate'],
            'normalized_comparisons':[{'field':'participants','left':m['kalshi']['participants'],'right':m['polymarket']['participants'],'equal':True},
                                      {'field':'start_utc','left':m['kalshi']['start_utc'],'right':m['polymarket']['start_utc'],'equal':True},
                                      {'field':'material_rules','equal':False}],
            'normalized_values':[{'value_path':'event.participants','value':m['participants'],'source_payload_sha256':source_hashes,
                                  'source_urls':urls,'received_at':received,'source_field_paths':['title','teams[].name'],
                                  'bounded_excerpts':[],'transformations':['exact alias registry']},
                                 {'value_path':'event.start_utc','value':m['start_utc'],'source_payload_sha256':source_hashes,
                                  'source_urls':urls,'received_at':received,'source_field_paths':['rules_primary','markets[].gameStartTime'],
                                  'bounded_excerpts':[],'transformations':['timezone normalization']}],
            'ambiguity_set':[],'scenario_proof':{'complete_binary_outcome_space':True,'material_rules_equal':False},
            'pricing_eligible':False,'pricing_disabled_reason':'MATERIAL_RULE_EQUIVALENCE_NOT_PROVEN'}
  evidence['decision_id']=canonical_hash(evidence);decisions.append(evidence)
 return {'schema_version':EVIDENCE_SCHEMA,'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
         'corpus_id':manifest['corpus_id'],'corpus_records_sha256':manifest['records_sha256'],
         'counts':{'records':manifest['record_count'],'parse_decisions':len(replay['parse_decisions']),'matches':len(replay['matches']),'unpaired':len(replay['unpaired'])},
         'decisions':sorted(decisions,key=lambda x:x['decision_id']),'unpaired':replay['unpaired']}


def write(report:dict[str,Any],path:Path)->None:
 unsigned=dict(report);unsigned['report_sha256']=canonical_hash(unsigned);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(unsigned,indent=2,sort_keys=True,default=str)+'\n');tmp.replace(path)
