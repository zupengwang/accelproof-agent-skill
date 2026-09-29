import argparse
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from .common import ROOT,read,write,sha
INPUT_SCHEMA=pa.schema([(c,t) for c,t in [('request_id',pa.string()),('ts_ms',pa.int64()),('model_id',pa.string()),('region',pa.string()),('status',pa.string()),('input_tokens',pa.int64()),('output_tokens',pa.int64()),('ttft_ms',pa.float64())]])
OUTPUT_SCHEMA=pa.schema([(c,t) for c,t in [('model_id',pa.string()),('region',pa.string()),('minute_ms',pa.int64()),('request_count',pa.int64()),('success_count',pa.int64()),('success_rate',pa.float64()),('mean_ttft_ms',pa.float64())]])
def generate(path,n,seed):
 rng=np.random.default_rng(seed);path.parent.mkdir(parents=True,exist_ok=True)
 with pq.ParquetWriter(path,INPUT_SCHEMA,compression='snappy') as w:
  for start in range(0,n,250000):
   k=min(250000,n-start)
   regions=rng.choice(['cn-east','cn-west','eu','us',None],k)
   statuses=rng.choice(['ok','error','timeout','unknown',None],k,p=[.87,.06,.04,.02,.01])
   ttft=rng.lognormal(4,0.5,k);mask=rng.random(k)<.12
   arr=[pa.array(np.arange(start,start+k).astype(str)),pa.array(1720000000000+rng.integers(0,3600000,k,dtype=np.int64)),pa.array(rng.choice(['model-a','model-b','model-c'],k)),pa.array(regions,type=pa.string()),pa.array(statuses,type=pa.string()),pa.array(rng.integers(0,4096,k,dtype=np.int64)),pa.array(rng.integers(0,2048,k,dtype=np.int64)),pa.array(ttft,mask=mask)]
   w.write_table(pa.Table.from_arrays(arr,schema=INPUT_SCHEMA))
 write(path.with_suffix('.json'),{'rows':n,'seed':seed,'sha256':sha(path),'schema':str(INPUT_SCHEMA),'synthetic':True})
def fixtures(directory):
 directory.mkdir(parents=True,exist_ok=True)
 cases=read(ROOT/'specs/oracles.json')['semantic_cases']
 # Exact int64 millisecond value above float64's consecutive-integer limit.
 cases=cases+[{'id':'large_integer_bucket','input_records':[dict(request_id='big',ts_ms=9007199254799999,model_id='model-a',region=None,status='ok',input_tokens=2**53+1,output_tokens=1,ttft_ms=12.5)],'expected_rows':[dict(model_id='model-a',region=None,minute_ms=9007199254740000,request_count=1,success_count=1,success_rate=1.,mean_ttft_ms=12.5)]}]
 for c in cases:
  pq.write_table(pa.Table.from_pylist(c['input_records'],schema=INPUT_SCHEMA),directory/(c['id']+'.parquet'))
 return cases
if __name__=='__main__':
 from pathlib import Path
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('--rows',type=int,default=1000000);p.add_argument('--seed',type=int,default=20260928);a=p.parse_args();generate(a.path,a.rows,a.seed)
