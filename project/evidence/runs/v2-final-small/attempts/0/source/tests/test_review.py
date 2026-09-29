import unittest,tempfile,shutil,json,zipfile,stat,subprocess,sys,os,time
from pathlib import Path
from unittest.mock import patch
from accelproof.common import ROOT,read,write,sha
from accelproof.proof import snapshot,seal,export_archive,verify_record,checked_extract
from accelproof.profiles import select_backend
POLICY={'action':'migrate','preserve_null_keys':True,'ttft_policy':'exclude_missing','backend':'cpu','read_strategy':'projected','next_experiment':'one_shot'}
class BoundCandidate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'project';self.root.mkdir();self.run=self.base/'run';self.run.mkdir()
  for n in ['accelproof','specs','skills','vendor','web']:
   shutil.copytree(ROOT/n,self.root/n,ignore=shutil.ignore_patterns('__pycache__'))
  for n in ['WORKFLOW_README.md','requirements-cpu.txt','LICENSE']:shutil.copy2(ROOT/n,self.root/n)
  write(self.run/'candidate-policy.json',POLICY)
  self.target,meta=snapshot(self.run,0,POLICY,{'test_fixture':True},[],self.root)
  decision={'status':'MEASURED','recommended_backend':'cpu','scope':{'rows':[8]},'observations_per_backend':1}
  self.state={'id':'fixture','status':'COMPLETED','finalized':True,'validation_status':'PASS','candidate_id':meta['candidate_id'],'measurement':{},'deployment':{'one_shot':decision}}
  self.state['validation_record_sha256']=seal(self.run,self.state,self.target,self.root);write(self.run/'run.json',self.state)
 def tearDown(self):self.tmp.cleanup()
 def export(self):return export_archive(self.run,self.state,'one_shot',True,self.root)
 def test_original_exports_and_binds(self):
  z=self.export()
  with zipfile.ZipFile(z) as f:self.assertEqual(json.loads(f.read('manifest.json'))['candidate_id'],self.state['candidate_id'])
 def test_changed_policy_rejected(self):
  write(self.run/'candidate-policy.json',dict(POLICY,ttft_policy='fill_zero'))
  with self.assertRaisesRegex(ValueError,'policy changed'):self.export()
 def test_changed_template_rejected(self):
  (self.root/'accelproof/pipeline.py').write_text('# changed')
  with self.assertRaisesRegex(ValueError,'source changed'):self.export()
 def test_changed_contract_rejected(self):
  (self.root/'specs/contract.yaml').write_text('changed: true')
  with self.assertRaisesRegex(ValueError,'source changed'):self.export()
 def test_changed_judge_rejected(self):
  (self.root/'accelproof/validation.py').write_text('# relaxed')
  with self.assertRaisesRegex(ValueError,'source changed'):self.export()
 def test_snapshot_edit_rejected(self):
  write(self.target/'policy.json',dict(POLICY,ttft_policy='fill_zero'))
  with self.assertRaises(ValueError):self.export()
 def test_unfinalized_rejected(self):
  self.state['finalized']=False
  with self.assertRaises(ValueError):self.export()
 def test_finalizing_not_exportable(self):
  self.state['finalized']=False;self.state['status']='FINALIZING'
  with self.assertRaises(ValueError):self.export()
 def test_no_profile_measurement_rejected(self):
  with self.assertRaisesRegex(ValueError,'no validated'):export_archive(self.run,self.state,'persistent_batch',True,self.root)
 def test_requires_approval(self):
  with self.assertRaises(ValueError):export_archive(self.run,self.state,'one_shot',False,self.root)
 def test_deployment_edit_rejected(self):
  self.state['deployment']['one_shot']['recommended_backend']='gpu'
  with self.assertRaises(ValueError):self.export()
 def extract(self,z):
  d=self.base/('out'+str(time.time_ns()));d.mkdir();return checked_extract(z,d)
 def mutate_zip(self,name,data,symlink=False,listed=False):
  z=self.export();out=self.base/'bad.zip'
  with zipfile.ZipFile(z) as f:content={n:f.read(n) for n in f.namelist()}
  if listed:
   import hashlib
   m=json.loads(content['manifest.json']);m['files'][name]=hashlib.sha256(data).hexdigest();content['manifest.json']=json.dumps(m).encode()
  with zipfile.ZipFile(out,'w') as f:
   for n,b in content.items():f.writestr(n,b)
   if symlink:
    info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;f.writestr(info,data)
   else:f.writestr(name,data)
  return out
 def test_extra_file_rejected(self):
  with self.assertRaises(ValueError):self.extract(self.mutate_zip('sitecustomize.py',b'print(1)'))
 def test_extra_even_if_added_to_manifest_rejected(self):
  with self.assertRaises(ValueError):self.extract(self.mutate_zip('sitecustomize.py',b'print(1)',listed=True))
 def test_traversal_rejected(self):
  with self.assertRaises(ValueError):self.extract(self.mutate_zip('../escape',b'x'))
 def test_symlink_rejected(self):
  with self.assertRaises(ValueError):self.extract(self.mutate_zip('link',b'/tmp',symlink=True))
 def test_stale_directory_rejected(self):
  d=self.base/'stale';d.mkdir();(d/'old.py').write_text('pass')
  with self.assertRaises(ValueError):checked_extract(self.export(),d)
 def test_two_archives_fresh_extractions(self):
  z=self.export();self.extract(z);self.extract(z)
 def test_cpu_run_without_gpu_tools(self):
  from accelproof.data import generate
  from accelproof.workflow import execute
  data=self.base/'input.parquet';generate(data,8,991)
  original=subprocess.check_output
  def check(cmd,*a,**kw):
   if cmd[0]=='nvidia-smi':raise AssertionError('CPU path called GPU tool')
   return original(cmd,*a,**kw)
  with patch('subprocess.check_output',side_effect=check):r=execute(self.export(),[data],self.base/'results')
  self.assertEqual(r['selected_backend'],'cpu');self.assertFalse(r['gpu_worker_called']);self.assertEqual(r['metrics']['optimized_cpu_same_structure']['backend_imported'],'pandas')
 def test_scale_change_cannot_preserve_gpu_recommendation(self):
  m={'deployment':{'recommended_backend':'gpu','scope':{'rows':[5000000]}}};self.assertEqual(select_backend(m,[10])[0],'cpu')
 def test_export_skill_does_not_call_harness_run(self):
  from accelproof.stages import main
  with patch('accelproof.harness.export_run',return_value='ok') as ex,patch('accelproof.harness.main',side_effect=AssertionError('must not migrate')):
   main(['export','--run-id','fixture','--execution-profile','one_shot','--approved']);ex.assert_called_once()

