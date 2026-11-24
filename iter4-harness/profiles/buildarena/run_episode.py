from pathlib import Path
import argparse,os,sys,json,subprocess,time,hashlib
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);p.add_argument('--out',required=True);p.add_argument('--release',required=True);p.add_argument('--skills',required=True);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=False);start=time.time()
model=f'h0-iter4-under40-{hashlib.sha256(str(out.resolve()).encode()).hexdigest()[:12]}-a{a.attempt}'
env={**os.environ,'DISPLAY':':97','BUILDARENA_EPISODE_DIR':str(out),'H0_CALL_LOG':str(out/'h0-calls.jsonl'),'BUILDARENA_RELEASE':a.release,'BUILDARENA_SKILL':a.skills,'BUILDARENA_ROLE_MODEL':model}
env['BESIEGE_SAVED_MACHINES']=os.environ['BESIEGE_SAVED_MACHINES']
Path(env['BESIEGE_SAVED_MACHINES']).mkdir(parents=True,exist_ok=True)
def call(args,log):
 with (out/log).open('w') as f:
  cp=subprocess.run([sys.executable,*args],env=env,stdout=f,stderr=subprocess.STDOUT)
 if cp.returncode:raise RuntimeError(f'{log} ended with code {cp.returncode}; inspect native logs')
r={'taskId':'buildarena_1_0','caseId':'transport_soft','outcome':'error','ended':False,'score':None}
try:
 sys.path.insert(0,os.environ['BUILDARENA_TRANSPORT_ROOT']);os.environ['DISPLAY']=':97'
 from linux_sim_v3 import observer_state
 assert observer_state()['scene']=='BARREN EXPANSE'
 call([str(BASE/'run-construction.py'),'--model',model,'--category','transport','--level','soft','--n_sample','1','--n_worker','1'],'construction.log')
 files=list((Path(os.environ['BUILDARENA_ROOT'])/'datacache').glob(f'transport_soft_{model}_*/task_database.db'));assert len(files)==1,files
 db=files[0];(out/'database.json').write_text(json.dumps({'construction':str(db)}))
 call([str(BASE/'run-native.py'),'--db',str(db),'--iteration','4'],'native.log')
 simdb=db.parent.with_name(db.parent.name+'_sim')/'simulation_database.db'
 call([str(BASE/'score-native.py'),'--db',str(simdb),'--iteration','4'],'score.log')
 native=json.loads((out/'native-evaluation/native-result.json').read_text()) if (out/'native-evaluation/native-result.json').exists() else json.loads((out/'native-result.json').read_text())
 r.update(outcome='success' if native['scalar_native_score']==1 else 'failure',ended=True,score=native['scalar_native_score'],native=native)
except Exception as e:r['reason']=str(e)
r['seconds']=round(time.time()-start);(out/'results.json').write_text(json.dumps({'results':[r]},indent=2)+'\n');print('FINISHED buildarena_1_0:',r['outcome'],flush=True)
sys.exit(1 if r['outcome']=='error' else 0)
