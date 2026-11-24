                                                                                                    
                                                                                                              
                                                                                                   
                                                                                    
                             
                                                                                                           
import ast
import hashlib
import importlib.abc
import importlib.util
import json
import os
import random
import sys
from collections import OrderedDict
from pathlib import Path

if os.environ.get("PYTHONHASHSEED") != "0":
    raise RuntimeError("The pooltool worker must start with PYTHONHASHSEED=0")

                                                                                                                 
PUBLIC_STDOUT = sys.stdout
sys.stdout = sys.stderr

VENDOR = Path(os.environ["POOLTOOL_VENDOR_DIR"]).resolve()                                                                
TASK_ID = "pooltool_billiards_shots"
PRIVATE_CONFIG = VENDOR / "configuration"                                                                   
sys.dont_write_bytecode = True


class PrivatePooltoolConfiguration(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    pass                                                                                                     

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pooltool.config.user":
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.CONFIG_DIR = PRIVATE_CONFIG
        module.PHYSICS_DIR = PRIVATE_CONFIG / "physics"


sys.meta_path.insert(0, PrivatePooltoolConfiguration())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pooltool as pt


def original_functions(filename, names, namespace):
    pass                                                                                               
    module = ast.parse(filename.read_text(encoding="utf8"), filename=str(filename))
    selected = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != set(names):
        raise ValueError("The required original Pooltool helpers changed")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(filename), "exec"), namespace)


_namespace = {"pt": pt, "np": np, "plt": plt, "OrderedDict": OrderedDict}
original_functions(VENDOR / "deepphy/runner/04_pooltool_runner.py",
                   {"setup_pooltool_game", "check_for_potted_balls", "get_cue_ball_reposition_point"}, _namespace)
