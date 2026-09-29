"""Create a separate submission copy for a narration-only revision."""
from pathlib import Path
import argparse,json,hashlib,shutil,zipfile
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--voice',type=Path,required=True);a=p.parse_args();base=a.base.resolve();out=a.output.resolve();voice=a.voice.resolve();rendered=voice/'rendered'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not out.exists();shutil.copytree(base,out)
media=out/'project/media'
# Remove stale derived media only from this newly created copy; the original v2 stays intact.
for name in ['AccelProof-Demo.mp4','Demo字幕.srt','Demo解说稿.md','video-build.json','video-probe.json','video-decode.log','video-qa.json','audio-levels.log','qa']:
 p=media/name
 if p.is_dir():shutil.rmtree(p)
 elif p.exists():p.unlink()
for p in rendered.iterdir():
 if p.is_dir():shutil.copytree(p,media/p.name)
 else:shutil.copy2(p,media/p.name)
oldn=media/'source/narration';shutil.rmtree(oldn);shutil.copytree(voice/'narration',oldn)
for n,d in [('render.py','render_neural.py'),('synthesize.py','synthesize_neural.py'),('prepare.py','prepare_neural.py'),('qa_video.py','qa_neural.py')]:shutil.copy2(voice/n,media/'source'/d)
(media/'source/requirements-neural.txt').write_text('edge-tts==7.2.8\nimageio-ffmpeg==0.6.0\nnumpy==2.5.3\n')
(out/'project/scripts/build_video.py').write_text('''"""Entry point for the v2.1 neural narration video; see media/source/requirements-neural.txt."""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[1]
if '--source' not in sys.argv:sys.argv.extend(['--source',str(root/'media/source/screenshots')])
if '--out' not in sys.argv:sys.argv.extend(['--out',str(root/'media')])
runpy.run_path(str(root/'media/source/render_neural.py'),run_name='__main__')
''')
# The old full-package assembler is explicitly kept as historical material, not the active entry.
q=out/'project/scripts/package_delivery.py'
if q.exists():q.rename(q.with_name('package_delivery_v2_legacy.py'))
shutil.copy2(Path(__file__),out/'project/scripts/package_voice_revision.py')
(out/'AccelProof-v2-Demo.mp4').unlink();shutil.copy2(rendered/'AccelProof-Demo-自然配音版.mp4',out/'AccelProof-v2.1-Demo-自然配音版.mp4')
for n in ['Demo字幕.srt','Demo解说稿.md','AccelProof-自然配音.mp3']:shutil.copy2(rendered/n,out/n)
meta=json.loads((rendered/'video-build.json').read_text());dur=meta['duration_seconds']
notes=f'''# AccelProof v2.1 配音修改说明

本次只调整视频配音、稿件、字幕与讲解停留时间，技术实现、实验结果、候选快照、工作流 ZIP、报告和征文保持 v2 内容。原 v2 提交包保留，未公开发布或提交赛事。

- 换用中文神经男声 `zh-CN-YunxiNeural`，语速 -2%，正常音高。属于 AI 合成，不是真人录音，也未模仿任何特定人物。
- 稿件改成演示讲解口吻，减少长句和密集术语，保留 10 与 5、13.26 倍、1.87 秒、18.83 秒及评测边界。
- 字幕按语音服务返回的实际单词时间戳生成，共 62 条；不再按字数均摊时间。
- 关键对照画面适当暂停，让错误项和当前运行模式与配音对应。原操作保持原速，画面保留暂停和 AI 配音标识。
- 成片 {dur:.2f} 秒，1920×1080 / 25 fps，AAC 48 kHz；提供独立 MP3、SRT、解说稿和生成脚本。
- 已检查完整解码、字幕时间、音量、静音间隔与代表画面。未声称完成真人听审；自然度仍可按试听反馈微调。

## 本地重建

在 project/ 下，新建独立环境并安装 `media/source/requirements-neural.txt`。直接使用已生成的声音，不需要联网：

```sh
python scripts/build_video.py
```

如需重新合成，执行 `python media/source/synthesize_neural.py --force`。该命令仅将解说文字发送到 Microsoft Edge 在线语音服务，不上传录像、项目代码或实验数据。macOS 使用系统 PingFang SC；Linux 需有 Noto Sans CJK SC 字体。

`media/video-build.json` 记录声音设置、每段字幕与镜头时间、原素材 SHA-256；`media/verification.json` 和音量日志记录检查结果。原始语音时间戳在 `media/source/narration/*.words.json`。

服务与工具文档：[edge-tts 项目](https://github.com/rany2/edge-tts)、[Microsoft 语音列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)。
'''
(out/'配音修改说明.md').write_text(notes)
f=out/'提交说明.md';s=f.read_text().replace('# AccelProof v2 本地提交材料','# AccelProof v2.1 自然配音版提交材料').replace('AccelProof-v2-Demo.mp4，194.502 秒',f'AccelProof-v2.1-Demo-自然配音版.mp4，{dur:.2f} 秒').replace('AccelProof-v2-提交包核验.json','AccelProof-v2.1-提交包核验.json');s+='\n本次配音修改详见 配音修改说明.md；实验与工作流保持 v2 验证版本。\n';f.write_text(s)
f=out/'交付核验.json';x=json.loads(f.read_text());x.update(version='v2.1 narration only',video_seconds=dur,neural_narration=True,core_results_inherited_from_unchanged_v2=True,core_tests_rerun_for_voice_revision=False);f.write_text(json.dumps(x,ensure_ascii=False,indent=2))
# All 92 protected source files and every recorded workflow remain exactly unchanged.
snap=json.loads((out/'project/evidence/runs/v2-final-large/attempts/0/snapshot.json').read_text())
for n,h in snap['protected_files'].items():assert sha(out/'project'/n)==h,n
for pattern in ['*.pdf','*工作流.zip']:
 for p in base.glob(pattern):assert sha(p)==sha(out/p.name),p.name
for p in (base/'project/evidence/runs').rglob('*'):
 if p.is_file():assert sha(p)==sha(out/'project/evidence/runs'/p.relative_to(base/'project/evidence/runs'))
files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.relative_to(out)!=Path('SHA256SUMS.json')}
(out/'SHA256SUMS.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
zpath=out.parent/'AccelProof-v2.1-自然配音版提交包.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(out.rglob('*')):
  if p.is_file():z.write(p,str(Path(out.name)/p.relative_to(out)))
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None;expected={out.name+'/'+n for n in files}|{out.name+'/SHA256SUMS.json'};assert len(z.namelist())==len(expected) and set(z.namelist())==expected
 for n,h in files.items():assert hashlib.sha256(z.read(out.name+'/'+n)).hexdigest()==h
result={'archive':zpath.name,'archive_sha256':sha(zpath),'archive_bytes':zpath.stat().st_size,'files':len(files),'zip_crc_pass':True,'exact_member_set':True,'all_hashes_match':True,'protected_source_files_unchanged':92,'reports_and_evidence_unchanged':True,'video_sha256':sha(out/'AccelProof-v2.1-Demo-自然配音版.mp4'),'duration_seconds':dur,'public_published':False}
(out.parent/'AccelProof-v2.1-提交包核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
