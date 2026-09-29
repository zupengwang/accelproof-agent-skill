import asyncio,json,re,sqlite3,subprocess,sys,uuid,difflib
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict
from .common import ROOT,STATE,read,write,sha,now
from .harness import SCENARIOS,export_run
from .profiles import PROFILES
from .lifecycle import ACTIVE,identity,reconcile,stop_group
jobs={};STATE.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(STATE/'metadata.sqlite',check_same_thread=False);db.execute('CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, created TEXT)');db.commit()
@asynccontextmanager
async def lifespan(app):
 for p in (STATE/'runs').glob('*/run.json'):reconcile(p.parent,jobs.get(p.parent.name))
 yield
app=FastAPI(title='AccelProof v2',docs_url=None,redoc_url=None,lifespan=lifespan)
class Scenario(BaseModel):
 model_config=ConfigDict(extra='forbid')
 scenario:str='standard'
 execution_profile:str='one_shot'
class Approval(BaseModel):
 model_config=ConfigDict(extra='forbid')
 kind:str='local_export'
 approved:bool=False
 execution_profile:str='one_shot'
def runpath(id):
 if not re.fullmatch('[a-zA-Z0-9_-]+',id):raise HTTPException(400,'Invalid id')
 p=STATE/'runs'/id
 if not (p/'run.json').exists():raise HTTPException(404,'Run not found')
 return p
def sync_status(id):return reconcile(runpath(id),jobs.get(id))
@app.get('/')
def index():return FileResponse(ROOT/'web/index.html')
@app.post('/api/projects')
def project():
 id='project-'+uuid.uuid4().hex[:10];db.execute('INSERT INTO projects VALUES (?,?)',(id,now()));db.commit();return {'id':id,'contract_sha256':sha(ROOT/'specs/contract.yaml'),'scope':'synthetic request-log contract'}
@app.post('/api/projects/{pid}/runs')
def start(pid:str,body:Scenario):
 if not db.execute('SELECT id FROM projects WHERE id=?',(pid,)).fetchone():raise HTTPException(404,'Project not found')
 if body.scenario not in SCENARIOS or body.execution_profile not in PROFILES:raise HTTPException(400,'Unknown scenario/profile')
 if any((s:=sync_status(p.parent.name))['status'] in ACTIVE or s.get('scheduling_blocked') for p in (STATE/'runs').glob('*/run.json')):raise HTTPException(409,'An active or unresolved previous job blocks scheduling')
 id=body.scenario+'-'+uuid.uuid4().hex[:10];d=STATE/'runs'/id;d.mkdir(parents=True)
 write(d/'run.json',{'version':2,'id':id,'scenario':body.scenario,'execution_profile':body.execution_profile,'status':'RUNNING','finalized':False,'events':[],'bench':{},'parity':{},'rows':SCENARIOS[body.scenario][0]})
 with open(d/'controller.log','w') as f:jobs[id]=subprocess.Popen([sys.executable,'-m','accelproof.harness','--scenario',body.scenario,'--execution-profile',body.execution_profile,'--run-id',id],cwd=ROOT,stdout=f,stderr=f,start_new_session=True)
 meta=identity(jobs[id].pid)
 if meta:write(d/'controller.json',meta)
 return {'id':id}
@app.get('/api/runs')
def runs():return [sync_status(p.parent.name) for p in sorted((STATE/'runs').glob('*/run.json'),key=lambda p:p.stat().st_mtime,reverse=True)]
@app.get('/api/runs/{id}')
def get_run(id:str):return sync_status(id)
@app.get('/api/runs/{id}/events')
async def events(id:str,request:Request,after:int=0):
 runpath(id)
 try:after=max(after,int(request.headers.get('last-event-id','0')))
 except ValueError:raise HTTPException(400,'Bad event cursor')
 async def stream():
  cursor=after
  while not await request.is_disconnected():
   s=sync_status(id)
   for event in s.get('events',[]):
    if event['sequence']>cursor:
     cursor=event['sequence'];yield f'id: {cursor}\ndata: {json.dumps(event,ensure_ascii=False)}\n\n'
   if s.get('finalized') and s['status'] not in ACTIVE:
    yield 'event: done\ndata: '+json.dumps({'run_id':id,'status':s['status']})+'\n\n';return
   yield ': heartbeat\n\n';await asyncio.sleep(.3)
 return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache'})
