import runpy
import sys
from pathlib import Path

sys.argv = [str(Path(__file__).resolve().parents[3] / 'download.py'), '--asset', 'actiview', *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
