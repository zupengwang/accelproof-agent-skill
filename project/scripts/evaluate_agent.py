import fcntl,os,subprocess,sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from accelproof.common import ROOT,read,write,sha
from accelproof.harness import MODEL_PATH,MODEL_PYTHON,LOCK
from accelproof.profiles import rule_plan
out=ROOT/'evidence/agent-eval';out.mkdir(parents=True,exist_ok=True);spec=read(ROOT/'specs/agent-evals-v2.json');conditions=['none','official','custom','all']
requests=[dict(id=t['id'],prompt=t['prompt'],condition=c) for t in spec['tasks'] for c in conditions];write(out/'requests.json',requests);write(out/'frozen.json',{'spec_sha256':sha(ROOT/'specs/agent-evals-v2.json'),'protocol':spec['protocol'],'conditions':conditions+['rule']})
with LOCK.open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
 start=time.monotonic();subprocess.run([MODEL_PYTHON,str(ROOT/'accelproof/model.py'),'--model',MODEL_PATH,'--requests',str(out/'requests.json'),'--output',str(out/'raw.json')],check=True,env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='4'));wall=time.monotonic()-start
records=read(out/'raw.json')
for t in spec['tasks']:
 start=time.perf_counter();plan=rule_plan(t['prompt']);records.append(dict(id=t['id'],condition='rule',plan=plan,schema_valid=True,input_tokens=0,output_tokens=0,latency_seconds=time.perf_counter()-start))
expected={t['id']:t['expected'] for t in spec['tasks']}
for r in records:
 r['pass']=r['schema_valid'] and all(r['plan'].get(k)==v for k,v in expected[r['id']].items());r['wrong_adoption']=bool(r['plan'] and r['plan'].get('action')=='migrate' and expected[r['id']].get('action') in ['refuse','clarify','none']);r['tool_calls']=0
summary={c:{'passed':sum(x['pass'] for x in records if x['condition']==c),'total':sum(x['condition']==c for x in records),'wrong_adoptions':sum(x['wrong_adoption'] for x in records if x['condition']==c),'input_tokens':sum(x['input_tokens'] for x in records if x['condition']==c),'output_tokens':sum(x['output_tokens'] for x in records if x['condition']==c),'planning_seconds':sum(x['latency_seconds'] for x in records if x['condition']==c),'tool_calls':0} for c in conditions+['rule']}
write(out/'results.json',{'protocol':spec['protocol'],'summary':summary,'records':records,'model_process_total_seconds':wall,'scope':'planning-only; tools are not invoked in these tasks. Real executed workflows have separate controller elapsed times; no equal-budget optimization claim.'});print(json.dumps(summary,indent=2))
