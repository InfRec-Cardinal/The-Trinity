#!/usr/bin/env python3

import os,sys
import shutil
binary=os.environ.get('NATIVE_CODEX_BIN') or shutil.which('codex')
if not binary:raise RuntimeError('Set NATIVE_CODEX_BIN or install codex on PATH')
if not os.environ.get('NATIVE_CODEX_API_KEY'):raise SystemExit('Missing experiment provider credential')
args=sys.argv[1:]
settings=['-c','model_provider="experiment"','-c','model_providers.experiment.name="experiment"',
 '-c','model_providers.experiment.base_url="'+os.environ.get('NATIVE_CODEX_BASE_URL','https://api.openai.com').rstrip('/')+'/v1"',
 '-c','model_providers.experiment.wire_api="responses"',
 '-c','model_providers.experiment.env_key="NATIVE_CODEX_API_KEY"',
 '-c','model_providers.experiment.requires_openai_auth=false',
 '-c','model_providers.experiment.request_max_retries=0',
 '-c','model_providers.experiment.stream_max_retries=0']
os.execv(binary,[binary,args[0],*settings,*args[1:]])
