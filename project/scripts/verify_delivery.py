import hashlib,json,zipfile
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();root=a.package
manifest=json.loads((root/'SHA256SUMS.json').read_text())
for rel,wanted in manifest.items():
 path=root/rel
 assert path.is_file(),rel
 assert hashlib.sha256(path.read_bytes()).hexdigest()==wanted,rel
print(json.dumps({'files':len(manifest),'all_hashes_match':True},ensure_ascii=False))
