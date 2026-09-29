"""Independent Arrow/Python comparator; never imported by candidate processes."""
import math
import pyarrow as pa
import pyarrow.parquet as pq
from .data import OUTPUT_SCHEMA
KEYS=['model_id','region','minute_ms']
FLOATS=['success_rate','mean_ttft_ms']
def logical(t):
 if pa.types.is_string(t) or pa.types.is_large_string(t):return 'string'
 return str(t)
def compare(expected,actual):
 if not isinstance(expected,pa.Table):expected=pq.read_table(expected)
 if not isinstance(actual,pa.Table):actual=pq.read_table(actual)
 diffs=[]
 if actual.column_names!=OUTPUT_SCHEMA.names:diffs.append({'kind':'column_order','expected':OUTPUT_SCHEMA.names,'actual':actual.column_names})
 for f in OUTPUT_SCHEMA:
  if f.name not in actual.column_names:continue
  if logical(actual.schema.field(f.name).type)!=logical(f.type):diffs.append({'kind':'dtype','column':f.name,'expected':logical(f.type),'actual':logical(actual.schema.field(f.name).type)})
 if diffs:return {'pass':False,'diffs':diffs,'rows':actual.num_rows}
 def index(t):
  d={}
  for row in t.to_pylist():
   key=tuple(row[c] for c in KEYS)
   if key in d:raise ValueError('Duplicate output group key')
   d[key]=row
  return d
 try:e,a=index(expected),index(actual)
 except ValueError as ex:return {'pass':False,'diffs':[{'kind':'duplicate_key','message':str(ex)}]}
 if set(e)!=set(a):diffs.append({'kind':'key_set','missing':list(set(e)-set(a))[:10],'extra':list(set(a)-set(e))[:10]})
 for k in e.keys()&a.keys():
  for c in OUTPUT_SCHEMA.names[3:]:
   x,y=e[k][c],a[k][c]
   xn=x is None;yn=y is None
   if xn!=yn:diffs.append({'kind':'null_mask','key':k,'column':c,'expected':None if xn else x,'actual':None if yn else y})
   elif not xn and ((c in FLOATS and not math.isclose(x,y,rel_tol=1e-9,abs_tol=1e-8)) or (c not in FLOATS and x!=y)):diffs.append({'kind':'value','key':k,'column':c,'expected':x,'actual':y})
 return {'pass':not diffs,'diffs':diffs[:30],'diff_count':len(diffs),'rows':actual.num_rows,'full_table':True,'rtol':1e-9,'atol':1e-8}
def verdict(parity,bench):
 if not parity:return 'FAILED'
 cpu=bench['optimized_cpu_same_structure']['samples'];gpu=bench['optimized_gpu']['samples']
 import statistics
 ratio=statistics.median(cpu)/statistics.median(gpu)
 if max(gpu)<=min(cpu)*.9:return 'VERIFIED_GAIN'
 if ratio<1/0.9:return 'KEEP_CPU'
 return 'NEEDS_REVIEW'
