"""Evidence-driven v2 report and engineering essay. Requires ReportLab on macOS."""
import json,statistics,hashlib
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
R=Path(__file__).resolve().parents[1];D=R/'docs';D.mkdir(exist_ok=True);read=lambda p:json.loads(p.read_text())
runs={p.parent.name:read(p) for p in (R/'evidence/runs').glob('*/run.json')};large=runs['v2-final-large'];small=runs['v2-final-small'];repair=runs['v2-final-repair'];failed=runs['v2-final-fail'];rule=runs['v2-final-rule'];ev=read(R/'evidence/agent-eval/results.json');clean=read(R/'evidence/clean-cpu/result.json')
pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/STHeiti Light.ttc',subfontIndex=0));pdfmetrics.registerFont(TTFont('B','/System/Library/Fonts/STHeiti Medium.ttc',subfontIndex=0))
ink=colors.HexColor('#17372c');green=colors.HexColor('#197449');muted=colors.HexColor('#657b71');line=colors.HexColor('#dce7e1')
styles={k:ParagraphStyle(k,fontName='B' if k in ['h1','h2','cover'] else 'CN',fontSize=sz,leading=lead,textColor=green if k in ['tag','h2'] else muted if k=='small' else ink,spaceAfter=9,wordWrap='CJK',keepWithNext=k=='h2') for k,sz,lead in [('body',10.3,18),('small',8.2,13),('h1',24,32),('h2',13,21),('cover',38,49),('tag',9,15)]}
def p(s,k='body'):return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[k])
def table(rows,widths=None):
 md.append('| '+' | '.join(map(str,rows[0]))+' |\n| '+' | '.join(['---']*len(rows[0]))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows[1:])+'\n')
 t=Table([[p(v,'small') for v in row] for row in rows],colWidths=widths or [498/len(rows[0])]*len(rows[0]),repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf6f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,line),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));return t
md=[]
def text(s,k='body'):md.append(s+'\n');return p(s,k)
def footer(c,d):
 c.setStrokeColor(line);c.line(48,44,547,44);c.setFont('CN',8);c.setFillColor(muted);c.drawString(48,29,'ACCELPROOF / v2.0 · RTX 4090 实测 · 本地评审版');c.drawRightString(547,29,str(d.page))
def build(path,story):SimpleDocTemplate(str(path),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=44,bottomMargin=60,title=path.stem,author='AccelProof 项目组').build(story,onFirstPage=footer,onLaterPages=footer)
def screenshot(name,width=498):
 from PIL import Image as PIL
 f=R/'media/source/screenshots'/name;im=PIL.open(f);return Image(str(f),width=width,height=width*im.height/im.width)
def flow():
 d=Drawing(498,218);labels=[('1 / INTAKE','契约 · 规模 · 运行模式'),('2 / PLAN','模型 + 按阶段 Skills'),('3 / SNAPSHOT','策略 · 模板 · 判卷身份'),('4 / VALIDATE','隔离执行 · 独立比较'),('5 / MEASURE','暖态与部署模式分开'),('6 / DELIVER','绑定 ZIP · 遵从后端')]
 for i,(a,b) in enumerate(labels):
  col=i%3;row=i//3;x=col*168;y=138-row*100;d.add(Rect(x,y,156,70,rx=7,ry=7,fillColor=colors.HexColor('#edf6f0'),strokeColor=line));d.add(String(x+12,y+45,a,fontName='B',fontSize=11,fillColor=green));d.add(String(x+12,y+21,b,fontName='CN',fontSize=9,fillColor=ink))
  if col<2:d.add(Line(x+157,y+35,x+165,y+35,strokeColor=green))
 d.add(String(0,5,'失败和无收益保留；模型不能修改契约、容差或验证程序。',fontName='CN',fontSize=10,fillColor=muted));return d
