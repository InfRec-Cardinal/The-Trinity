import argparse,json,os,signal,subprocess,time
from pathlib import Path

base=Path(__file__).resolve().parent
from transport.prerequisites import installation

p=argparse.ArgumentParser(description='Start the user-installed Besiege on a dedicated Linux display.')
p.add_argument('--out',type=Path,help='new directory for session logs')
p.add_argument('--game-root',type=Path,default=os.environ.get('BESIEGE_GAME_ROOT'))
p.add_argument('--mod-root',type=Path,default=os.environ.get('BESIEGE_MOD_ROOT'))
p.add_argument('--check',action='store_true',help='check external files and tools only; do not launch or write logs')
p.add_argument('--probe-seconds',type=float,default=0)
a=p.parse_args()
try:game,mod,xvfb,vgl=installation(a.game_root,a.mod_root)
except ValueError as error:p.exit(2,f'{error}\n')
if a.check:
    print('External prerequisite files found; no game, display or observer was started.')
    raise SystemExit(0)
if not a.out:p.error('--out is required to launch')
if Path('/tmp/.X11-unix/X97').exists():raise SystemExit('Display :97 is already in use')
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
saved=Path(os.environ.get('BESIEGE_SAVED_MACHINES',game.parent/'Besiege_Data/SavedMachines')).resolve();saved.mkdir(parents=True,exist_ok=True)
env={**os.environ,'DISPLAY':':97','SteamAppId':'346010','SteamGameId':'346010','BESIEGE_SAVED_MACHINES':str(saved),'BESIEGE_GAME_ROOT':str(game.parent),'BESIEGE_MOD_ROOT':str(mod),
     'BUILDARENA_ROOT':str(base.parent/'BuildArena-1.0'),'BUILDARENA_TRANSPORT_ROOT':str(base/'transport')}
children=[]
def stop(*_):
    for c in reversed(children):
        if c.poll() is None:
            c.terminate()
            try:c.wait(timeout=5)
            except subprocess.TimeoutExpired:c.kill();c.wait()
def interrupted(signum,_):raise SystemExit(128+signum)
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
try:
    with (out/'display.log').open('w') as display_log,(out/'game.log').open('w') as game_log:
        display=subprocess.Popen([str(xvfb),':97','-screen','0','1280x800x24','-nolisten','tcp'],env=env,stdout=display_log,stderr=subprocess.STDOUT)
        children.append(display)
        for _ in range(100):
            if display.poll() is not None:raise RuntimeError('Private display failed; inspect display.log')
            if Path('/tmp/.X11-unix/X97').exists():break
            time.sleep(.05)
        else:raise RuntimeError('Private display did not start')
        cmd=[str(vgl),'-d','egl',str(game),'-screen-fullscreen','0','-screen-width','1280','-screen-height','800','-mod',str(mod),'-logFile',str(out/'player.log'),'-popupwindow','-force-glcore']
        native=subprocess.Popen(cmd,cwd=game.parent,env=env,stdout=game_log,stderr=subprocess.STDOUT)
        children.append(native)
        (out/'launch.json').write_text(json.dumps({'display':':97','game':str(game),'pid':native.pid,'environment':{k:env[k] for k in ['DISPLAY','BUILDARENA_ROOT','BUILDARENA_TRANSPORT_ROOT','BESIEGE_SAVED_MACHINES','BESIEGE_GAME_ROOT','BESIEGE_MOD_ROOT']}},indent=2),encoding='utf-8')
        if a.probe_seconds:
            try:native.wait(timeout=a.probe_seconds)
            except subprocess.TimeoutExpired:pass
            else:raise RuntimeError(f'Native game exited during startup: {native.returncode}')
        elif native.wait()!=0:raise RuntimeError('Native game exited with an error')
finally:stop()
