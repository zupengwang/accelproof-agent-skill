"""Compatibility entry point. Choose run (obey backend) or verify (explicit CPU/GPU)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from accelproof.workflow import main
if __name__=='__main__':main()