def bars():
 d=Drawing(498,170);data=large['bench'];maximum=max(x['median_seconds'] for x in data.values());labels={'original_cpu':'原始 pandas','original_cudf_pandas':'原始 cudf.pandas','optimized_cpu_same_structure':'同构优化 pandas','optimized_gpu':'同构优化 cuDF'}
 for i,(name,label) in enumerate(labels.items()):
  y=135-i*36;v=data[name]['median_seconds'];d.add(String(0,y+6,label,fontName='CN',fontSize=9,fillColor=ink));d.add(Rect(130,y,290*v/maximum,18,fillColor=green if name=='optimized_gpu' else colors.HexColor('#adc4b5'),strokeColor=None));d.add(String(428,y+5,f'{v:.4f}s',fontName='CN',fontSize=9,fillColor=ink))
 return d
story=[]
def page(title):story.extend([PageBreak(),p('ACCELPROOF / VERIFIED WORKFLOW','tag'),text(title,'h1')])
oneshot=large['deployment']['one_shot'];batch=large['deployment']['persistent_batch'];cid=large['candidate_id']
story=[Spacer(1,35),p('AGENT SKILLS / REVIEW REVISION 2','tag'),p('验速工坊\nAccelProof','cover'),p('把已验证的结果，交付为同一份工作流。','h1'),p('RTX 4090 · 500 万行合成推理日志\n固定审计模板 / 本地模型 / 独立验收','body'),Spacer(1,20),table([[f"{large['speedup']:.2f}×",oneshot['recommended_backend'].upper(),'PASS'],['预热后同构 CPU / GPU','一次性模式实际推荐','第二数据 CPU 复用']]),Spacer(1,24),p(f"一次新进程 CPU {oneshot['cpu_total_seconds']:.2f}s / GPU {oneshot['gpu_total_seconds']:.2f}s。暖态收益不自动意味着应选 GPU。",'body'),p('2026 年 9 月 28 日 · v2.0\n本地评审材料；公开网址与赛事提交尚未完成。','small')]
md=['# AccelProof v2 项目报告\n',f"500 万行预热后同构加速比 {large['speedup']:.4f}；one_shot 推荐 {oneshot['recommended_backend']}。\n"]
page('01 / 从数据到可复用工作流')
story+=[text('项目面向固定结构的推理请求日志。模型选择受审计的 Parquet 读取策略及部署模式实验顺序，控制器冻结候选，独立验证器检查统计语义，再依据实际执行模式决定后端。定位是受限决策与验收工作台。'),flow(),table([['对象','执行责任'],['本地 Qwen3-VL-8B','纯文本、六字段 JSON；选择 full / projected 读取与下一项实验'],['四个业务 Skills','intake、migrate、validate、export 各有独立命令'],['验证与交付控制器','决定是否通过、选择实际后端、阻止不匹配的导出']]),text('模型不会生成自由 Python，不能改写判卷规则。官方 NVIDIA cuDF Skill 与业务 Skills 共同作为上下文；迁移和修复按阶段加载不同业务技能，不宣称实现全网动态发现。')]
page('02 / 一个空值足以改变结论')
story+=[text('同一组的两个成功请求，TTFT 为 [10, null]。契约只统计成功且非空的值，正确均值为 10；填零会变成 5。故障场景主动注入 fill_zero，并清楚记录它不是自然发生的模型失误。'),table([['输入','正确处理','错误处理'],['10, null','排除缺失 → (10 / 1) = 10','填零 → (10 + 0) / 2 = 5'],['故障候选','14/18，停止测速与有效导出','原始失败结果保留'],['修复候选',f"{repair['parity']['passed']}/{repair['parity']['total']}，模型修复 {repair['repairs']} 轮",'新的 attempt 与候选摘要']]),screenshot('failure-detail-report.png'),text('九个手算样例检查空表、空键、分钟边界、缺失 TTFT、全失败组及大整数。之后比较全量聚合表和每个测量样本；整数精确比较，空值掩码独立核验，浮点容差固定。','small')]
page('03 / 验证与 ZIP 必须属于同一候选')
story+=[text('v1 的导出只核对源码，未绑定验证时使用的策略。Review 复现了“通过后把 exclude_missing 改为 fill_zero，仍可导出”的问题。v2 在验证前复制不可变候选目录，保存策略、模板、测试、契约、输入和环境摘要，执行快照中的代码。'),screenshot('policy-repair-report.png'),text('控制器独占创建 validation-record.json。导出核对该记录摘要、候选身份、所有已验证产物和当前保护文件，再从快照打包。普通误编辑会被拒绝；这不等价于抵抗有权重写整个证据目录的所有者。'),table([['回归操作','结果'],['验证后修改策略 / 模板 / 契约 / 判卷规则','拒绝有效导出'],['添加未列出的文件、导入阴影、越界路径或符号链接','拒绝解包'],['连续复用不同 ZIP','每次使用新的临时目录，无旧代码污染']])]
page('04 / 暖态性能不是部署推荐')
story+=[text(f"新版 {large['rows']:,} 行运行的同构 CPU/GPU 暖态比值为 {large['speedup']:.3f}×。原始 pandas 与最终 GPU 的整体比值为 {large['overall_speedup']:.3f}×，后者包含聚合重写收益，不能全部归因于 GPU。"),bars(),text('每个配置先预热一次，再测三次；包括 Parquet 读取、聚合、写出和 GPU 同步。顺序固定，未随机化，未清除文件缓存。全部样本及全量一致性证据保存。'),table([['实际运行模式','CPU 总墙钟','GPU 总墙钟','建议'],['一次新进程',f"{oneshot['cpu_total_seconds']:.3f}s",f"{oneshot['gpu_total_seconds']:.3f}s",oneshot['recommended_backend'].upper()],['同进程处理两个不同输入',f"{batch['cpu_total_seconds']:.3f}s",f"{batch['gpu_total_seconds']:.3f}s",batch['recommended_backend'].upper()]]),text('部署模式各测一次，包含初始化。两份常驻批次输入使用不同种子，所有任务 PID 相同；总批次时间不等于预热后单任务样本。没有据两个不同口径的数字推算确定的盈亏平衡次数。')]
page('05 / 建议怎样落到实际命令')
story+=[text('日常 run 读取 manifest 的 execution_profile 与 recommended_backend。CPU 分支不导入 cuDF、不调用 nvidia-smi，也不申请 GPU 锁。需要 CPU/GPU 双路复核时必须显式使用 verify。'),screenshot('execution-profile.png'),table([['动作','实测或门禁'],['干净 CPU 环境 run',f"selected_backend={clean['selected_backend']}；GPU worker={clean['gpu_worker_called']}；model_called={clean['model_called']}"],['新规模或批次数超出范围','标记未测量，保守回退 CPU'],['未测量的执行模式','不可导出有效工作流'],['当前大数据候选摘要',cid[:40]+'…']]),text('python -m accelproof.workflow run WORKFLOW.zip --input INPUT.parquet --output RESULT_DIR','small')]
page('06 / Skills 消融与固定规则基线')
labels={'none':'无 Skills','official':'仅官方','custom':'仅业务','all':'官方 + 业务','rule':'固定规则'}
rows=[['条件','通过','错误采用','输入 / 输出 tokens','规划秒 / 工具数']]
for k in ['none','official','custom','all','rule']:
 s=ev['summary'][k];rows.append([labels[k],f"{s['passed']}/{s['total']}",s['wrong_adoptions'],f"{s['input_tokens']} / {s['output_tokens']}",f"{s['planning_seconds']:.2f} / {s['tool_calls']}"])
