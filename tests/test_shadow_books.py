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


class CheckpointTests(unittest.TestCase):
 def test_scalar_distributions_and_window(self):
  with tempfile.TemporaryDirectory() as directory:
   paths=[]
   for i in range(100):
    value={'status':'complete','started_at':f'2026-08-12T00:00:{i % 60:02d}Z','receipt_skew_ms':112,
           'kalshi':{'request_elapsed_ms':20,'source_time_status':'available','source_age_at_receipt_ms':1200},
           'polymarket':{'request_elapsed_ms':40,'source_time_status':'unavailable','source_age_at_receipt_ms':99999}}
    path=Path(directory)/f'{i}.json';path.write_text(json.dumps(value));paths.append(path)
   failed=Path(directory)/'failed.json';failed.write_text('{"status":"failed"}');paths.append(failed)
   value=summarize(list(reversed(paths)),include_window=True)
  self.assertEqual(value['sample_count'],100)
  self.assertEqual(value['failure_count'],1)
  self.assertEqual(value['receipt_skew_ms'],{'p50':112,'p95':112,'p99':112,'max':112})
  self.assertEqual(value['request_elapsed_ms']['p50'],30)
  self.assertEqual(value['source_age_ms']['sample_count'],100)
  self.assertEqual(value['source_age_ms']['max'],1200)
  self.assertEqual(value['suggested_limits'],{'pair_skew_ms':200,'source_age_ms':2000})
  self.assertEqual(value['threshold_status'],'READY_FOR_REVIEW')
  self.assertEqual(value['evidence_window']['elapsed_seconds'],59)
  self.assertEqual(summarize([],include_window=True)['evidence_window'],{'first':None,'last':None,'elapsed_seconds':0})

 def test_summary_does_not_retain_nested_payloads(self):
  import weakref
  from unittest.mock import Mock
  class Payload(dict):pass
  alive=weakref.WeakValueDictionary()
  def decode(_):
   self.assertLessEqual(len(alive),1,'only the preceding decoded sample may still be alive')
   payload=Payload(orderbook={'levels':['large nested book']})
   alive[id(payload)]=payload
   return {'status':'complete','receipt_skew_ms':12,
           'kalshi':{'request_elapsed_ms':20,'payload':payload},
           'polymarket':{'request_elapsed_ms':40,'payload':payload}}
  with patch('arbs.shadow_books.json.loads',side_effect=decode):
   result=summarize([Mock() for _ in range(5)])
  self.assertEqual(result['sample_count'],5)
  self.assertEqual(len(alive),0)

 def test_checkpoint_cutoff_replay_and_atomic_failure(self):
  import os
  import runpy
  import subprocess
  import sys
  from datetime import datetime,timezone
  script=Path(__file__).resolve().parents[1]/'scripts/build_shadow_checkpoint.py'
  module=runpy.run_path(str(script))
  with self.assertRaises(ValueError):module['parse_cutoff']('2026-08-12T00:00:00')
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);books=root/'books';books.mkdir();reports=root/'reports';reports.mkdir()
   old=books/'old.json';old.write_text('{"status":"failed"}');os.utime(old,ns=(2000000000000,2000000000000))
   later=books/'later.json';later.write_text('invalid excluded input');os.utime(later,ns=(2000000000001,2000000000001))
   (books/'partial.json.tmp').write_text('unpublished')
   cutoff=datetime.fromtimestamp(2000,timezone.utc)
   paths,metadata=module['snapshot'](books,cutoff)
   self.assertEqual(paths,[old]);self.assertEqual(metadata['file_count'],1)
   output=root/'checkpoint.json'
   command=[sys.executable,str(script),'--books',str(books),'--reports',str(reports),'--output',str(output),'--cutoff',cutoff.isoformat()]
   subprocess.run(command,check=True,capture_output=True,text=True)
   first=json.loads(output.read_text())
   self.assertEqual(output.stat().st_mode & 0o777,0o644)
   subprocess.run(command,check=True,capture_output=True,text=True)
   second=json.loads(output.read_text())
   first.pop('generated_at');second.pop('generated_at');self.assertEqual(first,second)
   self.assertEqual(first['timing']['failure_count'],1)
   self.assertEqual(first['gate_status'],'PARTIAL_EVIDENCE_ONLY')
   self.assertEqual(first['input_snapshot']['books'],metadata)
   previous=output.read_bytes()
   with patch('os.replace',side_effect=OSError('simulated publication failure')):
    with self.assertRaises(OSError):module['atomic_write'](output,{'new':True})
   self.assertEqual(output.read_bytes(),previous)
   self.assertEqual(list(root.glob('.*.tmp')),[])
   old.write_text('broken frozen input');os.utime(old,(1000,1000))
   failed=subprocess.run(command,capture_output=True,text=True)
   self.assertNotEqual(failed.returncode,0);self.assertEqual(output.read_bytes(),previous)


if __name__=='__main__':unittest.main()
