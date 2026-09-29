import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from accelproof.stages import main
if __name__=="__main__":main(["intake"]+sys.argv[1:])
