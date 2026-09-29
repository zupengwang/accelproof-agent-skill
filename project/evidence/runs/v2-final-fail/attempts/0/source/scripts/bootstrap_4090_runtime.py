"""Recreate this node's RAM-backed runtime without changing its existing model environment."""
import os,sys,json,subprocess,shutil,urllib.request,hashlib,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ACCELPROOF_MODEL_PYTHON','/home/wangzupeng/competitions/aic-grounding-20260916/.venv/bin/python')
RAM=Path('/dev/shm/accelproof-runtime-20260928');WHEELS=Path('/dev/shm/accelproof-wheels-20260928');WHEELS.mkdir(exist_ok=True)
if not RAM.exists():subprocess.run([BASE,'-m','venv',str(RAM)],check=True)
link=ROOT/'.venv'
if link.is_symlink():
 if link.resolve()!=RAM:raise RuntimeError('Unexpected existing runtime link')
elif link.exists():raise RuntimeError('Existing real .venv; use it or choose an empty project copy')
else:link.symlink_to(RAM,target_is_directory=True)
site=Path(subprocess.check_output([BASE,'-c','import site;print(site.getsitepackages()[0])'],text=True).strip());dst=RAM/'lib/python3.12/site-packages';(dst/'nvidia').mkdir(exist_ok=True)
lib=dst/'nvidia/cu13'
if not lib.exists():lib.symlink_to(site/'nvidia/cu13',target_is_directory=True)
allowed=['nvidia_cublas-','nvidia_cufft-','nvidia_curand-','nvidia_cusolver-','nvidia_cusparse-','nvidia_cufile-','nvidia_cuda_runtime-','nvidia_cuda_nvrtc-','nvidia_nvjitlink-','cuda_toolkit-','nvidia_cuda_cupti-','nvidia_nvtx-']
for d in site.glob('*.dist-info'):
 if any(d.name.startswith(a) for a in allowed) and not (dst/d.name).exists():shutil.copytree(d,dst/d.name)
items=json.loads((ROOT/'specs/dependency-wheels.json').read_text())
def fetch(it):
 p=WHEELS/it['filename']
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=it['sha256']:
  subprocess.run(['curl','-L','--fail','--retry','3','-sS','-o',str(p),it['url'].replace('https://files.pythonhosted.org','https://pypi.tuna.tsinghua.edu.cn')],check=True)
 if hashlib.sha256(p.read_bytes()).hexdigest()!=it['sha256']:raise RuntimeError('Wheel hash mismatch')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,items))
tmp=WHEELS/'pip-temp';tmp.mkdir(exist_ok=True)
env=dict(os.environ,TMPDIR=str(tmp))
subprocess.run([str(link/'bin/python'),'-m','pip','install','--no-index','--no-deps']+[str(WHEELS/i['filename']) for i in items],env=env,check=True)
subprocess.run([str(link/'bin/python'),'-m','pip','check'],check=True)
print('Runtime ready:',link,'->',RAM)
