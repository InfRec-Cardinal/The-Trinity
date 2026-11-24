#!/usr/bin/env python3

import os,sys,subprocess,pathlib,time
import shutil
binary=os.environ.get('NATIVE_CODEX_BIN') or shutil.which('codex')
if not binary:raise RuntimeError('Set NATIVE_CODEX_BIN or install codex on PATH')
key=os.environ.get('NATIVE_CODEX_API_KEY')
if not key:raise SystemExit('Missing experiment provider credential')
args=sys.argv[1:]
settings=['-c','model_provider="experiment"','-c','model_providers.experiment.name="experiment"','-c','model_providers.experiment.base_url="'+os.environ.get('NATIVE_CODEX_BASE_URL','https://api.openai.com').rstrip('/')+'/v1"','-c','model_providers.experiment.wire_api="responses"','-c','model_providers.experiment.env_key="NATIVE_CODEX_API_KEY"','-c','model_providers.experiment.requires_openai_auth=false','-c','model_providers.experiment.request_max_retries=0','-c','model_providers.experiment.stream_max_retries=0']
i=args.index("exec") if "exec" in args else -1
if i<0:raise SystemExit("Native contract requires codex exec")
p=subprocess.run([binary,*args[:i+1],*settings,*args[i+1:]],input=sys.stdin.buffer.read(),capture_output=True)
r=pathlib.Path(os.environ['H0_NATIVE_DIAGNOSTICS_DIR']);r.mkdir(exist_ok=True);tag=str(time.time_ns())
(r/(tag+'.stdout')).write_text(p.stdout.decode(errors='replace').replace(key,'[redacted]'))
(r/(tag+'.stderr')).write_text(p.stderr.decode(errors='replace').replace(key,'[redacted]'))
sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);sys.exit(p.returncode)
