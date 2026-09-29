"""Loopback-only recording aid: execute ONE configured trusted CPU workflow, never user code."""
import argparse,json,subprocess,threading,time
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
p=argparse.ArgumentParser();p.add_argument('--python',required=True);p.add_argument('--package',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=8769);a=p.parse_args()
state={'status':'READY'};lock=threading.Lock()
PAGE='''<!doctype html><meta charset="utf-8"><title>AccelProof · CPU-only 实际复用</title><style>body{font:20px/1.7 -apple-system,sans-serif;background:#f3f7f4;color:#19372b;margin:0;padding:70px 10%}h1{font-size:40px;margin-bottom:4px}small{color:#698074}button{background:#177649;color:white;border:0;padding:15px 25px;border-radius:8px;font-size:20px;margin:20px 0}section{background:white;border:1px solid #dce8df;padding:28px;border-radius:12px;margin-top:24px}pre{font:17px/1.6 monospace;white-space:pre-wrap;overflow-wrap:anywhere}b{color:#177649}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.v{font-size:34px;font-weight:600}label{font-size:16px;color:#698074}</style><small>ACCELPROOF / 实际执行 · 仅本地</small><h1>导出的 CPU 建议，真的在 CPU 上执行。</h1><p>全新 Python 环境 · 未安装 cuDF / 模型权重 · 另一随机种子的 1000 行输入</p><button id="run" onclick="start()">执行已审核工作流</button><span id="status">READY</span><section class="grid"><div><label>实际后端</label><div class="v" id="backend">—</div></div><div><label>GPU worker</label><div class="v" id="gpu">—</div></div><div><label>调用模型</label><div class="v" id="model">—</div></div></section><section><b>固定的真实命令与结果</b><pre id="out">点击后启动新进程。这里不播放预设输出。</pre></section><script>async function refresh(){const r=await(await fetch('/status')).json();document.getElementById('status').textContent=r.status;document.getElementById('run').disabled=r.status==='RUNNING';const x=r.result||{};document.getElementById('backend').textContent=x.selected_backend||'—';document.getElementById('gpu').textContent=x.gpu_worker_called===false?'未调用':'—';document.getElementById('model').textContent=x.model_called===false?'未调用':'—';document.getElementById('out').textContent=r.command?JSON.stringify({command:r.command,candidate_id:x.candidate_id,source_workflow_sha256:x.source_workflow_sha256,rows:x.rows,selected_backend:x.selected_backend,execution_profile:x.execution_profile,total_seconds:x.total_seconds,error:r.error},null,2):'点击后启动新进程。这里不播放预设输出。'}async function start(){await fetch('/run',{method:'POST'});refresh()}setInterval(refresh,400);refresh()</script>'''
def run():
 global state
 out=a.output/str(time.time_ns());cmd=[a.python,'-m','accelproof.workflow','run',str(a.archive.resolve()),'--input',str(a.input.resolve()),'--output',str(out.resolve())]
 state={'status':'RUNNING','command':cmd};result=subprocess.run(cmd,cwd=a.package,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if result.returncode:state.update(status='FAILED',error=result.stdout)
 else:state.update(status='COMPLETED',result=json.loads((out/'result.json').read_text()))
 out.mkdir(parents=True,exist_ok=True);(out/'command.log').write_text(result.stdout);(a.output/'latest.json').write_text(json.dumps(state,ensure_ascii=False,indent=2));lock.release()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  content=PAGE.encode() if self.path=='/' else json.dumps(state,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8' if self.path=='/' else 'application/json');self.end_headers();self.wfile.write(content)
 def do_POST(self):
  if self.path!='/run':self.send_error(404);return
  if not lock.acquire(False):self.send_error(409);return
  threading.Thread(target=run,daemon=True).start();self.send_response(202);self.end_headers()
 def log_message(self,*args):pass
a.output.mkdir(parents=True,exist_ok=True);ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
