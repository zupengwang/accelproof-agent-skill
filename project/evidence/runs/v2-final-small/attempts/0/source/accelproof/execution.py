import os,sys,subprocess,time,signal,statistics
from pathlib import Path
from .common import ROOT,write,read
MODES=['original_cpu','original_cudf_pandas','optimized_cpu_same_structure','optimized_gpu']
def worker(mode,inp,out,policy,folder,iterations=4,profile=False,root=ROOT,batch=False,portable_cpu=False):
 ROOT=Path(root)
 import psutil
 folder.mkdir(parents=True,exist_ok=True);out=out.resolve();metric=folder/'metrics.json'
 cfg={'dirs':[str(ROOT),str(ROOT/'accelproof')],'read':['/usr','/lib','/lib64','/proc','/sys','/etc/ld.so.cache','/etc/localtime','/etc/os-release',str(Path(sys.executable).resolve().parents[1]),str(ROOT/'.venv'),str(Path(sys.prefix)),str((Path(sys.prefix)/f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/nvidia/cu13').resolve()),str(ROOT/'accelproof/__init__.py'),str(ROOT/'accelproof/worker.py'),str(ROOT/'accelproof/pipeline.py'),str(ROOT/'accelproof/common.py'),str(inp.resolve()),str(policy.resolve())]+([str(Path(x).resolve()) for x in read(inp)] if batch else []),'write':[str(folder.resolve())]}
 write(folder/'sandbox.json',cfg)
 args=[sys.executable]
 if mode=='original_cudf_pandas':args+=['-m','cudf.pandas']+(['--profile'] if profile else [])
 args +=[str(ROOT/'accelproof/worker.py'),'--mode',mode,'--input',str(inp),'--output',str(out),'--policy',str(policy),'--iterations',str(iterations),'--metrics',str(metric)]
 if batch:args+=['--batch']
 if portable_cpu and mode not in ('original_cpu','optimized_cpu_same_structure'):raise ValueError('Portable path supports CPU only')
 cmd=args if portable_cpu else ['unshare','-Urn',sys.executable,str(ROOT/'accelproof/sandbox.py'),str(folder/'sandbox.json')]+args
 env=dict(os.environ,CUDA_VISIBLE_DEVICES='0' if mode in ('original_cudf_pandas','optimized_gpu') else '',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',NUMBA_NUM_THREADS='4',PYTHONPATH=str(ROOT))
 t=time.monotonic();peak=0
 with open(folder/'stdout.log','w') as so,open(folder/'stderr.log','w') as se:
  # Shares controller process group: API cancellation kills every descendant.
  proc=subprocess.Popen(cmd,env=env,stdout=so,stderr=se)
  while proc.poll() is None:
   try:
    p=psutil.Process(proc.pid);rss=sum(q.memory_info().rss for q in [p]+p.children(recursive=True));peak=max(peak,rss)
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   if time.monotonic()-t>240 or peak>12*1024**3:
    for q in p.children(recursive=True):
     try:q.kill()
     except psutil.NoSuchProcess:pass
    proc.kill();proc.wait();raise RuntimeError('Worker time/RSS limit exceeded')
   time.sleep(.1)
 if proc.returncode:raise RuntimeError(f'{mode} exit {proc.returncode}: '+(folder/'stderr.log').read_text()[-1800:])
 m=read(metric);m.update(process_wall_seconds=time.monotonic()-t,observed_peak_rss_mib=peak/1024**2,sandbox='trusted CPU workflow subprocess; no OS sandbox' if portable_cpu else 'network namespace + Landlock ABI >=3 + resource limits + RSS watchdog',median_seconds=statistics.median(m['samples']))
 write(metric,m);return m
