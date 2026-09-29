"""Audit final evidence and source correspondence without rerunning GPU measurements."""
import json,hashlib,zipfile
from pathlib import Path
from accelproof.common import ROOT,read,sha,write
from accelproof.proof import current_identity,verify_snapshot
runs={p.parent.name:read(p) for p in (ROOT/'evidence/runs').glob('*/run.json')};identity=current_identity();checks={}
for name,s in runs.items():
 if not name.startswith('v2-final-'):continue
 d=ROOT/'evidence/runs'/name;meta=verify_snapshot(d/'attempts'/str(s['attempt']))
 assert meta['protected_files']==identity,name+' source mismatch'
 assert s['candidate_id']==meta['candidate_id']
 if s['scenario']=='fail':assert s['status']=='FAILED' and not s['bench']
 else:
  assert s['status']=='COMPLETED' and s['validation_status']=='PASS' and s['finalized'];record=read(d/'validation-record.json');assert sha(d/'validation-record.json')==s['validation_record_sha256'];assert record['candidate_id']==s['candidate_id']
  for n,h in record['artifacts'].items():assert sha(d/n)==h,name+': '+n
  for profile in ['one_shot','persistent_batch']:
   p=read(d/(profile+'-measurements.json'));assert all(x['pass'] for x in p['parity'])
   if profile=='persistent_batch':
    for m in p['results'].values():assert len({t['pid'] for t in m['batch_tasks']})==1 and len({t['input_sha256'] for t in m['batch_tasks']})==2
 checks[name]={'status':s['status'],'candidate_id':s['candidate_id'],'protected_files_match':len(identity),'validation':s['validation_status']}
clean=read(ROOT/'evidence/clean-cpu/result.json');assert not clean['model_called'] and not clean['gpu_worker_called'] and clean['selected_backend']=='cpu'
assert sha(ROOT/'evidence/runs/v2-final-small/workflow-one_shot.zip')==clean['source_workflow_sha256']
reuse=read(ROOT/'evidence/reuse-gpu/result.json');assert reuse['operation']=='verify' and all(p['pass'] for p in reuse['parity']) and not reuse['model_called'];assert sha(ROOT/'evidence/runs/v2-final-large/workflow-one_shot.zip')==reuse['source_workflow_sha256']
batch=read(ROOT/'evidence/reuse-batch/result.json');assert batch['execution_profile']=='persistent_batch' and not batch['gpu_worker_called'];assert sha(ROOT/'evidence/runs/v2-final-large/workflow-persistent_batch.zip')==batch['source_workflow_sha256']
write(ROOT/'evidence/final-review-acceptance.json',{'runs':checks,'clean_cpu_reuse':True,'gpu_cross_verification':True,'persistent_batch_reuse':True,'public_submission':False,'history_note':'Pre-YAML-fix runs are development evidence, never the final candidate identities.'});print(json.dumps(checks,indent=2))
