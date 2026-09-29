"""Entry point for the v2.1 neural narration video; see media/source/requirements-neural.txt."""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[1]
if '--source' not in sys.argv:sys.argv.extend(['--source',str(root/'media/source/screenshots')])
if '--out' not in sys.argv:sys.argv.extend(['--out',str(root/'media')])
runpy.run_path(str(root/'media/source/render_neural.py'),run_name='__main__')
