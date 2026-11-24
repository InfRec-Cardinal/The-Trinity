import argparse
import runpy
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--videos')
ap.add_argument('--keep-going', action='store_true')
a = ap.parse_args()
args = [str(Path(__file__).resolve().parents[3] / 'download.py'), '--asset', 'videomme']
for video in a.videos.split(',') if a.videos else []:
    args.extend(['--video', video])
sys.argv = args
runpy.run_path(sys.argv[0], run_name='__main__')
