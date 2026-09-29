"""Export read-only interactive UI from v2 snapshots and measured records."""
import json,difflib,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'preview';D.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
runs=[read(p) for p in sorted((R/'evidence/runs').glob('*/run.json'))]
runs.sort(key=lambda s:(s['scenario']!='large',s['id']))
api={'/api/runs':runs,'/api/contract':{'text':(R/'specs/contract.yaml').read_text(),'sha256':hashlib.sha256((R/'specs/contract.yaml').read_bytes()).hexdigest()},'/api/skills':[dict(name=p.parent.name,kind='custom',text=p.read_text(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((R/'skills').glob('*/SKILL.md'))]+[dict(name='accelerated-computing-cudf',kind='NVIDIA upstream',sha256=hashlib.sha256((R/'vendor/nvidia/accelerated-computing-cudf/SKILL.md').read_bytes()).hexdigest())]}
for s in runs:
 prefix='/api/runs/'+s['id'];api[prefix]=s;api[prefix+'/artifacts']=[];arr=[];directory=R/'evidence/runs'/s['id']
 for p in sorted((directory/'attempts').glob('*/snapshot.json'),key=lambda p:int(p.parent.name)):
  m=read(p);policy=read(p.parent/'policy.json');src=(p.parent/'source/accelproof/pipeline.py').read_text();a=src.index('def original');b=src.index('def optimized');previous=arr[-1]['policy'] if arr else {}
  diff=lambda x,y:'\n'.join(difflib.unified_diff(x.splitlines(),y.splitlines(),lineterm=''))
  checks=directory/f'candidate-{m["attempt"]}-parity.json'
  arr.append(dict(attempt=m['attempt'],candidate_id=m['candidate_id'],policy=policy,policy_diff=diff(json.dumps(previous,indent=2),json.dumps(policy,indent=2)),original=src[a:b],candidate=src[b:],diff=diff(src[a:b],src[b:]),checks=read(checks) if checks.exists() else [],path='frozen snapshot/pipeline.py'))
 api[prefix+'/attempts']=arr
html=(R/'web/index.html').read_text().replace('v2 / 候选绑定与部署验证','v2 离线回放 / 真实记录').replace('数据为固定种子的合成日志。指标来自远程真实运行；未运行时不展示测量值。','离线版回放已保存的真实记录，禁止启动和重新导出。完整证据在 project/evidence。')
shim='window.OFFLINE=true;window.fetch=async(path,options)=>{if(options?.method)throw Error("离线版不能启动或导出");if(!(path in SAVED))throw Error("没有此离线记录");return new Response(JSON.stringify(SAVED[path]),{status:200})};'
extra="$('downloadMock').onclick=()=>{if(current){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:'application/json'}));a.download=current.id+'.json';a.click()}};"
embed='<script>const SAVED='+json.dumps(api,ensure_ascii=False).replace('<','\\u003c')+';'+shim+'</script><script>'+(R/'web/app.js').read_text()+extra+'</script>'
(D/'index.html').write_text(html.replace('<script src="/static/app.js"></script>',embed));print(D/'index.html')
