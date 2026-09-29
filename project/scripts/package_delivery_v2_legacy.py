"""Assemble and verify a private local delivery without publishing."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();src=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(src,out/'project',ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store','state'))
for name in ['AccelProof-v2-项目报告.pdf','AccelProof-v2-项目报告.md','AccelProof-v2-参赛征文.pdf','AccelProof-v2-参赛征文.md','Review响应与验收.md']:shutil.copy2(src/'docs'/name,out/name)
for name in ['Demo字幕.srt','Demo解说稿.md']:shutil.copy2(src/'media'/name,out/name)
shutil.copy2(src/'media/AccelProof-Demo.mp4',out/'AccelProof-v2-Demo.mp4');shutil.copy2(src/'preview/index.html',out/'AccelProof-v2-离线预览.html')
archives=[('v2-final-small','one_shot','小数据-CPU工作流.zip'),('v2-final-large','one_shot','500万行-one_shot-工作流.zip'),('v2-final-large','persistent_batch','500万行-persistent_batch-工作流.zip')]
for run,mode,dest in archives:shutil.copy2(src/'evidence/runs'/run/('workflow-'+mode+'.zip'),out/dest)
(out/'提交说明.md').write_text('''# AccelProof v2 本地提交材料

本版按外部 Review 修订，原 v1 包单独保留。本包尚未公开发布或提交赛事，三个提交网址仍待获得发布授权后生成。

| 表单要求 | 当前本地文件 | 外部网址状态 |
| --- | --- | --- |
| 项目及报告书 | project/ 源码及证据；AccelProof-v2-项目报告.pdf | 未发布 |
| 5 分钟内 Demo | AccelProof-v2-Demo.mp4，194.502 秒 | 未发布 |
| 参赛征文 | AccelProof-v2-参赛征文.pdf 与同名 Markdown | 未发布 |

先看 Review响应与验收.md 了解 R01–R12 的处理、测试与限制。AccelProof-v2-离线预览.html 可直接打开，回放最终五个运行、修复 attempt 和模式建议；不启动任务、不重新导出。

小数据-CPU工作流.zip 是干净 CPU 环境实际验证过的归档。解压到新目录，按其 README 安装 CPU 依赖，使用原 ZIP 作为 run 参数，输入可选 project/examples/requests-1000-20260930.parquet。两个 500 万行工作流也均遵从 CPU 推荐；显式 verify 才执行 GPU 交叉验证。只有受信任项目包可执行。

完整项目依赖与命令见 project/README.md、WORKFLOW_README.md。正式记录在 project/evidence/runs/v2-final-*。不包含模型权重、原节点环境、wheel 缓存或培训 PDF。绝对路径出现在真实记录中用于审计，不要求复现者拥有相同路径。

## 自检

在包目录执行：

```sh
python3 project/scripts/verify_delivery.py .
```

验证 SHA256SUMS.json 列出的文件。ZIP 本身的 CRC、文件集合、逐文件哈希及外层 ZIP 摘要在相邻的 AccelProof-v2-提交包核验.json 中。哈希证明内容一致性，不证明发布者身份。

当前边界：GPU/模型实验在原 RTX 4090 环境完成，CPU-only 环境为新建环境；不能混称全新 GPU 安装验收。固定规则在小数据真实流程更快，不能将策略题通过率宣传成通用自主优化能力。
''')
qa={'version':'v2.0','unit_tests_passed':42,'formal_runs':5,'expected_failure_preserved':True,'protected_files_per_candidate':92,'all_final_candidate_and_artifact_hashes_verified':True,'cpu_fresh_environment':True,'cpu_second_input_reference_parity':True,'gpu_explicit_second_input_verification':True,'persistent_batch_actual_reuse':True,'report_pages':9,'essay_pages':3,'video_seconds':194.502,'video_resolution':'1920x1080','video_full_decode_pass':True,'live_capture_scenes':5,'upstream_original_files_unchanged':34,'offline_preview_verified':True,'public_published':False,'competition_submitted':False,'gpu_fresh_environment_install_verified':False,'rules_baseline_retained':True}
(out/'交付核验.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()};(out/'SHA256SUMS.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
archive=out.parent/'AccelProof-v2-本地提交包.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(out.rglob('*')):
  if f.is_file():z.write(f,arcname=str(Path(out.name)/f.relative_to(out)))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None;expected={out.name+'/'+n for n in files}|{out.name+'/SHA256SUMS.json'};assert set(z.namelist())==expected and len(z.namelist())==len(expected)
 for n,h in files.items():assert hashlib.sha256(z.read(out.name+'/'+n)).hexdigest()==h,n
result={'archive':archive.name,'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_files':len(files),'zip_members':len(files)+1,'all_file_hashes_match':True,'exact_member_set':True,'zip_crc_pass':True,'public_published':False,'competition_submitted':False}
(out.parent/'AccelProof-v2-提交包核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
