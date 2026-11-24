
import os,sys,json,fcntl,argparse
from pathlib import Path
BASE=Path(__file__).resolve().parent
assert os.environ.get('DISPLAY','').split('.')[0]==':97'
p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--iteration',type=int,choices=[4],required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
db=Path(a.db).resolve();assert db.is_file()
sys.path.insert(0,os.environ['BUILDARENA_TRANSPORT_ROOT']);sys.path.insert(1,str(Path(os.environ['BUILDARENA_ROOT'])));os.chdir(Path(os.environ['BUILDARENA_ROOT']))
from linux_sim_v3 import run_sequence,observer_state
                                                                 
import pyautogui
_inherited_x_connections=[]
def reset_child_x_connection():
    from Xlib import display
    _inherited_x_connections.append(pyautogui._pyautogui_x11._display)
    pyautogui._pyautogui_x11._display=display.Display(':97')
os.register_at_fork(after_in_child=reset_child_x_connection)
                                                                                    
lock=(BASE/'native-evaluation.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
case='_'.join(db.parent.name.split('_')[:2]);category=case.split('_')[0]
expected='MasterSceneMultiplayer' if category=='support' else 'BARREN EXPANSE'
os.environ['BUILDARENA_EXPECTED_SCENE']=expected
assert observer_state()['scene']==expected,'Load correct official scene first'
out=Path(os.environ['BUILDARENA_EPISODE_DIR'])/'native-evaluation';out.mkdir(exist_ok=a.resume)
os.environ.update(BUILDARENA_EPISODE_DIR=str(out),H0_CALL_LOG=str(out/'h0-calls.jsonl'),
 BESIEGE_SAVED_MACHINES=os.environ['BESIEGE_SAVED_MACHINES'])
import simulation.operations as ops
ops.run_simulation_sequence=run_sequence
import h0_client,agents
h0_client.H0_CALL=str(BASE/'h0_call.mjs')
class Client(h0_client.H0ChatCompletionClient):
 async def _call_node(self,payload):
  r=await super()._call_node(payload)
  if 'error' in r:raise RuntimeError(r['error'])
  return r
agents.model_clients[os.environ['BUILDARENA_ROLE_MODEL']]=Client(max_retries=1)
                                                                                  
import scheduler.task_db as task_db
old_failed=task_db.mark_task_failed
def fail_once(task_id,error_info=None,db_path=None):
 old_failed(task_id,error_info,db_path)
 import sqlite3
 with sqlite3.connect(db_path) as c:c.execute('update task set max_retries=retry_count where id=?',(task_id,))
task_db.mark_task_failed=fail_once
os.chdir(Path(os.environ['BUILDARENA_ROOT']))
from script.run_simulation import main
if a.resume:
 import sqlite3
 simdb=db.parent.with_name(db.parent.name+'_sim')/'simulation_database.db'
 connection=sqlite3.connect(simdb)
 failed=connection.execute("select id,stage,status,error_info from task where status not in ('completed','simulated')").fetchall()
 assert failed and all(row[1]=='simulation' and row[2]=='failed' and any(reason in (row[3] or '') for reason in ['Expected reply for request','Game observer state stale']) for row in failed),failed
 backup=out/'before-native-adapter-repair.db'
 assert not backup.exists(),'Native adapter resume already performed'
 connection.backup(sqlite3.connect(backup));connection.close()
main(original_db_path=str(db),rfd_only=True,max_workers=1,resume=a.resume)
(out/'process-ended.json').write_text(json.dumps({'db':str(db),'case':case,'note':'Review native DB and analyze every required generation; process exit is not valid score.'},indent=2))
