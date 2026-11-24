                                                                                         

                                                                                                                 
                                                                                                                        
                                                                             
                                                                                                 
                                                                                                                                
   
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "BuildArena-1.0")
                                                                                                                                     
PY = os.environ.get("UNSEEN17_PY_BUILDARENA_1_0", os.path.join(os.path.dirname(os.path.dirname(ROOT)), "envs", "buildarena-1.0", "bin", "python"))
STATE = os.path.join(HERE, "state.json")
N_SAMPLE = 5
CONC = int(os.environ.get("BA_CONC", "3"))
TASKS = [(c, l) for c in ("transport", "support", "lift") for l in ("soft", "medium", "hard")]
                                                                                                              
                                                                                          
ONLY = [c for c in os.environ.get("BA_ONLY", "").split(",") if c]
                                                                                                      
ZOOM = {("support", "soft"): 6, ("support", "medium"): 5, ("support", "hard"): 3,
        ("lift", "soft"): 6, ("lift", "medium"): 3, ("lift", "hard"): 3,                                       
        ("transport", "soft"): 3, ("transport", "medium"): 3, ("transport", "hard"): 3}                      


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print(f"{now()} {msg}", flush=True)


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"created": now(), "tasks": {f"{c}_{l}": {"category": c, "level": l, "construction": "pending",
                                                    "simulation": "pending", "scoring": "pending"} for c, l in TASKS}}


