
import argparse,json,hashlib,sqlite3,sys,os,csv
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--iteration',type=int,required=True);a=p.parse_args()
BASE=Path(__file__).resolve().parent;sys.path.insert(1,str(Path(os.environ['BUILDARENA_ROOT'])));os.chdir(Path(os.environ['BUILDARENA_ROOT']))
db=Path(a.db).resolve();case='_'.join(db.parent.name.split('_')[:2]);category=case.split('_')[0]
from analyze.sim_transport import analyze_simulation_transport
from analyze.sim_lift import analyze_simulation_lift
from analyze.sim_support import analyze_simulation_support
scorer={'transport':analyze_simulation_transport,'lift':analyze_simulation_lift,'support':analyze_simulation_support}[category]
c=sqlite3.connect(db);c.row_factory=sqlite3.Row
rows=[dict(r) for r in c.execute("select * from task where stage='simulation'")]
assert rows and all(r['status']=='completed' for r in rows),[(r['id'],r['status']) for r in rows]
machines=list((db.parent/'simulation').glob('*'));machines=[m for m in machines if m.is_dir()];assert len(machines)==1
m=machines[0];generations=[1,2,3] if category=='transport' else [None];scores=[]
for gen in generations:
 suffix=f'_{gen}' if gen is not None else ''
 trace=m/f'simulation_log_{m.name}_sim{suffix}.csv';assert trace.is_file(),trace
 data=list(csv.reader(trace.open()));times=sorted(set(round(float(r[0]),2) for r in data if len(r)==5))
 n=250 if case=='lift_soft' else 425 if category=='support' else 750
 assert times==[round((i+1)*.04,2) for i in range(n)],(trace,len(times),times[:2],times[-2:])
                                                                            
 if any(cell!=cell.strip() for row in data for cell in row):
  import shutil
  backup=trace.with_suffix('.before-field-strip.csv');assert not backup.exists()
  shutil.copy2(trace,backup)
  with trace.open('w',newline='') as f:csv.writer(f).writerows([[cell.strip() for cell in row] for row in data])
 if category=='transport':
  from analyze.sim_common import clean_simulation_data
  frame=clean_simulation_data(str(trace));assert 'ID_1' in set(frame.id) or 'ID_Ballast' in set(frame.id),'Missing scorer tracking target'
 score=scorer(str(m),sim_round=gen)
 scores.append({'generation':gen,'score':score,'sample_count':len(times),'csv_sha256':hashlib.sha256(trace.read_bytes()).hexdigest()})
                                                                                
                                                                              
                                                                             
best=max(scores,key=lambda item:int(item['score']['pass'])) if category=='transport' else scores[-1]
result={'iteration':a.iteration,'case':case,'valid':True,'native_score':best['score'],'scalar_native_score':int(best['score']['pass']),'score_metric':'native pass/fail (no scalar composite supplied)','selected_generation':best['generation'],'final_generation_score':scores[-1]['score'],'generations':scores,'selection':'best native pass/fail across all three prescribed trials; earliest tie' if category=='transport' else 'single prescribed native trial','selection_source':'source/levels.yaml: Evaluation Protocol','simulation_adapter':'private-window Linux adapter; see invocation logs for version'}
out=Path(os.environ['BUILDARENA_EPISODE_DIR'])/'native-result.json';
if out.exists():
 backup=out.with_name('native-result.before-selection-fix.json')
 if not backup.exists():backup.write_bytes(out.read_bytes())
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