story+=[table(rows,[100,55,65,100,178]),text('12 个冻结任务、四种模型上下文加固定规则基线。新措辞覆盖列投影、全列审计、不同分组分布、空值修复、缺失模式与负向请求；期望输出不发送给模型。所有模型条件使用相同模型、生成预算和评分器。'),text(f"本轮无技能 {ev['summary']['none']['passed']}/12，仅官方 {ev['summary']['official']['passed']}/12，业务技能 {ev['summary']['custom']['passed']}/12，组合 {ev['summary']['all']['passed']}/12，固定规则 {ev['summary']['rule']['passed']}/12。上下文更多并不自动带来更高得分，所有负向与接近的结果保留。"),text('这些是规划策略评测：工具调用数为零，不可写成 GPU 端到端成功率。模型有真实但有限的选择空间：full / projected 改变实际 Parquet 读取集合，next_experiment 改变控制器测量顺序；统计契约始终固定。'),table([['实际小数据端到端控制器','完成秒数','结果'],['模型 + 阶段 Skills',f"{small['elapsed_seconds']:.2f}",small['validation_status']],['固定规则',f"{rule['elapsed_seconds']:.2f}",rule['validation_status']]]),text('端到端各运行一次，均启动 13 个隔离 worker；模型方案另有 1 次推理，规则为 0 次。包含全部验证和两模式测量，不是等预算的优化能力比较。固定规则若更快或评分相近，结果照实保留；当前证据不足以证明模型优于确定规则。')]
page('07 / 收尾、恢复与干净环境')
story+=[table([['运行边界','v2 实现与验证'],['FINALIZING','profiler、哈希和制品收尾后才一次性写入 finished 与终态；延迟/失败 SSE 测试通过'],['API 重启','使用 PID、启动时间、命令、进程组、boot ID 恢复身份；身份不明则阻止新调度'],['浏览历史','活动任务独立保留，场景选择禁用，取消始终指向活动 run_id'],['历史展示','按 run_id / attempt 读取冻结策略与模板，不读取当前源码冒充历史'],['精简工作流','独立 README、许可、CPU 安装入口、HTTPS+哈希 Linux wheel 清单']]),text('干净目录按导出包 README 新建 Python 3.12 CPU 环境，禁用 pip 缓存，从依赖源安装；检查 help、模块导入、实际 CPU run，并将 nvidia-smi 替换为失败哨兵。该测试不包含原模型权重、cuDF 或旧节点虚拟环境。'),text('GPU 与模型实验在原 4090 的专用运行库完成，不冒称全新 GPU 环境安装验证。原节点 tmpfs 恢复脚本被明确标为节点专用；GPU/模型安装说明与 CPU 日常复用分开。'),text('隔离仍限于受信任固定模板：网络命名空间、Landlock、资源限制和超时。CUDA 需要读取设备与 /proc，并写本进程线程名称；不宣称任意恶意代码沙箱。')]
page('08 / 交付范围与验收映射')
story+=[table([['Review 项','落地证据'],['R01 / R12','候选绑定、精确归档集合、临时解包、篡改回归'],['R02 / R03 / R04','遵从后端、两种实际执行模式、CPU 干净环境'],['R05 / R06 / R07 / R08','终态提交、进程身份恢复、活动任务、历史 attempt'],['R09','四个不同 CLI；导出 Skill 不生成新任务'],['R10 / R11','受限读取与实验选择；五条件消融；保留固定规则基线']]),text('本地交付包括项目源码、可复现证据、项目报告、工程征文、五分钟以内视频、离线交互预览及按执行模式导出的工作流。没有公开网址、主办方接收回执或已投稿声明。'),text('项目版本：v2.0 / 2026-09-28。核心结果来自本版冻结候选；v1 材料单独保留作历史，不能用旧通过状态替代本版验收。'),text('归属与工具说明','h2'),text('产品原型和初版规划沿用 AccelProof 方案；本轮根据外部 Review 修订。实现、排版和验证使用 Codex 辅助。NVIDIA Skill 固定提交 d8519c57da6db5d9bea274ec1724a4a7a56a3dee，原始许可证与签名文件保留；未宣称密码学签名验证或官方认证。'),text('参考：NVIDIA/skills（固定提交）、Agent Skills specification、RAPIDS/cuDF 官方文档。全部硬件实验为 RTX 4090，不是 DGX Spark 实测。','small')]
build(D/'AccelProof-v2-项目报告.pdf',story);(D/'AccelProof-v2-项目报告.md').write_text('\n'.join(md))
article=[];amd=['# 当十多倍加速仍然不该选 GPU\n']
def ap(s,k='body'):amd.append(s+'\n');article.append(p(s,k))
ap('当十多倍加速\n仍然不该选 GPU','h1');ap('AccelProof 验速工坊 · 三次工程取舍','tag')
ap('第一次转折：能运行，不等于算对','h2');ap('日志迁移最容易出现的错误，往往不是崩溃，而是一张看起来正常的统计表。两个成功请求的首字延迟，一个是 10，一个缺失。把缺失值填成零后，代码能跑、类型正确，均值却从 10 变成了 5。GPU 只会更快地把这个错误重复一遍。')
ap('因此，我们把统计口径先写进契约：空分组键要保留，成功状态只认 ok，首字延迟只统计成功且非空的值。模型不能改动契约，也不能放宽容差。它只能在受审计策略里选择，独立程序决定候选是否合格。故障演示是主动注入，并不伪装成模型现场出错。')
article.append(screenshot('failure-detail-report.png'));ap('错误检查首先展示字段、参考值、候选值和原因，再提供原始 JSON。修复不是覆盖文件后说“好了”：旧 attempt、14/18 的失败检查、新策略和复验结果都有各自的身份。','small')
article.append(PageBreak());ap('第二次转折：漂亮的比值不是运行建议','h1')
ap(f"新版 500 万行记录的预热后同构 CPU/GPU 比值为 {large['speedup']:.2f}×。如果只看这个指标，把默认后端切到 GPU 似乎顺理成章。但实际日常复用会启动新进程，初始化成本也由这一次任务承担。新进程对照中，CPU 花了 {oneshot['cpu_total_seconds']:.2f} 秒，GPU 花了 {oneshot['gpu_total_seconds']:.2f} 秒。")
article.append(bars());ap('我们把结果一致性、性能测量和部署建议拆开。暖态样本回答的是“后端已经准备好时一次计算多快”；one_shot 回答“只做一次任务要等多久”；persistent_batch 则让同一进程处理两份不同输入，并计入初始化和整个批次。三个问题不能共用一个绿色成功标签。')
ap(f"本次 persistent_batch 的推荐为 {batch['recommended_backend'].upper()}。我们没有为了让 GPU 获胜增加一个未经测量的“将来可摊薄”承诺，也没有从两组口径不同的数字推算神奇的盈亏平衡次数。每个部署模式只有一次观测，因此结论只适用于所测输入和节点。")
ap('后端建议还必须变成程序行为。v1 的复用脚本一面写 KEEP_CPU，一面无条件运行 GPU，这个矛盾在 Review 中暴露出来。v2 的日常 run 读取已审核 manifest，CPU 路径根本不调用 GPU 工具；显式 verify 才进行 CPU/GPU 双路复核。')
article.append(PageBreak());ap('第三次转折：验证过的文件还会变化','h1')
ap('另一个问题更隐蔽：通过验证后，编辑候选策略，再导出。旧版会给新的错误策略附上旧的通过结论。ZIP 内部逐文件哈希即使全部正确，也只能证明“文件彼此符合这个清单”，不能证明这些文件就是当初验过的那一组。')
ap('修复的关键不是再算一次当前哈希，而是把时间关系保存下来。验证前冻结策略、模板、判卷规则、输入和环境；从快照执行；完成后让控制器绑定结果与候选摘要；导出只能取这一份快照。验证后误改策略、契约、模板或判卷规则，都会要求重新验证。每次复用还要在新的临时目录解包，精确核对成员集合，避免上一次遗留代码影响导入。')
article.append(screenshot('policy-repair-report.png'));ap('这套机制防止意外漂移，不声称抵抗能重写整个证据目录的所有者。内容一致性与来源认证是两回事。','small')
ap('最后，我们也给 Agent 本身留了一条对照：固定规则。五种条件的评测把官方技能和业务技能分开，记录错误采用、token 与耗时；真正的端到端运行另行记账。当前有限策略空间里，模型未必比规则更划算。验速工坊的价值，首先是把这个事实和所有失败结果一起交付，而不是让每一轮实验都显得成功。')
ap('工具与归属：项目修订参考外部 Review，开发与材料制作使用 Codex 辅助；实验记录来自 RTX 4090。本篇属于本地评审材料，尚无公开发表或赛事接收声明。','small')
build(D/'AccelProof-v2-参赛征文.pdf',article);(D/'AccelProof-v2-参赛征文.md').write_text('\n'.join(amd));print('Rendered report and engineering essay from v2 evidence')
