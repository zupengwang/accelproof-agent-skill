"""Persisted process identity. Uncertain survivors block new scheduling."""
import os,signal,subprocess,time
from pathlib import Path
from .common import read,write,now
ACTIVE={'RUNNING','FINALIZING'}
def identity(pid):
 try:
  import psutil
  p=psutil.Process(pid)
  return {'pid':pid,'created':p.create_time(),'cmdline':p.cmdline(),'pgid':os.getpgid(pid),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip() if Path('/proc/sys/kernel/random/boot_id').exists() else None}
 except (ProcessLookupError,FileNotFoundError):return None
 except Exception:return None

def same_process(saved):
 actual=identity(saved['pid'])
 return bool(actual and actual==saved)

def group_alive(pgid):
 import psutil
 for p in psutil.process_iter(['pid','status']):
  try:
   if os.getpgid(p.pid)==pgid and p.info['status']!='zombie':return True
  except (ProcessLookupError,PermissionError,psutil.NoSuchProcess):pass
 return False

def reconcile(path,owned=None):
 s=read(path/'run.json')
 if s.get('status') not in ACTIVE:return s
 meta=read(path/'controller.json') if (path/'controller.json').exists() else None
 if owned is not None and owned.poll() is None:return s
 if meta and same_process(meta):s['supervision']='recovered_by_persisted_process_identity';return s
 alive=bool(meta and group_alive(meta['pgid']))
 if meta is None:
  s.update(status='RECOVERY_REQUIRED',finalized=True,finished=now(),error='Controller identity missing; cannot prove old work ended. Inspect processes before manually resolving this record.',scheduling_blocked=True);write(path/'run.json',s);return s
 s.update(status='RECOVERY_REQUIRED' if alive else 'INTERRUPTED',finalized=True,finished=now(),error='Controller identity lost; surviving process group needs review' if alive else 'Controller ended without terminal commit; no matching process group remains',scheduling_blocked=alive)
 write(path/'run.json',s);return s

def stop_group(saved):
 if not same_process(saved):raise ValueError('Cannot verify controller identity; refusing to signal a recycled PID')
 os.killpg(saved['pgid'],signal.SIGTERM)
 time.sleep(.3)
 # Group ID is allocated to this verified controller. Do not signal if it has disappeared.
 if group_alive(saved['pgid']):
  try:os.killpg(saved['pgid'],signal.SIGKILL)
  except ProcessLookupError:pass
