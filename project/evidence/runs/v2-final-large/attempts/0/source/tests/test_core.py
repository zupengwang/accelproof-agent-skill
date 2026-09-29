import unittest,tempfile,json
from pathlib import Path
import pyarrow as pa
from accelproof.data import OUTPUT_SCHEMA,fixtures
from accelproof.validation import compare,verdict
from accelproof.model import parse
from accelproof.harness import export_run
class Checks(unittest.TestCase):
 def test_large_integer_oracle(self):
  with tempfile.TemporaryDirectory() as d:
   c=fixtures(Path(d))[-1];self.assertEqual(c['input_records'][0]['ts_ms']//60000*60000,c['expected_rows'][0]['minute_ms'])
 def table(self,mean=10,region=None,count=2):return pa.Table.from_pylist([dict(model_id='a',region=region,minute_ms=0,request_count=count,success_count=2,success_rate=1.,mean_ttft_ms=mean)],schema=OUTPUT_SCHEMA)
 def test_zero_fill_rejected(self):self.assertFalse(compare(self.table(),self.table(5))['pass'])
 def test_null_mask_rejected(self):self.assertFalse(compare(self.table(None),self.table(0))['pass'])
 def test_nan_is_not_null(self):self.assertFalse(compare(self.table(None),self.table(float('nan')))['pass'])
 def test_lost_key_rejected(self):self.assertFalse(compare(self.table(),self.table(region='unknown'))['pass'])
 def test_int_exact(self):self.assertFalse(compare(self.table(count=2**53),self.table(count=2**53+1))['pass'])
 def test_dtype_rejected(self):
  t=self.table();i=t.column_names.index('mean_ttft_ms');t=t.set_column(i,'mean_ttft_ms',t.column(i).cast(pa.float32()));self.assertFalse(compare(self.table(),t)['pass'])
 def test_empty_schema(self):self.assertTrue(compare(pa.Table.from_pylist([],schema=OUTPUT_SCHEMA),pa.Table.from_pylist([],schema=OUTPUT_SCHEMA))['pass'])
 def test_duplicate_keys(self):self.assertFalse(compare(self.table(),pa.concat_tables([self.table(),self.table()]))['pass'])
 def test_closed_schema(self):
  with self.assertRaises(ValueError):parse('{"action":"exec","code":"rm"}')
 def test_decisions(self):
  b=lambda c,g:{'optimized_cpu_same_structure':{'samples':c},'optimized_gpu':{'samples':g}}
  self.assertEqual(verdict(True,b([1,1,1],[.5,.5,.5])),'VERIFIED_GAIN')
  self.assertEqual(verdict(True,b([.05]*3,[.07]*3)),'KEEP_CPU')
  self.assertEqual(verdict(True,b([1,1,1],[.7,.8,1.1])),'NEEDS_REVIEW')
  self.assertEqual(verdict(False,b([1]*3,[.5]*3)),'FAILED')
 def test_export_gate(self):
  import accelproof.harness as h
  old=h.STATE
  with tempfile.TemporaryDirectory() as d:
   h.STATE=Path(d);r=Path(d)/'runs'/'test';r.mkdir(parents=True);(r/'run.json').write_text(json.dumps({'status':'FAILED'}))
   try:
    with self.assertRaises(ValueError):export_run('test',True)
   finally:h.STATE=old
if __name__=='__main__':unittest.main()
