from pathlib import Path
import os,sys
BASE=Path(__file__).resolve().parent
sys.path.insert(1,str(Path(os.environ['BUILDARENA_ROOT'])));os.chdir(Path(os.environ['BUILDARENA_ROOT']))
import agents,h0_client
h0_client.H0_CALL=str(BASE/'h0_call.mjs')
class Client(h0_client.H0ChatCompletionClient):
 async def _call_node(self,payload):
  r=await super()._call_node(payload)
  if 'error' in r:raise RuntimeError(r['error'])
  return r
model=sys.argv[sys.argv.index('--model')+1]
assert model.startswith('h0-iter4-under40-')
agents.model_clients[model]=Client(max_retries=1)
import scheduler.task_db as task_db
original=task_db.mark_task_failed
def fail_once(task_id,error_info=None,db_path=None):
 original(task_id,error_info,db_path)
 import sqlite3
 with sqlite3.connect(db_path) as c:c.execute('update task set max_retries=retry_count where id=?',(task_id,))
task_db.mark_task_failed=fail_once
from script.run_construction import main
main()