class SkillMetadata(unittest.TestCase):
 def test_frontmatter_parses(self):
  import yaml
  for p in (ROOT/'skills').glob('*/SKILL.md'):
   data=yaml.safe_load(p.read_text().split('---',2)[1]);self.assertEqual(data['name'],p.parent.name);self.assertIsInstance(data['description'],str)

class Lifecycle(unittest.TestCase):
 def test_orphan_becomes_interrupted(self):
  from accelproof.lifecycle import reconcile
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);write(p/'run.json',{'status':'RUNNING'});self.assertEqual(reconcile(p)['status'],'RECOVERY_REQUIRED')
 def test_unverified_live_group_blocks(self):
  from accelproof.lifecycle import reconcile
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);write(p/'run.json',{'status':'RUNNING'});write(p/'controller.json',{'pid':12,'pgid':12})
   with patch('accelproof.lifecycle.same_process',return_value=False),patch('accelproof.lifecycle.group_alive',return_value=True):s=reconcile(p)
   self.assertEqual(s['status'],'RECOVERY_REQUIRED');self.assertTrue(s['scheduling_blocked'])
 def test_recover_exact_real_process_then_cancel(self):
  from accelproof.lifecycle import identity,reconcile,stop_group
  with tempfile.TemporaryDirectory() as t:
   job=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
   try:
    p=Path(t);write(p/'run.json',{'status':'FINALIZING'});write(p/'controller.json',identity(job.pid));s=reconcile(p);self.assertEqual(s['status'],'FINALIZING');stop_group(read(p/'controller.json'));job.wait(timeout=5);self.assertEqual(reconcile(p)['status'],'INTERRUPTED')
   finally:
    if job.poll() is None:job.kill();job.wait()
 def test_pid_identity_mismatch_not_signaled(self):
  from accelproof.lifecycle import stop_group
  with patch('accelproof.lifecycle.same_process',return_value=False),patch('os.killpg') as kill:
   with self.assertRaises(ValueError):stop_group({'pid':1,'pgid':1})
   kill.assert_not_called()
 def test_failed_finalizer_never_commits_success(self):
  from accelproof.harness import Run
  with tempfile.TemporaryDirectory() as t,patch('accelproof.harness.STATE',Path(t)):
   r=Run('finalizer','small');r.s['status']='FINALIZING';r.save();self.assertFalse(read(r.dir/'run.json')['finalized']);r.pending='FAILED';r.s['error']='profiler failed';r.finalize();s=read(r.dir/'run.json');self.assertEqual(s['status'],'FAILED');self.assertTrue(s['finalized'])
if __name__=='__main__':unittest.main()
