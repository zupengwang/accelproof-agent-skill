"""Rebuild original AccelProof UI footage with neural narration and timed captions."""
import argparse,hashlib,json,math,re,subprocess,sys
from pathlib import Path
import imageio_ffmpeg
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
ROOT=Path(__file__).resolve().parent;src=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);build=ROOT/'build';build.mkdir(exist_ok=True);ff=imageio_ffmpeg.get_ffmpeg_exe()
scenes=json.loads((ROOT/'narration/scenes.json').read_text())
def probe(path):
 log=subprocess.run([ff,'-hide_banner','-i',str(path)],text=True,capture_output=True).stderr
 h,m,s=re.search(r'Duration: (\d+):(\d+):([\d.]+)',log).groups();return int(h)*3600+int(m)*60+float(s)
def stamp(t,ass=False):
 base=100 if ass else 1000;n=round(t*base);return f'{n//(3600*base):02}:{n//(60*base)%60:02}:{n//base%60:02}'+(f'.{n%100:02}' if ass else f',{n%1000:03}')
header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,PingFang SC,36,&H00FFFFFF,&H00FFFFFF,&H80302018,&H80302018,0,0,0,0,100,100,0,0,3,1.5,0,2,80,80,24,1
Style: Tag,PingFang SC,20,&H00FFFFFF,&H00FFFFFF,&H80302018,&H80302018,0,0,0,0,100,100,0,0,3,1.5,0,9,20,20,12,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
header=header.replace('PingFang SC', 'PingFang SC' if sys.platform=='darwin' else 'Noto Sans CJK SC')
# Retain real footage at original speed. Holds keep the relevant evidence onscreen during explanation.
edits={1:[(0,9,6.5),(9,24,0)],2:[(0,2.4,15.5),(2.4,9,0)]}
lead=.25;cursor=0;subs=[];timeline=[];records=[]
for i,s in enumerate(scenes):
 audio=ROOT/'narration'/s['audio'];picture=src/s['image'];live=picture.suffix=='.webm';duration=math.ceil((probe(audio)+lead+.65)*25)/25
 cues=json.loads(audio.with_suffix('.cues.json').read_text());ass=header
 label='真实操作录屏 · 讲解处暂停 / AI 配音' if live else '已保存的真实实验记录 / AI 配音'
 ass+=f'Dialogue: 0,0:00:00.00,{stamp(duration,True)},Tag,,0,0,0,,{label}\n'
 for c in cues:
  start=c['start']+lead;end=c['end']+lead;assert 0<=start<end<duration
  caption=c['text'].replace('{','').replace('}','')
  ass+=f'Dialogue: 0,{stamp(start,True)},{stamp(end,True)},Main,,0,0,0,,{caption}\n'
  subs.append(f'{len(subs)+1}\n{stamp(cursor+start)} --> {stamp(cursor+end)}\n{caption}\n')
  timeline.append(dict(scene=i+1,start=cursor+start,end=cursor+end,text=caption))
 af=build/f'{i:02}.ass';af.write_text(ass)
 inputargs=[] if live else ['-loop','1'];filters=[]
 if i in edits:
  clips=edits[i];filters.append(f'[0:v]split={len(clips)}'+''.join(f'[s{j}]' for j in range(len(clips))))
  for j,(start,end,hold) in enumerate(clips):filters.append(f'[s{j}]fps=25,trim=start={start}:end={end},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop={round(hold*25)},setpts=N/(25*TB)[c{j}]')
  filters.append(''.join(f'[c{j}]' for j in range(len(clips)))+f'concat=n={len(clips)}:v=1:a=0[edited]');base='[edited]'
 else:base='[0:v]'
 filters.append(base+f'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,tpad=stop_mode=clone:stop={math.ceil(duration*25)},setpts=N/(25*TB),ass={af}[v]')
 filters.append('[1:a]adelay=250:all=1,apad,loudnorm=I=-16:TP=-1.5:LRA=10[a]')
 cmd=[ff,'-hide_banner','-loglevel','error','-y']+inputargs+['-i',str(picture),'-i',str(audio),'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(duration),'-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(build/f'scene-{i:02}.mp4')]
 subprocess.run(cmd,check=True);print(i,s['title'],duration,flush=True)
 records.append({'scene':i+1,'title':s['title'],'start':cursor,'duration':duration,'footage':s['image'],'source_sha256':hashlib.sha256(picture.read_bytes()).hexdigest(),'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'edits':edits.get(i),'voice':s['voice'],'rate':s['rate']});cursor+=duration
assert cursor<300
(build/'concat.txt').write_text('\n'.join(f"file 'scene-{i:02}.mp4'" for i in range(len(scenes))))
video=out/'AccelProof-Demo-自然配音版.mp4'
subprocess.run([ff,'-v','error','-y','-f','concat','-safe','0','-i',str(build/'concat.txt'),'-c:v','copy','-af','aresample=async=1:first_pts=0','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(video)],check=True)
subprocess.run([ff,'-v','error','-y','-i',str(video),'-vn','-c:a','libmp3lame','-q:a','2',str(out/'AccelProof-自然配音.mp3')],check=True)
(out/'Demo字幕.srt').write_text('\n'.join(subs));(out/'subtitle-timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2))
(out/'Demo解说稿.md').write_text('# AccelProof 自然配音版解说稿\n\n使用 zh-CN-YunxiNeural 中文神经男声，-2% 语速，AI 合成，非真人录音。按实际单词时间戳生成字幕。画面沿用 v2 实验记录与操作录屏，保持原速；在解释错误值和两种运行模式时暂停画面，保留标注。\n\n'+'\n\n'.join(f'## {i+1}. {s["title"]}\n\n{s["text"]}' for i,s in enumerate(scenes)))
meta={'version':'v2.1 narration revision','duration_seconds':probe(video),'resolution':'1920x1080','fps':25,'narration':'Microsoft Edge neural TTS, zh-CN-YunxiNeural; synthetic, not a human recording','rate':'-2%','pitch':'+0Hz','scenes':records,'subtitle_timing':'provider word boundaries, with 250 ms lead-in; not proportional character interpolation','live_capture_scenes':[2,3,4,5,6],'source_footage_changed':False,'public_published':False}
(out/'video-build.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));print('COMPLETE',meta['duration_seconds'],flush=True)
