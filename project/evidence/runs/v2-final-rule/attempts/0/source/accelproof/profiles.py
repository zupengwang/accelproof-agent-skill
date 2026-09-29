"""Mode-specific deployment decisions are separate from semantic and warm benchmarks."""
import statistics
PROFILES=('one_shot','persistent_batch')
def deployment(cpu,gpu,scope):
 c=cpu['process_wall_seconds'];g=gpu['process_wall_seconds']
 return {'status':'MEASURED','recommended_backend':'gpu' if g<=c*.9 else 'cpu','cpu_total_seconds':c,'gpu_total_seconds':g,'speedup':c/g,'scope':scope,'observations_per_backend':1,'claim':'one observed fresh process per backend; filesystem cache not flushed; no statistical generalization'}
def select_backend(manifest,rows):
 d=manifest['deployment'];scope=d['scope'];expected=scope['rows']
 # A schema match alone never extends a GPU recommendation to a new scale or batch count.
 if list(rows)!=expected:return 'cpu','UNMEASURED_INPUT_SCALE: conservative CPU fallback; benchmark this workload before using GPU'
 return d['recommended_backend'],'within measured row-count and batch-count envelope; performance is not guaranteed on a new distribution or machine'
def rule_plan(prompt):
 """Frozen no-model comparator, deliberately simple and reported separately."""
 p=prompt.lower();action='migrate'
 if any(x in p for x in ['ignore contract','change tolerance','export without validation','删除验证','降低精度']):action='refuse'
 elif any(x in p for x in ['contract unknown','missing contract','no execution mode','缺少契约']):action='clarify'
 elif any(x in p for x in ['weather','poem','写诗']):action='none'
 return dict(action=action,preserve_null_keys=True,ttft_policy='exclude_missing',backend='cpu',read_strategy='projected',next_experiment='persistent_batch' if 'persistent' in p else 'one_shot')