@app.post('/api/runs/{id}/cancel')
async def cancel(id:str):
 p=runpath(id);s=sync_status(id)
 if s['status'] not in ACTIVE or not (p/'controller.json').exists():raise HTTPException(409,'No verified active controller')
 meta=read(p/'controller.json')
 try:await asyncio.to_thread(stop_group,meta)
 except ValueError as e:raise HTTPException(409,str(e))
 if id in jobs:jobs[id].wait(timeout=5)
 s=read(p/'run.json');s.update(status='CANCELLED',finalized=True,finished=now(),cancelled_process_group=meta['pgid']);write(p/'run.json',s);return {'status':'CANCELLED','process_group':meta['pgid']}
@app.post('/api/runs/{id}/approval')
def approve(id:str,body:Approval):
 runpath(id)
 if body.kind!='local_export' or body.execution_profile not in PROFILES:raise HTTPException(400,'Only a measured local workflow can be exported')
 try:p=export_run(id,approved=body.approved,profile=body.execution_profile)
 except (ValueError,FileNotFoundError,KeyError) as e:raise HTTPException(409,str(e))
 return {'artifact_url':f'/api/runs/{id}/download/'+p.name,'sha256':sha(p)}
@app.get('/api/runs/{id}/artifacts')
def artifacts(id:str):
 d=runpath(id);return [{'name':str(p.relative_to(d)),'bytes':p.stat().st_size,'url':f'/api/runs/{id}/download/'+str(p.relative_to(d))} for p in d.rglob('*') if p.is_file() and p.suffix in ['.json','.log','.zip']]
@app.get('/api/runs/{id}/download/{name:path}')
def download(id:str,name:str):
 d=runpath(id).resolve();p=(d/name).resolve()
 if not p.is_relative_to(d) or not p.is_file() or p.suffix not in ['.json','.log','.zip']:raise HTTPException(404,'Artifact not found')
 return FileResponse(p,filename=p.name)
@app.get('/api/contract')
def contract():return {'text':(ROOT/'specs/contract.yaml').read_text(),'sha256':sha(ROOT/'specs/contract.yaml')}
@app.get('/api/runs/{id}/attempts')
def attempts(id:str):
 d=runpath(id);result=[]
 for p in sorted((d/'attempts').glob('*/snapshot.json'),key=lambda p:int(p.parent.name)):
  meta=read(p);policy=read(p.parent/'policy.json');src=(p.parent/'source/accelproof/pipeline.py').read_text();a=src.index('def original');b=src.index('def optimized');orig=src[a:b];cand=src[b:];checks=read(d/f'candidate-{meta["attempt"]}-parity.json') if (d/f'candidate-{meta["attempt"]}-parity.json').exists() else []
  previous=result[-1]['policy'] if result else None;delta='\n'.join(difflib.unified_diff(json.dumps(previous or {},indent=2).splitlines(),json.dumps(policy,indent=2).splitlines(),fromfile='previous policy',tofile=f'attempt {meta["attempt"]}',lineterm=''))
  result.append({'attempt':meta['attempt'],'candidate_id':meta['candidate_id'],'policy':policy,'policy_diff':delta,'original':orig,'candidate':cand,'diff':'\n'.join(difflib.unified_diff(orig.splitlines(),cand.splitlines(),fromfile='audited original template',tofile='audited optimized template',lineterm='')),'checks':checks,'path':'snapshot/accelproof/pipeline.py'})
 return result
@app.get('/api/skills')
def skills():return [{'name':p.parent.name,'kind':'custom','sha256':sha(p),'text':p.read_text()} for p in sorted((ROOT/'skills').glob('*/SKILL.md'))]+[{'name':'accelerated-computing-cudf','kind':'NVIDIA upstream','sha256':sha(ROOT/'vendor/nvidia/accelerated-computing-cudf/SKILL.md'),'commit':read(ROOT/'vendor/nvidia/PROVENANCE.json')['commit']}]
app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static')
