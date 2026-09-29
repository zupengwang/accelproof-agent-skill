"""Content binding against accidental edits. Not authentication against the directory owner."""
import hashlib,json,shutil,zipfile,stat
from pathlib import Path,PurePosixPath
from .common import ROOT,sha,read,write,now
SOURCE_PATTERNS=['accelproof/*.py','specs/*','skills/**/*','vendor/**/*','tests/*.py','scripts/replay_workflow.py','scripts/bootstrap_4090_runtime.py','requirements*.txt','LICENSE','WORKFLOW_README.md']
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def source_files(root=ROOT):
 return {str(p.relative_to(root)):p for pattern in SOURCE_PATTERNS for p in root.glob(pattern) if p.is_file() and '__pycache__' not in p.parts}
def current_identity(root=ROOT):return {n:sha(p) for n,p in source_files(root).items()}
def snapshot(run_dir,attempt,policy,environment,inputs,root=ROOT):
 target=run_dir/'attempts'/str(attempt);target.mkdir(parents=True,exist_ok=False)
 # All execution sources and judging rules are copied before validation.
 files=source_files(root)
 # Web assets support import/help in the portable project without being candidate logic.
 files.update({str(p.relative_to(root)):p for p in (root/'web').glob('*') if p.is_file()})
 for n,p in files.items():
  q=target/'source'/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 write(target/'policy.json',policy);write(target/'environment.json',environment)
 meta={'version':2,'attempt':attempt,'policy_sha256':sha(target/'policy.json'),'environment_sha256':sha(target/'environment.json'),'files':{n:sha(p) for n,p in files.items()},'protected_files':current_identity(root),'inputs':inputs}
 meta['candidate_id']=digest(meta);write(target/'snapshot.json',meta)
 return target,meta

def verify_snapshot(target):
 meta=read(target/'snapshot.json');identity=meta.pop('candidate_id')
 if digest(meta)!=identity:raise ValueError('Candidate snapshot identity changed')
 meta['candidate_id']=identity
 for n,h in meta['files'].items():
  if sha(target/'source'/n)!=h:raise ValueError('Snapshot source changed: '+n)
 if sha(target/'policy.json')!=meta['policy_sha256']:raise ValueError('Snapshot policy changed')
 if sha(target/'environment.json')!=meta['environment_sha256']:raise ValueError('Snapshot environment changed')
 return meta

def seal(run_dir,state,target,root=ROOT):
 meta=verify_snapshot(target)
 for entry in meta['inputs']:
  if sha(entry['path'])!=entry['sha256']:raise ValueError('Input changed during validation')
 if current_identity(root)!=meta['protected_files']:raise ValueError('Protected source changed during validation')
 if sha(run_dir/'candidate-policy.json')!=meta['policy_sha256']:raise ValueError('Candidate changed during validation')
 artifacts={str(p.relative_to(run_dir)):sha(p) for p in run_dir.rglob('*') if p.is_file() and 'attempts' not in p.parts and p.name not in ['run.json','controller.log','validation-record.json'] and p.suffix in ['.json','.parquet']}
 record={'version':2,'candidate_id':meta['candidate_id'],'snapshot':str(target.relative_to(run_dir)),'validation_status':state['validation_status'],'measurement':state.get('measurement',{}),'deployment':state.get('deployment',{}),'artifacts':artifacts,'created':now(),'assurance':'content consistency; not source authentication against an owner who can rewrite the whole evidence directory'}
 # Exclusive creation: the controller never reseals a historical run in place.
 path=run_dir/'validation-record.json'
 with path.open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2)
 return sha(path)

def verify_record(run_dir,state,root=ROOT,check_current=True):
 if not state.get('finalized') or state.get('validation_status')!='PASS':raise ValueError('Run has not committed a validated terminal state')
 path=run_dir/'validation-record.json'
 if sha(path)!=state.get('validation_record_sha256'):raise ValueError('Validation record changed')
 rec=read(path);target=run_dir/rec['snapshot'];meta=verify_snapshot(target)
 if rec['candidate_id']!=meta['candidate_id'] or state.get('candidate_id')!=meta['candidate_id']:raise ValueError('Candidate identity mismatch')
 if rec['deployment']!=state.get('deployment') or rec['measurement']!=state.get('measurement'):raise ValueError('Deployment recommendation changed')
 if sha(run_dir/'candidate-policy.json')!=meta['policy_sha256']:raise ValueError('Validated policy changed; revalidation required')
 if check_current and current_identity(root)!=meta['protected_files']:raise ValueError('Protected source changed; revalidation required')
 for n,h in rec['artifacts'].items():
  if sha(run_dir/n)!=h:raise ValueError('Validated artifact changed: '+n)
 return rec,target,meta

