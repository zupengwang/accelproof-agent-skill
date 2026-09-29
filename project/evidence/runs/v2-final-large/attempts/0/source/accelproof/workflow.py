"""Run an already validated workflow, or explicitly cross-verify CPU/GPU. No model calls."""
import argparse,json,os,sys,tempfile,subprocess,time
from pathlib import Path
from .common import read,write,sha
from .proof import checked_extract
from .profiles import select_backend

def input_rows(paths):
 import pyarrow.parquet as pq
 return [pq.ParquetFile(p).metadata.num_rows for p in paths]

def execute(archive,inputs,output,operation='run',portable_cpu=True):
 output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True);inputs=[Path(p).resolve() for p in inputs]
 rows=input_rows(inputs);started=time.monotonic()
 # Each import occurs in a fresh child interpreter rooted in a new verified extraction.
 with tempfile.TemporaryDirectory(prefix='accelproof-workflow-') as temp:
  target=Path(temp);manifest=checked_extract(archive,target);profile=manifest['execution_profile']
  if profile=='one_shot' and len(inputs)!=1:raise ValueError('one_shot requires exactly one input')
  if profile=='persistent_batch' and (len(inputs)<2 or len({sha(p) for p in inputs})!=len(inputs)):raise ValueError('persistent_batch requires distinct inputs')
  selected,scope=select_backend(manifest,rows)
  if operation=='verify':modes=['original_cpu','optimized_gpu']
  else:modes=['optimized_gpu' if selected=='gpu' else 'optimized_cpu_same_structure']
  uses_gpu=any('gpu' in m for m in modes);lock=None
  if uses_gpu:
   import fcntl
   lockpath=Path(os.environ.get('ACCELPROOF_GPU_LOCK','/tmp/accelproof-gpu0.lock'));lockpath.parent.mkdir(parents=True,exist_ok=True);lock=lockpath.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
  try:
   config={'inputs':[str(p) for p in inputs],'output':str(output),'modes':modes,'batch':profile=='persistent_batch','portable_cpu':portable_cpu,'policy':str(target/'workflow/policy.json')};write(output/'replay-config.json',config)
   script='''import json,sys\nfrom pathlib import Path\nfrom accelproof.execution import worker\nfrom accelproof.common import write\nc=json.loads(Path(sys.argv[1]).read_text());o=Path(c['output']);batch=c['batch'];inp=o/'batch-inputs.json'\nif batch:write(inp,c['inputs'])\nelse:inp=Path(c['inputs'][0])\nmetrics={}\nfor mode in c['modes']:\n d=o/mode;metrics[mode]=worker(mode,inp,d/'result.parquet',Path(c['policy']),d,iterations=1,batch=batch,portable_cpu=c['portable_cpu'] and mode in ['original_cpu','optimized_cpu_same_structure'])\nwrite(o/'execution.json',metrics)\n'''
   env=dict(os.environ,PYTHONPATH=str(target),PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='0' if uses_gpu else '')
   subprocess.run([sys.executable,'-c',script,str(output/'replay-config.json')],cwd=target,env=env,check=True)
   metrics=read(output/'execution.json');parity=None
   if operation=='verify':
    from .validation import compare
    names=[f'batch-{i}.parquet' for i in range(len(inputs))] if profile=='persistent_batch' else ['result.parquet']
    parity=[compare(output/'original_cpu'/n,output/'optimized_gpu'/n) for n in names]
    if not all(p['pass'] for p in parity):raise ValueError('Explicit cross-verification failed')
   result={'operation':operation,'selected_backend':selected if operation=='run' else 'cpu+gpu verification','execution_profile':profile,'candidate_id':manifest['candidate_id'],'source_workflow_sha256':sha(archive),'rows':rows,'input_sha256':[sha(p) for p in inputs],'scope':scope,'model_called':False,'gpu_worker_called':uses_gpu,'metrics':metrics,'parity':parity,'total_seconds':time.monotonic()-started,'assurance':'manifest verifies content consistency, not publisher identity; accept trusted project packages only'}
   write(output/'result.json',result);return result
  finally:
   if lock:lock.close()

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['run','verify']);p.add_argument('archive',type=Path);p.add_argument('--input',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--linux-isolation',action='store_true');a=p.parse_args(argv)
 print(json.dumps(execute(a.archive,a.input,a.output,a.operation,not a.linux_isolation),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