original_functions(VENDOR / "deepphy/utils/img_utils.py", {"plot_static_pool_table"}, _namespace)
setup_pooltool_game = _namespace["setup_pooltool_game"]
check_for_potted_balls = _namespace["check_for_potted_balls"]
get_cue_ball_reposition_point = _namespace["get_cue_ball_reposition_point"]
plot_static_pool_table = _namespace["plot_static_pool_table"]
CONFIGURATION = json.loads((VENDOR / "conf/env_config_04_pooltool.json").read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def setup_seeded_game(seed):
    pass                                                               
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 100:
        raise ValueError("Expected one seed in 0..99")
    random.seed(seed)
    np.random.seed(seed)
    return setup_pooltool_game()


def state_record(system):
    pass                                                                         
    return {"table": {"width": float(system.table.w), "length": float(system.table.l)},
            "balls": {name: {"rvw": ball.state.rvw.tolist(), "state": int(ball.state.s),
                             "time": float(ball.state.t), "radius": float(ball.params.R)}
                      for name, ball in system.balls.items()}}


def prepare_next_observation(system):
    pass                                                                          
    cue_id = system.cue.cue_ball_id
    if cue_id not in system.balls:
        point = get_cue_ball_reposition_point(system.table)
        system.balls[cue_id] = pt.Ball.create(cue_id, xy=point[:2])
    system.stop_balls()
    system.reset_history()


def simulate_shot(system, speed, strikespot):
    pass                                                                        

                                                                             
                                                                                                              
       
    if not isinstance(speed, str) or not isinstance(strikespot, str) \
            or speed not in CONFIGURATION["speed_mapping"] or strikespot not in CONFIGURATION["strikespot_mapping"]:
        return {"outcome": "INVALID_VLM_ACTION", "potted": [], "solved": False,
                "resolved": None, "physicsExecuted": False}
    cue_id = system.cue.cue_ball_id
    targets = sorted((name for name in system.balls if name != cue_id and name.isdigit()
                      and 1 <= int(name) <= 15), key=int)
    if not targets:
        return {"outcome": "NO_TARGET_BALLS_LEFT", "potted": [], "solved": "9" not in system.balls,
                "resolved": None, "physicsExecuted": False}
    velocity = CONFIGURATION["speed_mapping"][speed]
    offsets = CONFIGURATION["strikespot_mapping"][strikespot]
    azimuth = pt.aim.at_ball(system, targets[0])
    system.cue.set_state(V0=velocity, phi=azimuth, a=offsets["a"], b=offsets["b"])
    try:
        pt.simulate(system, inplace=True)
    except Exception as error:
        return {"outcome": "SIMULATION_CRASHED_ROOT_SOLVER_ISSUE" if isinstance(error, ValueError)
                and "cannot assign slice of shape (2,) from input of shape (4,)" in str(error)
                else "UNEXPECTED_SIMULATION_ERROR", "potted": [], "solved": False,
                "resolved": [velocity, offsets["a"], offsets["b"]], "physicsExecuted": True,
                "nativeErrorType": type(error).__name__, "nativeError": str(error)}
    potted = [name for name, value in check_for_potted_balls(system).items() if value]
    native_events = pt.serialize.conversion[pt.serialize.SerializeFormat.JSON].unstructure(system.events)
    post_simulation_state = state_record(system)
    outcome = "9_BALL_POTTED" if "9" in potted else "CUE_BALL_POTTED" if cue_id in potted \
        else "NO_BALLS_POTTED" if not potted else "OTHER_BALLS_POTTED"
    system.balls = OrderedDict((name, ball) for name, ball in system.balls.items() if name not in potted)
    return {"outcome": outcome, "potted": potted, "solved": "9" in potted,
            "resolved": [velocity, offsets["a"], offsets["b"]], "physicsExecuted": True,
            "forcedTarget": targets[0], "resolvedAzimuth": float(azimuth),
            "nativeEvents": native_events, "postSimulationState": post_simulation_state}


class Episode:
    def init(self, configuration, run_root, episode_path):
        self.seed = configuration["seed"]
        self.configuration_hash = configuration["configurationHash"]
        self.run_root = Path(run_root).resolve()
        self.directory = self.run_root / episode_path
        self.directory.mkdir(parents=True, exist_ok=True)
        self.system = setup_seeded_game(self.seed)
        prepare_next_observation(self.system)
        self.step_count = 0
        self.last_result = None
        self.reason = None
        self.outcome = None
        return self.observation()

    def observation(self):
        native_state = state_record(self.system)
        state_hash = digest({"configurationHash": self.configuration_hash, "step": self.step_count,
                             "nativeState": native_state, "lastResult": self.last_result,
                             "reason": self.reason, "outcome": self.outcome})
        path = self.directory / "media" / (state_hash + ".png")
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.stem + ".pending.png")
            plot_static_pool_table(self.system, filename=str(temporary))
            os.replace(temporary, path)
        text = ("Nine-ball: pot ball9 within15 shots. Each shot is automatically aimed at the lowest-numbered remaining ball. "
                "Choose Speed Low/Medium/High (2/5/8m/s) and one stated Strikespot; cue scratches are replaced at the original head-string point. "
                + "Shot count " + str(self.step_count) + "; remaining " + str(max(0, 15 - self.step_count)) + ".")
        return {"publicText": text,
                "frame": {"path": str(path.relative_to(self.run_root)),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mimeType": "image/png"},
                "step": self.step_count, "stateHash": state_hash,
                "terminal": {"ended": self.reason is not None, "outcome": self.outcome, "reason": self.reason,
                             "score": 1 if self.outcome == "success" else 0 if self.outcome == "failure" else None}}

    def apply(self, action):
        if self.reason is not None:
            raise ValueError("Native task already terminal")
        self.step_count += 1
        speed = action.get("speed") if isinstance(action, dict) else None
        strikespot = action.get("strikespot") if isinstance(action, dict) else None
                                                                                                         
        self.last_result = json.loads(json.dumps(simulate_shot(self.system, speed, strikespot), allow_nan=False))
        if self.last_result["outcome"] in ("UNEXPECTED_SIMULATION_ERROR", "SIMULATION_CRASHED_ROOT_SOLVER_ISSUE"):
            self.reason = "native_simulation_error"
            self.outcome = "invalid"
        elif self.last_result["solved"]:
            self.reason = "native_ball9_pocketed"
            self.outcome = "success"
        elif self.last_result["outcome"] == "NO_TARGET_BALLS_LEFT":
            self.reason = "native_no_numbered_target"
            self.outcome = "failure"
        elif self.step_count == 15:
            self.reason = "source15shot_budget_exhausted"
            self.outcome = "failure"
        if self.reason is None:
            prepare_next_observation(self.system)

    def step(self, action, expected_step):
        if expected_step is not None and expected_step != self.step_count:
            raise ValueError("Native Pooltool sequence changed")
        self.apply(action)
        return self.observation()


def main():
    episode = None
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        try:
            name = request["command"]
            if name == "init":
                episode = Episode()
                result = episode.init(request["configuration"], request["runDir"], request["episodePath"])
            elif name == "step":
                if episode is None:
                    raise ValueError("No episode initialised")
                result = episode.step(request["action"], request.get("expectedStep"))
            elif name == "close":
                print(json.dumps({"id": request["id"], "ok": True, "result": {"closed": True}}), file=PUBLIC_STDOUT, flush=True)
                return
            else:
                raise ValueError("Unknown Pooltool command")
            print(json.dumps({"id": request["id"], "ok": True, "result": result}, allow_nan=False), file=PUBLIC_STDOUT, flush=True)
        except Exception as error:                
            print(json.dumps({"id": request.get("id"), "ok": False, "message": f"{type(error).__name__}: {error}"}),
                  file=PUBLIC_STDOUT, flush=True)


if __name__ == "__main__":
    main()
