"""Audited template. Model chooses only closed-schema policies, never Python code."""
KEYS=['model_id','region','minute_ms']
COLS=KEYS+['request_count','success_count','success_rate','mean_ttft_ms']
def empty_frame(lib):
 return lib.DataFrame({c:lib.Series([],dtype=('str' if c in ['model_id','region'] else 'float64' if c in ['success_rate','mean_ttft_ms'] else 'int64')) for c in COLS})
def original(df,lib):
 if len(df)==0:return empty_frame(lib)
 df['minute_ms']=(df.ts_ms//60000)*60000
 ok=df.status.eq('ok').fillna(False)
 counts=df.groupby(KEYS,dropna=False).size().rename('request_count')
 success=df.loc[ok].groupby(KEYS,dropna=False).size().rename('success_count')
 means=df.loc[ok].groupby(KEYS,dropna=False).ttft_ms.mean().rename('mean_ttft_ms')
 out=counts.to_frame().join(success).join(means).reset_index()
 out['success_count']=out.success_count.fillna(0).astype('int64')
 out['request_count']=out.request_count.astype('int64')
 out['success_rate']=out.success_count/out.request_count
 out['mean_ttft_ms']=out.mean_ttft_ms.astype('float64')
 return out[COLS]
def optimized(df,lib,policy):
 if len(df)==0:return empty_frame(lib)
 # Integer bucketing and float64 are frozen; no model-controlled precision casts.
 df['minute_ms']=(df.ts_ms//60000)*60000
 ok=df.status.eq('ok').fillna(False)
 df['ok_count']=ok.astype('int64')
 values=df.ttft_ms.fillna(0) if policy['ttft_policy']=='fill_zero' else df.ttft_ms
 df['valid_ttft']=values.where(ok)
 out=df.groupby(KEYS,dropna=not policy['preserve_null_keys']).agg({'request_id':'count','ok_count':'sum','valid_ttft':'mean'}).reset_index()
 out=out.rename(columns={'request_id':'request_count','ok_count':'success_count','valid_ttft':'mean_ttft_ms'})
 for c in ['minute_ms','request_count','success_count']:out[c]=out[c].astype('int64')
 out['success_rate']=(out.success_count/out.request_count).astype('float64')
 out['mean_ttft_ms']=out.mean_ttft_ms.astype('float64')
 return out[COLS]
