                                                                          

                                                                             
                                                                        
   
import os
import sys
import time
import subprocess
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from game_input import click, key, gui
from capture_game import capture

BASE = Path(__file__).resolve().parent
if not os.environ.get('BESIEGE_MOD_ROOT'):
    raise RuntimeError('Set BESIEGE_MOD_ROOT to the external Lua mod with the compatible observer')
OBSERVER = Path(os.environ['BESIEGE_MOD_ROOT']).expanduser().resolve()/'Observer'

def observer_state():
    for _ in range(200):
        try:
            state=json.loads((OBSERVER/'state.json').read_text())
            at=datetime.fromisoformat(state['wall'].replace('Z','+00:00')).timestamp()
            if abs(time.time()-at)>3:
                time.sleep(.1)
                continue
            return state
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.05)
    raise RuntimeError('Game observer state unavailable')


def snapshot(path):
    capture(path)
    return Image.open(path).convert('RGB')


def running(im):
    pixels = list(im.crop((18,18,36,38)).getdata())
    return sum(g>120 and b>100 and r<100 for r,g,b in pixels)>10


def log_open(im):
    return sum(max(p)-min(p)<60 and max(p)<80 for p in
               im.crop((400,130,700,220)).getdata()) > 22000


def copy_log():
    click(500,200)
    key('ctrl','a');key('ctrl','c')
    return subprocess.check_output(['xclip','-display',':97','-selection','clipboard','-o'],
                                   text=True,timeout=5)


def native_time(text):
    values=[]
    for line in text.splitlines():
        try: values.append(float(line.split(',')[0]))
        except ValueError: pass
    return max(values) if values else None