def export_archive(run_dir,state,profile,approved,root=ROOT):
 if not approved:raise ValueError('Explicit local export approval required')
 rec,target,meta=verify_record(run_dir,state,root)
 decision=rec['deployment'].get(profile)
 if not decision or decision['status']!='MEASURED' or decision['recommended_backend'] not in ['cpu','gpu']:raise ValueError('Execution profile has no validated deployment measurement')
 files={n:target/'source'/n for n in meta['files']}
 files['README.md']=target/'source/WORKFLOW_README.md'
 files.update({'workflow/policy.json':target/'policy.json','workflow/environment.json':target/'environment.json','workflow/snapshot.json':target/'snapshot.json','workflow/validation-record.json':run_dir/'validation-record.json'})
 manifest={'format':'accelproof.workflow.v2','run_id':state['id'],'candidate_id':rec['candidate_id'],'validation_status':'PASS','validation_record_sha256':sha(run_dir/'validation-record.json'),'execution_profile':profile,'recommended_backend':decision['recommended_backend'],'deployment':decision,'local_only':True,'files':{n:sha(p) for n,p in files.items()}}
 dest=run_dir/f'workflow-{profile}.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
  z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
 write(run_dir/f'export-{profile}.json',{'approved':True,'scope':'local_only','candidate_id':rec['candidate_id'],'zip_sha256':sha(dest)})
 return dest

def checked_extract(archive,target):
 """Only a new empty directory, exact file set, no symlinks or path aliases."""
 if any(target.iterdir()):raise ValueError('Extraction target must be empty')
 with zipfile.ZipFile(archive) as z:
  infos=z.infolist();names=[i.filename for i in infos]
  if len(names)!=len(set(names)) or len(names)>5000 or sum(i.file_size for i in infos)>1024**3:raise ValueError('Duplicate or oversized archive')
  for i in infos:
   n=i.filename;p=PurePosixPath(n);mode=i.external_attr>>16
   if not n or '\\' in n or p.is_absolute() or any(x in ('','.','..') for x in n.split('/')) or i.is_dir() or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0,stat.S_IFREG):raise ValueError('Unsafe member: '+n)
  m=json.loads(z.read('manifest.json'))
  if m.get('format')!='accelproof.workflow.v2' or set(names)!=set(m['files'])|{'manifest.json'}:raise ValueError('Archive members differ from manifest')
  for n,h in m['files'].items():
   if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Archive hash mismatch: '+n)
  record=json.loads(z.read('workflow/validation-record.json'));snap=json.loads(z.read('workflow/snapshot.json'));cid=snap.pop('candidate_id')
  expected=set(snap['files'])|{'README.md','workflow/policy.json','workflow/environment.json','workflow/snapshot.json','workflow/validation-record.json'}
  if set(m['files'])!=expected:raise ValueError('Unvalidated execution member or import shadow')
  if hashlib.sha256(z.read('README.md')).hexdigest()!=snap['files']['WORKFLOW_README.md']:raise ValueError('Workflow README changed')
  if hashlib.sha256(z.read('workflow/environment.json')).hexdigest()!=snap['environment_sha256']:raise ValueError('Environment identity changed')
  if digest(snap)!=cid or cid!=record['candidate_id'] or cid!=m['candidate_id']:raise ValueError('Candidate proof mismatch')
  if hashlib.sha256(z.read('workflow/validation-record.json')).hexdigest()!=m['validation_record_sha256']:raise ValueError('Record hash mismatch')
  if m['deployment']!=record['deployment'].get(m['execution_profile']) or m['recommended_backend']!=m['deployment']['recommended_backend']:raise ValueError('Backend recommendation mismatch')
  if hashlib.sha256(z.read('workflow/policy.json')).hexdigest()!=snap['policy_sha256']:raise ValueError('Policy binding mismatch')
  for n,h in snap['files'].items():
   if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Execution set differs from validated snapshot')
  z.extractall(target)
 return m
