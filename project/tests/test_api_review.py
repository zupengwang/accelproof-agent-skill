import unittest,tempfile,subprocess,sys,threading,time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from accelproof.common import write,read
from accelproof.lifecycle import identity
import accelproof.server as server
class APIReview(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.patch=patch.object(server,'STATE',self.root);self.patch.start();server.jobs.clear();self.job=None
 def tearDown(self):
  if self.job and self.job.poll() is None:self.job.kill();self.job.wait()
  self.patch.stop();self.temp.cleanup()
 def record(self,status='RUNNING',real=False):
  p=self.root/'runs'/'review';p.mkdir(parents=True);write(p/'run.json',{'id':'review','status':status,'finalized':False,'events':[]})
  if real:
   self.job=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True);write(p/'controller.json',identity(self.job.pid))
  return p
 def test_startup_orphan_not_infinite_running(self):
  self.record()
  with TestClient(server.app) as c:self.assertEqual(c.get('/api/runs/review').json()['status'],'RECOVERY_REQUIRED')
 def test_api_restart_can_cancel_persisted_identity(self):
  self.record(real=True)
  with TestClient(server.app) as c:
   self.assertEqual(c.get('/api/runs/review').json()['status'],'RUNNING');self.assertEqual(c.post('/api/runs/review/cancel').status_code,200)
  self.job.wait(timeout=5);self.assertIsNotNone(self.job.returncode)
 def test_sse_waits_for_finalizer_and_delivers_failure(self):
  p=self.record('FINALIZING',True)
  def finish():
   time.sleep(.8);write(p/'run.json',{'id':'review','status':'FAILED','finalized':True,'finished':'test','error':'profiler failed','events':[{'sequence':1,'run_id':'review','stage':'error','message':'profiler failed'}]})
  with TestClient(server.app) as c:
   t=time.monotonic();threading.Thread(target=finish).start();s=c.get('/api/runs/review/events').text
   self.assertGreaterEqual(time.monotonic()-t,.8);self.assertIn('profiler failed',s);self.assertIn('event: done',s);self.assertIn('FAILED',s)
 def test_finalizing_export_stays_blocked(self):
  self.record('FINALIZING',True)
  with TestClient(server.app) as c,patch('accelproof.harness.STATE',self.root):self.assertEqual(c.post('/api/runs/review/approval',json={'approved':True}).status_code,409)
if __name__=='__main__':unittest.main()
