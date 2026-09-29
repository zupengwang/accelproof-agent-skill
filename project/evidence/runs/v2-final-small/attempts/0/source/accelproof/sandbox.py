"""Fail-closed Linux Landlock filesystem policy, run inside an isolated network namespace.
This is a bounded audited-template runner, not an arbitrary untrusted-code service.
"""
import ctypes,os,sys,resource
from pathlib import Path
libc=ctypes.CDLL(None,use_errno=True)
class Ruleset(ctypes.Structure):_fields_=[('handled_access_fs',ctypes.c_uint64)]
class PathRule(ctypes.Structure):_pack_=1;_fields_=[('allowed_access',ctypes.c_uint64),('parent_fd',ctypes.c_int)]
def call(n,*args):
 r=libc.syscall(n,*args)
 if r<0:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
 return r
def restrict(readpaths,writepaths,dirpaths=()):
 abi=call(444,0,0,1)
 if abi<3:raise RuntimeError('Landlock ABI >=3 required')
 allfs=(1<<15)-1;rs=Ruleset(allfs);fd=call(444,ctypes.byref(rs),ctypes.sizeof(rs),0)
 def add(path,rights):
  path=Path(path)
  if not path.exists():return
  if not path.is_dir():rights&=(1<<0)|(1<<1)|(1<<2)|(1<<14)
  f=os.open(path,os.O_PATH|os.O_CLOEXEC);rule=PathRule(rights,f)
  call(445,fd,1,ctypes.byref(rule),0);os.close(f)
 for path in dirpaths:add(path,1<<3)
 for path in readpaths:add(path,(1<<0)|(1<<2)|(1<<3))
 for path in writepaths:add(path,allfs)
 # GPU device nodes and standard I/O are available; filesystem creation under /dev is not.
 for path in Path('/dev').glob('nvidia*'):add(path,(1<<1)|(1<<2))
 for path in ['/dev/null','/dev/urandom','/dev/random','/dev/zero']:add(path,(1<<1)|(1<<2))
 add('/dev/shm',1<<3)
 # CUDA names its own helper threads through /proc/self/task/*/comm.
 add('/proc/self/task',(1<<1)|(1<<14))
 if libc.prctl(38,1,0,0,0):raise OSError('no_new_privs')
 call(446,fd,0);os.close(fd)
 return abi
if __name__=='__main__':
 import json
 config=json.loads(Path(sys.argv[1]).read_text())
 resource.setrlimit(resource.RLIMIT_CPU,(180,185));resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_NOFILE,(1024,1024));resource.setrlimit(resource.RLIMIT_NPROC,(512,512))
 os.umask(0o077)
 restrict(config['read'],config['write'],config.get('dirs',[]))
 os.execvpe(sys.argv[2],sys.argv[2:],dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HOME=config['write'][0],TMPDIR=config['write'][0]))
