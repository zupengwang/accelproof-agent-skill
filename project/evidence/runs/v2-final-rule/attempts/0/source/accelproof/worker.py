"""Fixed audited operations. --batch keeps one interpreter/backend alive across distinct inputs."""
import argparse,time,json,sys,resource,os,shutil
from pathlib import Path
started=time.perf_counter()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--policy',required=True);p.add_argument('--iterations',type=int,default=4);p.add_argument('--metrics',required=True);p.add_argument('--batch',action='store_true');a=p.parse_args()
from accelproof.pipeline import original,optimized
from accelproof.common import write,sha
import pyarrow
pyarrow.set_cpu_count(4);pyarrow.set_io_thread_count(4)
if a.mode=='optimized_gpu':import cudf as lib
else:import pandas as lib
isgpu=a.mode in ['optimized_gpu','original_cudf_pandas']
if isgpu:import cupy
policy=json.loads(Path(a.policy).read_text());samples=[];hashes=[];tasks=[]
inputs=[Path(x) for x in json.loads(Path(a.input).read_text())] if a.batch else sorted(Path(a.input).glob('*.parquet')) if Path(a.input).is_dir() else [Path(a.input)]
setup=time.perf_counter()-started
columns=['request_id','ts_ms','model_id','region','status','ttft_ms'] if policy.get('read_strategy')=='projected' and not a.mode.startswith('original') else None
for i in range(a.iterations):
 if isgpu:cupy.cuda.runtime.deviceSynchronize()
 t=time.perf_counter()
 for j,source in enumerate(inputs):
  t_task=time.perf_counter();df=lib.read_parquet(source,**({'columns':columns} if columns else {}))
  out=original(df,lib) if a.mode.startswith('original') else optimized(df,lib,policy)
  target=Path(a.output).parent/(f'batch-{j}.parquet' if a.batch else source.name) if a.batch or Path(a.input).is_dir() else Path(a.output)
  out.to_parquet(target,index=False);del df,out
  if isgpu:cupy.cuda.runtime.deviceSynchronize()
  if a.batch:tasks.append({'input':str(source),'output':str(target),'seconds':time.perf_counter()-t_task,'pid':os.getpid(),'input_sha256':sha(source)})
 if isgpu:cupy.cuda.runtime.deviceSynchronize()
 samples.append(time.perf_counter()-t);hashes.append(sha(a.output) if Path(a.output).exists() else None)
 if Path(a.output).exists():shutil.copyfile(a.output,Path(a.output).with_name(f'sample-{i}.parquet'))
write(a.metrics,{'mode':a.mode,'warmup':samples[0] if a.iterations>1 else None,'samples':samples[1:] if a.iterations>1 else samples,'max_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024*1024 if sys.platform=='darwin' else 1024),'output_sha256':hashes,'includes':['parquet read','transform','serialize','GPU synchronize when applicable'],'pid':os.getpid(),'execution_profile':'persistent_batch' if a.batch else 'one_shot' if a.iterations==1 else 'warm_benchmark','setup_seconds':setup,'batch_tasks':tasks,'backend_imported':'cudf' if isgpu else 'pandas','read_strategy':policy.get('read_strategy','full')})
