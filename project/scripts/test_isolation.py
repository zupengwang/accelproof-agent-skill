import json,os,socket,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);checks={}
for key,path,mode in [('contract_write',root/'specs/contract.yaml','a'),('oracle_read',root/'specs/oracles.json','r'),('private_sentinel_read',root/'work/private-sentinel.txt','r'),('runtime_write',root/'.venv/accelproof-denial-probe','w')]:
 try:
  with open(path,mode) as f:
   if mode=='r':f.read(1)
  checks[key]='UNEXPECTED_ALLOW'
 except PermissionError:checks[key]='DENIED'
s=socket.socket();s.settimeout(2)
try:s.connect(('1.1.1.1',443));checks['network']='UNEXPECTED_ALLOW'
except OSError:checks['network']='DENIED'
(out/'allowed.txt').write_text('ok');checks['output_write']='ALLOWED'
(out/'isolation-result.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks));assert all(v=='DENIED' for k,v in checks.items() if k!='output_write')