def run_sequence(machine_name, output_dir, duration, set_ground=False):
    out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    state=observer_state()
    if state['simulating']:raise RuntimeError('Existing simulation running')
    if state['scene']=='MasterSceneMultiplayer':
        if not os.environ.get('BUILDARENA_SUPPORT_ATTESTATION'):
            raise RuntimeError('Set BUILDARENA_SUPPORT_ATTESTATION for the optional support scene')
        att=json.loads(Path(os.environ['BUILDARENA_SUPPORT_ATTESTATION']).read_text())
        import hashlib
        if att['level']!='support_medium' or hashlib.sha256(Path(att['path']).read_bytes()).hexdigest()!=att['sha256']:
            raise RuntimeError('Support scene evidence mismatch')
    if state['scene'] not in [os.environ.get('BUILDARENA_EXPECTED_SCENE','BARREN EXPANSE')]:
        raise RuntimeError('Unexpected scene: '+state['scene'])
    im=snapshot(out/'before.png')
    if running(im):
        raise RuntimeError('Existing simulation running; refuse to interrupt it')
                                                                    
    if sum(r>100 and r>g*1.7 and r>b*1.3 for r,g,b in im.crop((16,125,195,150)).getdata())>2000:
        click(880,28);key('ctrl','l');time.sleep(.4)
    click(265,28);time.sleep(.8)
    click(610,169);key('ctrl','a');gui.write(machine_name,interval=.1)
    for _ in range(3):
        click(812,169);time.sleep(1.4)
        im=snapshot(out/'loaded.png')
        if observer_state()['machine']==machine_name and sum(r>150 and g<90 and b<130 for r,g,b in im.crop((15,16,40,40)).getdata())>=4:
            break
                                                                      
    if sum(r>150 and g<90 and b<130 for r,g,b in im.crop((15,16,40,40)).getdata())<4:
        raise RuntimeError('Load did not return to build mode')
    if observer_state()['machine']!=machine_name:
        raise RuntimeError('Requested machine did not load; refuse wrong-machine score')
    if set_ground:click(640,28);time.sleep(.5)
                                                            
    click(138,16);time.sleep(.3)
    if abs(observer_state()['time_scale']-1)>0.001:
        raise RuntimeError('Simulation speed is not 100%')
    key('ctrl','l');time.sleep(.3)
    chunks=[];latest=None;begun=time.time();stop=threading.Event();errors=[]
    evidence=out/('native-capture-'+str(time.time_ns())+'.jsonl')
    def collect():
        previous=None; fresh_epoch=False
        with evidence.open('w') as f:
            while not stop.is_set():
                try:
                    raw=(OBSERVER/'lua-snapshot.json').read_text()
                    item=json.loads(raw);state=item['state']
                    at=datetime.fromisoformat(state['wall'].replace('Z','+00:00')).timestamp()
                    if at>=begun and state['machine']==machine_name and state['simulating'] and raw!=previous:
                        previous=raw
                        t=native_time(item['text'])
                        if not fresh_epoch:
                            fresh_epoch=t is not None and 0<t<1
                        f.write(raw+'\n');f.flush()
                        if fresh_epoch:chunks.append(item['text'])
                except (FileNotFoundError,json.JSONDecodeError):pass
                except Exception as e:errors.append(str(e));return
                stop.wait(.05)
    collector=threading.Thread(target=collect,daemon=True);collector.start()
    try:
        click(27,28)
        for _ in range(50):
            if observer_state()['simulating']:break
            time.sleep(.1)
        im=snapshot(out/'started.png')
        if not observer_state()['simulating']:
            raise RuntimeError('Game did not enter simulation')
        while latest is None or latest<duration:
            if errors:raise RuntimeError(errors[0])
            latest=native_time(chunks[-1]) if chunks else None
            if time.time()-begun>60 and latest is None:
                raise RuntimeError('No native Lua samples after60s; investigate, not a valid score')
            time.sleep(.1)
        click(27,28)
        for _ in range(50):
            if not observer_state()['simulating']:break
            time.sleep(.1)
        im=snapshot(out/'stopped.png')
        if observer_state()['simulating']:
            raise RuntimeError('Game did not stop after native duration')
                                                                             
                                                    
        visible=copy_log()
        captured={line.strip() for chunk in chunks for line in chunk.splitlines()}
        visible_rows={line.strip() for line in visible.splitlines() if ',' in line}
        shared=len(visible_rows & captured)
        if shared<10:raise RuntimeError('GUI/observer Lua trace cross-check failed')
        (out/'gui-log-crosscheck.json').write_text(json.dumps(dict(shared_rows=shared,
            visible_rows=len(visible_rows),text=visible),indent=2)+'\n')
    finally:
        stop.set();collector.join(timeout=3)
        current=observer_state()
        if current['simulating'] and current['machine']==machine_name:
            click(27,28)
            time.sleep(1)
                                                                            
                                                                             
    lines=[]
    for raw in chunks:
        for line in raw.splitlines():
            try:t=float(line.split(',')[0])
            except ValueError:continue
            if 0<=t<=duration:lines.append(line)
    if not lines or min(float(l.split(',')[0]) for l in lines)>.5:
        raise RuntimeError('Initial physics samples absent; refuse incomplete score')
    csv=out/f'simulation_log_{machine_name}.csv'
                                                                 
    from simulation.operations import save_to_csv
    if csv.exists(): raise RuntimeError('Refuse to overwrite an existing physics trace')
    save_to_csv('\n'.join(lines), str(csv))
    from simulation.operations import clean_simulation_csv
    clean_simulation_csv(str(csv))
    click(880,28);key('ctrl','l')
    (out/'linux-simulation.json').write_text(json.dumps(dict(machine=machine_name,
        native_duration=duration,last_observed_time=latest,wall_seconds=time.time()-begun,
        display=':97',csv=str(csv),unfiltered_log=str(evidence)),
        indent=2)+'\n')
    return str(csv)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--machine',required=True)
    p.add_argument('--category',choices=['lift','support','transport'],required=True)
    p.add_argument('--level',choices=['soft','medium','hard'],required=True)
    p.add_argument('--control')
    a=p.parse_args()
    if not os.environ.get('BESIEGE_SAVED_MACHINES'):
        p.error('Set BESIEGE_SAVED_MACHINES to the installed game save directory')
    source = Path(os.environ.get('BUILDARENA_ROOT', BASE.parents[1]/'BuildArena-1.0')).resolve()
    sys.path.insert(0,str(source));os.chdir(source)
    import simulation.operations as ops
    ops.run_simulation_sequence=run_sequence
    import importlib
    sim=importlib.import_module('simulation.simulation_'+a.category)
    print(sim.main(a.machine,a.level,control_path=a.control) if a.category=='transport' else sim.main(a.machine,a.level))