def save_state(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def task_dir(key):
    d = os.path.join(HERE, key)
    os.makedirs(d, exist_ok=True)
    return d


def env_for(key):
    d = task_dir(key)
    cat, lvl = key.split("_")
    return {**os.environ, "H0_CALL_LOG": os.path.join(d, "h0-calls.jsonl"), "H0_METER_LOG": os.path.join(d, "cli-meter.jsonl"),
            "BUILDARENA_ZOOM": str(ZOOM[(cat, lvl)]), "BUILDARENA_FREE_BUILD": "1"}                                                            


def find_db(key):
    logf = os.path.join(task_dir(key), "construction.log")
    if not os.path.exists(logf):
        return None
    m = re.search(r"Database initialized at (\S+task_database\.db)", open(logf, errors="ignore").read())
    return os.path.normpath(os.path.join(SRC, m.group(1))) if m else None


def start_construction(key, t):
    d = task_dir(key)
    cmd = [PY, "run_h0.py", "--model", "h0-opus-5", "--category", t["category"], "--level", t["level"],
           "--n_sample", str(N_SAMPLE), "--n_worker", str(N_SAMPLE)]
    p = subprocess.Popen(cmd, cwd=SRC, env=env_for(key), stdout=open(os.path.join(d, "construction.log"), "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
    t.update(construction="running", construction_pid=p.pid, construction_started=now())
    log(f"{key}: construction started (pid {p.pid})")
    return p


def screen_locked():
    import Quartz
    d = Quartz.CGSessionCopyCurrentDictionary() or {}
    return bool(d.get("CGSSessionScreenIsLocked", False))


def run_simulation(key, t):
    d = task_dir(key)
                                                                                           
    if screen_locked():
        log(f"{key}: screen is locked; simulation waits until it is unlocked")
        while screen_locked():
            time.sleep(30)
        log(f"{key}: screen unlocked")
                                                                                                                
                                                                                                                  
    proj = os.path.basename(os.path.dirname(t["db"]))
    resume = os.path.exists(os.path.join(SRC, "datacache", f"{proj}_sim", "simulation_database.db"))
    if t["category"] == "support":                                                                       
        rc = subprocess.run([PY, "-W", "ignore", "run_sim_h0.py", "--load-level", f"support_{t['level']}"], cwd=SRC,
                            env=env_for(key), stdin=subprocess.DEVNULL, stdout=open(os.path.join(d, "simulation.log"), "a"),
                            stderr=subprocess.STDOUT).returncode
        if rc != 0:
            raise RuntimeError(f"could not load level support_{t['level']}")
        log(f"{key}: level support_{t['level']} loaded")
    t.update(simulation="running", simulation_started=now())
    log(f"{key}: simulation started for {t['db']}" + (" (official --resume)" if resume else ""))
                                                                                                                 
    awake = subprocess.Popen(["caffeinate", "-dimsu"])
    try:
        rc = subprocess.run([PY, "-W", "ignore", "run_sim_h0.py", "--db", t["db"]] + (["--resume"] if resume else []), cwd=SRC, env=env_for(key), stdin=subprocess.DEVNULL,
                            stdout=open(os.path.join(d, "simulation.log"), "a"), stderr=subprocess.STDOUT).returncode
    finally:
        awake.terminate()
    t.update(simulation="done" if rc == 0 else "failed", simulation_rc=rc, simulation_finished=now())
    log(f"{key}: simulation finished rc={rc}")


def score(key, t):
    pass                                                                    
    proj = os.path.basename(os.path.dirname(t["db"]))
    sim_root = os.path.join(SRC, "datacache", f"{proj}_sim", "simulation")
    results = []
    for mdir in sorted(glob.glob(os.path.join(sim_root, "*"))):
        if not glob.glob(os.path.join(mdir, "simulation_log_*.csv")):
            continue
        code = (f"import json,sys; from analyze.sim_{t['category']} import analyze_simulation_{t['category']} as f; "
                f"r=f({json.dumps(os.path.relpath(mdir, SRC))}); print('@@'+json.dumps(r, default=str))")
        out = subprocess.run([PY, "-c", code], cwd=SRC, capture_output=True, text=True)
        line = next((l for l in out.stdout.splitlines() if l.startswith("@@")), None)
        r = json.loads(line[2:]) if line else {"error": (out.stderr or out.stdout)[-800:]}
        r["machine_dir"] = os.path.relpath(mdir, ROOT)
        results.append(r)
    json.dump(results, open(os.path.join(task_dir(key), "results.json"), "w"), indent=1, default=str)
    passed = sum(1 for r in results if r.get("pass") is True)
    t.update(scoring="done", machines_scored=len(results), passed=passed, scored_at=now())
    log(f"{key}: scored {len(results)} simulated machines, pass {passed}")


LOCK = threading.Lock()


def save(st):
    with LOCK:
        save_state(st)


def sim_worker(st, stop):
    pass                                                                                        
    while not stop.is_set():
        with LOCK:
                                                                                                              
                                                                                                       
            order = sorted(st["tasks"], key=lambda k: (st["tasks"][k]["category"] == "transport", list(st["tasks"]).index(k)))
            nxt = next((k for k in order if st["tasks"][k]["construction"] == "done" and st["tasks"][k]["simulation"] == "pending"
                        and (not ONLY or st["tasks"][k]["category"] in ONLY)), None)
        if not nxt:
            time.sleep(30)
            continue
        t = st["tasks"][nxt]
        try:
            run_simulation(nxt, t); save(st)
            score(nxt, t); save(st)
        except Exception as exc:
            t.update(simulation="failed", simulation_error=repr(exc)); save(st)
            log(f"{nxt}: simulation/scoring error {exc!r}")


def main():
    st = load_state()
    for t in st["tasks"].values():                                                                     
        if t["simulation"] == "running":
            t["simulation"] = "pending"
    procs, stop = {}, threading.Event()
    threading.Thread(target=sim_worker, args=(st, stop), daemon=True).start()
    while True:
        with LOCK:
            tasks = st["tasks"]
            for key, t in tasks.items():
                if t["construction"] == "running":
                    p = procs.get(key)
                    alive = p.poll() is None if p else _pid_alive(t.get("construction_pid"))
                    if not alive:
                        t["db"] = find_db(key)
                        t.update(construction="done" if t["db"] else "failed", construction_finished=now())
                        log(f"{key}: construction finished ({t['construction']}), db {t['db']}")
            running = sum(1 for t in tasks.values() if t["construction"] == "running")
            for key, t in tasks.items():
                if running >= CONC:
                    break
                if t["construction"] == "pending":
                    procs[key] = start_construction(key, t)
                    running += 1
            save_state(st)
            finished = all(t["scoring"] == "done" or t["construction"] == "failed" or t["simulation"] == "failed"
                           for t in tasks.values() if not ONLY or t["category"] in ONLY)
        if finished:
            log("ALL TASKS FINISHED")
            stop.set()
            break
        time.sleep(30)


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    main()
