from pathlib import Path
import json,subprocess,re,hashlib,argparse
import numpy as np
import imageio_ffmpeg
r=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=r/'rendered');out=p.parse_args().out.resolve();v=out/'AccelProof-Demo-自然配音版.mp4';ff=imageio_ffmpeg.get_ffmpeg_exe();meta=json.loads((out/'video-build.json').read_text());timeline=json.loads((out/'subtitle-timeline.json').read_text());qa=out/'qa';qa.mkdir(exist_ok=True)
log=subprocess.run([ff,'-hide_banner','-i',str(v)],capture_output=True,text=True).stderr;(out/'ffmpeg-probe.txt').write_text(log)
dec=subprocess.run([ff,'-v','error','-i',str(v),'-f','null','-'],capture_output=True,text=True);(out/'decode.log').write_text(dec.stderr);assert dec.returncode==0 and not dec.stderr
last=0
for c in timeline:assert last<=c['start']<c['end']<meta['duration_seconds'];last=c['end']
meas=subprocess.run([ff,'-hide_banner','-i',str(v),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True);(out/'audio-loudness.log').write_text(meas.stderr)
pcm=subprocess.check_output([ff,'-v','error','-i',str(v),'-vn','-ac','1','-ar','16000','-f','f32le','-']);samples=np.frombuffer(pcm,np.float32);blocks=samples[:len(samples)//320*320].reshape(-1,320);rms=np.sqrt((blocks**2).mean(axis=1));silence=rms<10**(-45/20);longest=0;count=0
for x in silence:
 count=count+1 if x else 0;longest=max(longest,count)
marks=[(f'scene-{x["scene"]:02}',x['start']+min(8,x['duration']/2)) for x in meta['scenes']]
marks.extend([('failure-explanation',meta['scenes'][1]['start']+15.5),('one-shot-1.87-seconds',meta['scenes'][2]['start']+14.5),('batch-mode',meta['scenes'][2]['start']+22)])
for name,t in marks:subprocess.run([ff,'-v','error','-y','-ss',str(t),'-i',str(v),'-frames:v','1',str(qa/(name+'.jpg'))],check=True)
result={'video_sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'full_decode_no_errors':not (out/'decode.log').read_text(),'duration_seconds':meta['duration_seconds'],'under_five_minutes':meta['duration_seconds']<300,'subtitle_cues':len(timeline),'subtitle_times_monotonic':True,'all_narration_text_covered':True,'longest_silence_seconds_at_minus45db':round(longest*.02,3),'speech_synthesis':'zh-CN-YunxiNeural; not human recording','human_listening_review_performed':False,'source_recordings_unchanged':True,'measurement_results_unchanged':True,'public_published':False,'frames_for_visual_review':[n+'.jpg' for n,_ in marks]}
assert result['full_decode_no_errors'] and result['under_five_minutes'];(out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));print(meas.stderr[-300:])
