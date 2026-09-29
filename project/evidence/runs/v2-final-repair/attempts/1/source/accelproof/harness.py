"""Bounded model decisions, immutable candidate copies, independent validation, atomic finish."""
import argparse,fcntl,json,os,re,subprocess,sys,time,traceback,uuid
from pathlib import Path
from .common import ROOT,STATE,sha,read,write,now
from .execution import worker,MODES
from .proof import snapshot,seal,export_archive,current_identity
from .profiles import deployment,PROFILES,rule_plan
SCENARIOS={'small':(1000,20260928),'standard':(1000000,20260928),'large':(5000000,20260928),'repair':(1000000,20260928),'fail':(1000,20260928)}
MODEL_PYTHON=os.environ.get('ACCELPROOF_MODEL_PYTHON','/home/wangzupeng/competitions/aic-grounding-20260916/.venv/bin/python')
MODEL_PATH=os.environ.get('ACCELPROOF_MODEL_PATH','/home/wangzupeng/competitions/aic-grounding-20260916/models/Qwen3-VL-8B-Instruct')
LOCK=Path(os.environ.get('ACCELPROOF_GPU_LOCK','/home/wangzupeng/oss-ai-infra/gpu-claims/gpu0.lock'))
def protected():return current_identity()
class Run:
 def __init__(self,id,scenario,execution_profile='one_shot',planner='model'):
  self.dir=STATE/'runs'/id;self.dir.mkdir(parents=True,exist_ok=True);self.seq=0;self.pending='FAILED';self.snapshot=None
  self.s={'version':2,'id':id,'scenario':scenario,'execution_profile':execution_profile,'planner':planner,'status':'RUNNING','finalized':False,'validation_status':'PENDING','started':now(),'events':[],'bench':{},'parity':{},'deployment':{},'measurement':{},'rows':SCENARIOS[scenario][0],'seed':SCENARIOS[scenario][1],'model':'Qwen3-VL-8B-Instruct' if planner=='model' else 'fixed-rule baseline','hardware':'RTX 4090','publication':'local_only','repairs':0,'fault_injection':scenario in ('repair','fail'),'contract_sha256':sha(ROOT/'specs/contract.yaml')}
  self.save()
 def save(self):write(self.dir/'run.json',self.s)
 def event(self,stage,msg,skill=None,kind='progress'):
  self.seq+=1;e={'run_id':self.s['id'],'sequence':self.seq,'timestamp':now(),'stage':stage,'event_type':kind,'message':msg}
  if skill:e.update(skill=skill,skill_sha256=sha(ROOT/'skills'/skill/'SKILL.md'))
  self.s['events'].append(e);self.save()
 def model(self,prompt,tag):
  if self.s['planner']=='rule':
   plan=rule_plan(prompt);write(self.dir/(tag+'-response.json'),[{'plan':plan,'condition':'rule','model_called':False}]);return plan
  request={'id':tag,'prompt':prompt,'condition':'all','stage':'repair' if tag.startswith('repair') else 'migrate'};write(self.dir/(tag+'-request.json'),[request])
  cmd=[MODEL_PYTHON,str(ROOT/'accelproof/model.py'),'--model',MODEL_PATH,'--requests',str(self.dir/(tag+'-request.json')),'--output',str(self.dir/(tag+'-response.json'))]
  with open(self.dir/(tag+'-model.log'),'w') as f:subprocess.run(cmd,stdout=f,stderr=f,check=True,timeout=180,env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='4'))
  record=read(self.dir/(tag+'-response.json'))[0]
  if not record['schema_valid']:raise RuntimeError('Model output violates closed policy schema')
  return record['plan']
 def fixtures(self,tag,modes):
  import pyarrow as pa
  from .data import fixtures,OUTPUT_SCHEMA
  from .validation import compare
  cases=fixtures(self.dir/'fixture-inputs');result=[]
  for mode in modes:
   folder=self.dir/'workers'/tag/mode;worker(mode,self.dir/'fixture-inputs',folder/'unused.parquet',self.snapshot/'policy.json',folder,iterations=1,root=self.snapshot/'source')
   for c in cases:
    r=compare(pa.Table.from_pylist(c['expected_rows'],schema=OUTPUT_SCHEMA),folder/(c['id']+'.parquet'));r.update(case_id=c['id'],mode=mode);result.append(r)
  write(self.dir/(tag+'-parity.json'),result);return result
 def run(self):
  from .data import generate
  from .validation import compare,verdict
  import pyarrow.parquet as pq
  start=time.monotonic();n,seed=SCENARIOS[self.s['scenario']];dataset_root=Path(os.environ.get('ACCELPROOF_DATASETS',STATE/'datasets'));dataset_root.mkdir(parents=True,exist_ok=True)
  data=dataset_root/f'requests-{n}-{seed}.parquet';second=dataset_root/f'requests-{n}-{seed+1}.parquet'
  for p,k in [(data,seed),(second,seed+1)]:
   if not p.exists():generate(p,n,k)
  inputs=[{'path':str(p.resolve()),'sha256':sha(p),'rows':pq.ParquetFile(p).metadata.num_rows} for p in [data,second]]
  self.s.update(input_sha256=inputs[0]['sha256'],input_bytes=data.stat().st_size);self.event('intake','读取数据规模、冻结契约与运行模式；两个不同种子的输入','log-pipeline-intake')
  LOCK.parent.mkdir(parents=True,exist_ok=True)
  with LOCK.open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied; no workload interrupted')
   environment={'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv'],text=True),'python':sys.version,'packages':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines(),'cpu_threads':4,'input_storage':str(data.resolve()),'runtime':str(Path(sys.prefix).resolve()),'source_identity':protected()};write(self.dir/'environment.json',environment)
   prompt=f'Migrate {n} synthetic request-log rows. Contract: preserve null key groups; only status ok succeeds; TTFT mean uses successful nonnull values; float64. Execution mode is {self.s["execution_profile"]}. Extra input/output token columns are unused. Choose full or projected Parquet read strategy and the next mode-specific experiment. CPU is a safe proposal until this mode is measured.'
   self.event('generate','模型按阶段加载技能，选择读取策略和下一项运行模式实验','gpu-pipeline-migrate');policy=self.model(prompt,'initial');self.s['model_policy']=policy
   if policy['action']!='migrate':self.pending='NEEDS_REVIEW';self.event('decision','模型请求澄清或拒绝，未启动候选');return
   if self.s['fault_injection']:policy=dict(policy,ttft_policy='fill_zero');self.event('inject','显式故障注入：缺失 TTFT 补零；保留原始模型决策',kind='fault_injection')
   for attempt in range(3):
    self.s['candidate_policy']=policy;write(self.dir/'candidate-policy.json',policy)
    self.snapshot,meta=snapshot(self.dir,attempt,policy,environment,inputs);self.s['candidate_id']=meta['candidate_id'];self.s['attempt']=attempt
    self.event('snapshot',f'候选 attempt {attempt} 已冻结：策略、模板、判卷规则、输入与环境绑定')
    if attempt==0:
     baseline=self.fixtures('baseline',['original_cpu','original_cudf_pandas'])
     if not all(x['pass'] for x in baseline):raise RuntimeError('Original baseline failed independent oracle')
    checks=self.fixtures(f'candidate-{attempt}',['optimized_cpu_same_structure','optimized_gpu']);self.s['parity']={'pass':all(x['pass'] for x in checks),'passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks};self.save()
    if self.s['parity']['pass']:break
    self.event('validate','候选未通过，禁止测速与有效导出','dataframe-parity-benchmark','validation_failed')
    if self.s['scenario']=='fail' or attempt==2:self.s['validation_status']='FAIL';return
    feedback=[{'case':x['case_id'],'diffs':x['diffs'][:2]} for x in checks if not x['pass']][:3]
    policy=self.model('Repair unchanged contract. Exclude missing successful TTFT; do not fill zero. Preserve read_strategy and next_experiment from '+json.dumps(policy)+'. Differences: '+json.dumps(feedback,ensure_ascii=False),'repair-'+str(attempt+1));self.s['repairs']+=1
    if policy['action']!='migrate':self.pending='NEEDS_REVIEW';return
    self.event('repair','模型返回新策略；原 attempt 与错误值完整保留','gpu-pipeline-migrate')
   results={};outputs={}
   for mode in MODES:
    self.event('benchmark','预热后四配置测量：'+mode);folder=self.dir/'workers/timing'/mode;outputs[mode]=folder/'result.parquet';results[mode]=worker(mode,data,outputs[mode],self.snapshot/'policy.json',folder,root=self.snapshot/'source');self.s['bench']=results;self.save()
   full={m:compare(outputs['original_cpu'],p) for m,p in outputs.items()};samples={m:[compare(outputs['original_cpu'],q) for q in p.parent.glob('sample-*.parquet')] for m,p in outputs.items()};write(self.dir/'full-parity.json',full);write(self.dir/'sample-parity.json',samples)
   passed=all(r['pass'] for r in full.values()) and all(r['pass'] for arr in samples.values() for r in arr)
   if not passed:raise RuntimeError('Full or sample parity failed')
   self.s.update(full_parity=full,sample_parity_pass=True);self.s['parity']['full_pass']=True
   warm=results['optimized_cpu_same_structure']['median_seconds']/results['optimized_gpu']['median_seconds'];self.s.update(speedup=warm,overall_speedup=results['original_cpu']['median_seconds']/results['optimized_gpu']['median_seconds'])
   self.s['measurement']={'warm_speedup':warm,'warm_verdict':verdict(True,results),'warm_scope':{'rows':n,'warmups':1,'measurements':3}}
   # The model actually determines which measured profile experiment runs first.
   order=[policy['next_experiment']]+[p for p in PROFILES if p!=policy['next_experiment']];self.s['experiment_order']=order
   for profile in order:
    self.event('deployment','测量实际部署模式：'+profile)
    isbatch=profile=='persistent_batch';inp=self.dir/'batch-inputs.json' if isbatch else data
    if isbatch:write(inp,[str(data.resolve()),str(second.resolve())])
    profile_results={}
    for mode in ['optimized_cpu_same_structure','optimized_gpu']:
     folder=self.dir/'workers'/profile/mode;profile_results[mode]=worker(mode,inp,folder/'result.parquet',self.snapshot/'policy.json',folder,iterations=1,root=self.snapshot/'source',batch=isbatch)
    names=['batch-0.parquet','batch-1.parquet'] if isbatch else ['result.parquet'];checks=[compare(self.dir/'workers'/profile/'optimized_cpu_same_structure'/name,self.dir/'workers'/profile/'optimized_gpu'/name) for name in names]
    if not all(x['pass'] for x in checks):raise RuntimeError('Deployment profile parity failed')
    write(self.dir/(profile+'-measurements.json'),{'results':profile_results,'parity':checks})
    self.s['deployment'][profile]=deployment(profile_results['optimized_cpu_same_structure'],profile_results['optimized_gpu'],{'rows':[n,n] if isbatch else [n],'distinct_inputs':2 if isbatch else 1,'input_sha256':[x['sha256'] for x in inputs[:2 if isbatch else 1]]});self.save()
   # Finalizing remains active until every required step succeeds.
   self.s['status']='FINALIZING';self.event('profile','正在独立 profiler 与最终哈希核验；尚未提交终态')
   pf=self.dir/'workers/profile';worker('original_cudf_pandas',data,pf/'profile-output.parquet',self.snapshot/'policy.json',pf,iterations=1,profile=True,root=self.snapshot/'source')
   if environment['packages']!=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines():raise RuntimeError('Runtime packages changed during validation')
   self.s.update(validation_status='PASS',protected_unchanged=True,elapsed_seconds=time.monotonic()-start)
   self.s['validation_record_sha256']=seal(self.dir,self.s,self.snapshot)
   self.pending='COMPLETED';self.event('decision','结果一致；部署推荐按所选模式实测，预热收益单独展示','publish-validated-workflow')
 def finalize(self):
  self.s.update(status=self.pending,finished=now(),finalized=True)
  self.s['artifact_files']=[str(p.relative_to(self.dir)) for p in self.dir.rglob('*') if p.is_file() and p.suffix in ['.json','.log']]
  self.save()
def export_run(id,approved=False,profile='one_shot'):
 d=STATE/'runs'/id
 return export_archive(d,read(d/'run.json'),profile,approved)
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--scenario',choices=SCENARIOS,default='standard');p.add_argument('--run-id');p.add_argument('--execution-profile',choices=PROFILES,default='one_shot');p.add_argument('--planner',choices=['model','rule'],default='model');a=p.parse_args(argv);id=a.run_id or a.scenario+'-'+uuid.uuid4().hex[:10]
 if not re.fullmatch('[a-zA-Z0-9_-]+',id):raise SystemExit('Invalid run id')
 if (STATE/'runs'/id/'run.json').exists() and read(STATE/'runs'/id/'run.json').get('finalized'):raise SystemExit('Historical run is immutable; choose a new id')
 r=Run(id,a.scenario,a.execution_profile,a.planner)
 from .lifecycle import identity
 if os.getpgrp()!=os.getpid():os.setsid()
 controller=identity(os.getpid())
 if controller:write(r.dir/'controller.json',controller)
 try:r.run()
 except BaseException as e:r.s.update(error=str(e),validation_status='FAIL');r.event('error',str(e),kind='error');(r.dir/'error.log').write_text(traceback.format_exc());r.pending='FAILED'
 finally:r.finalize()
 print(json.dumps({'run_id':id,'status':r.s['status'],'path':str(r.dir)}));return 0 if r.s['status'] in ('COMPLETED','NEEDS_REVIEW') else 1
if __name__=='__main__':sys.exit(main())
