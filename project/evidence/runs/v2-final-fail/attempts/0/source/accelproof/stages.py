"""Distinct skill entry points. Export and revalidation never launch a model/GPU job."""
import argparse,json
from pathlib import Path
from .common import ROOT,STATE,read,sha

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='stage',required=True)
 intake=sub.add_parser('intake');intake.add_argument('--scenario',default='standard');intake.add_argument('--execution-profile',choices=['one_shot','persistent_batch'],required=True)
 migrate=sub.add_parser('migrate');migrate.add_argument('--scenario',default='standard');migrate.add_argument('--execution-profile',choices=['one_shot','persistent_batch'],required=True);migrate.add_argument('--run-id')
 validate=sub.add_parser('validate');validate.add_argument('--run-id',required=True)
 export=sub.add_parser('export');export.add_argument('--run-id',required=True);export.add_argument('--approved',action='store_true');export.add_argument('--execution-profile',choices=['one_shot','persistent_batch'],required=True)
 a=p.parse_args(argv)
 if a.stage=='intake':
  from .harness import SCENARIOS
  if a.scenario not in SCENARIOS:p.error('Unknown scenario')
  print(json.dumps({'scenario':a.scenario,'rows':SCENARIOS[a.scenario][0],'execution_profile':a.execution_profile,'contract_sha256':sha(ROOT/'specs/contract.yaml'),'gpu_called':False,'next':'migrate only after intake parameters are supplied'}));return
 if a.stage=='migrate':
  from .harness import main as run
  args=['--scenario',a.scenario,'--execution-profile',a.execution_profile]+(['--run-id',a.run_id] if a.run_id else []);raise SystemExit(run(args))
 if a.stage=='export':
  from .harness import export_run
  print(export_run(a.run_id,a.approved,a.execution_profile));return
 from .proof import verify_record
 from .validation import compare
 d=STATE/'runs'/a.run_id;s=read(d/'run.json');rec,target,meta=verify_record(d,s)
 baseline=d/'workers/timing/original_cpu/result.parquet';samples=list((d/'workers/timing').glob('*/sample-*.parquet'))
 results=[compare(baseline,q) for q in samples]
 if not results or not all(x['pass'] for x in results):raise ValueError('Saved sample validation failed')
 print(json.dumps({'candidate_id':meta['candidate_id'],'samples':len(results),'pass':True,'gpu_called':False,'model_called':False}))
if __name__=='__main__':main()
