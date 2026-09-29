"""Synthesize narration only; no project files, measurements or private inputs are sent."""
import asyncio,json,html,re,argparse
from pathlib import Path
import edge_tts
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');args=parser.parse_args()
async def main():
 scenes=json.loads((ROOT/'narration/scenes.json').read_text())
 for i,s in enumerate(scenes):
  out=ROOT/'narration'/s['audio'];events=[]
  if not args.force and out.exists() and out.with_suffix('.words.json').exists() and out.with_suffix('.cues.json').exists():continue
  for attempt in range(3):
   try:
    events=[]
    with out.open('wb') as f:
     c=edge_tts.Communicate(s['text'],s['voice'],rate=s['rate'],pitch=s['pitch'],boundary='WordBoundary',connect_timeout=20,receive_timeout=90)
     async for chunk in c.stream():
      if chunk['type']=='audio':f.write(chunk['data'])
      elif chunk['type']=='WordBoundary':events.append(chunk)
    assert out.stat().st_size>5000 and events
    break
   except Exception:
    if attempt==2:raise
    await asyncio.sleep(2*(attempt+1))
  out.with_suffix('.words.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
  norm=lambda s:''.join(c.lower() for c in html.unescape(s) if c.isalnum())
  raw=s['text'];n=norm(raw);timings=[None]*len(n);pos=0
  for e in events:
   word=norm(e['text']);start=n.find(word,pos)
   if start<0:raise ValueError((i,word,pos))
   for j in range(start,start+len(word)):timings[j]=(e['offset']/1e7,(e['offset']+e['duration'])/1e7)
   pos=start+len(word)
  assert all(timings),(i,'incomplete alignment')
  clauses=[];buf='';offset=0
  for m in re.finditer(r'[^，。！？；：]+[，。！？；：]?',raw):
   part=m.group();buf+=part
   if len(buf)>=12 or buf.endswith(('。','？','！')):
    length=len(norm(buf));clauses.append({'start':timings[offset][0],'end':timings[offset+length-1][1],'text':buf});offset+=length;buf=''
  if buf:
   length=len(norm(buf));clauses.append({'start':timings[offset][0],'end':timings[offset+length-1][1],'text':buf})
  for j,c in enumerate(clauses):
   if j+1<len(clauses):c['end']=min(c['end']+.12,clauses[j+1]['start']-.015)
   assert c['end']>c['start']
  out.with_suffix('.cues.json').write_text(json.dumps(clauses,ensure_ascii=False,indent=2));print(i,s['title'],len(events),'word boundaries',len(clauses),'captions',flush=True)
asyncio.run(main())
