import hashlib,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=Path(os.environ.get('ACCELPROOF_STATE',ROOT/'state'))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False));tmp.replace(p)
def read(p):return json.loads(Path(p).read_text())
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
