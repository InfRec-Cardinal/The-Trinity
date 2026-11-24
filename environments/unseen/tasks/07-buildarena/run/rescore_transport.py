                                                                                                                 
                                                                                     
                                                                                                               
import glob, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); SRC = os.path.join(ROOT, "BuildArena-1.0")
PY = os.environ.get("UNSEEN17_PY_BUILDARENA_1_0", os.path.join(os.path.dirname(os.path.dirname(ROOT)), "envs", "buildarena-1.0", "bin", "python"))
st = json.load(open(os.path.join(HERE, "state.json")))
for lvl in sys.argv[1:] or ["soft", "medium", "hard"]:
    t = st["tasks"][f"transport_{lvl}"]
    proj = os.path.basename(os.path.dirname(t["db"]))
    out = []
    for mdir in sorted(glob.glob(os.path.join(SRC, "datacache", f"{proj}_sim", "simulation", "*"))):
        rounds = {}
        for rnd in (1, 2, 3):
            if not os.path.exists(os.path.join(mdir, f"simulation_log_{os.path.basename(mdir)}_sim_{rnd}.csv")):
                continue
            code = (f"import json; from analyze.sim_transport import analyze_simulation_transport as f; "
                    f"r=f({json.dumps(os.path.relpath(mdir, SRC))}, sim_round={rnd}); print('@@'+json.dumps(r, default=str))")
            p = subprocess.run([PY, "-W", "ignore", "-c", code], cwd=SRC, capture_output=True, text=True)
            line = next((l for l in p.stdout.splitlines() if l.startswith("@@")), None)
            rounds[rnd] = json.loads(line[2:]) if line else {"error": (p.stderr or p.stdout)[-500:]}
        final = rounds.get(3) or rounds.get(max(rounds)) if rounds else {}
        out.append({"machine_id": os.path.basename(mdir), "rounds": rounds,
                    "final_round": max(rounds) if rounds else None, "pass_final": bool(final.get("pass")),
                    "pass_any_round": any(r.get("pass") for r in rounds.values()),
                    "pass_by_round": {k: r.get("pass") for k, r in rounds.items()},
                    "max_distance_by_round": {k: r.get("max_transport_distance") for k, r in rounds.items()}})
    json.dump(out, open(os.path.join(HERE, f"transport_{lvl}", "results_rounds.json"), "w"), indent=1, default=str)
    print(f"transport_{lvl}: machines {len(out)}, pass final {sum(o['pass_final'] for o in out)}, "
          f"pass any round {sum(o['pass_any_round'] for o in out)}, by round "
          f"{[sum(1 for o in out if o['pass_by_round'].get(k)) for k in (1, 2, 3)]}")
