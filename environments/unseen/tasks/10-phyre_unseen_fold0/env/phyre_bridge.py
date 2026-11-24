                                                                                                  
                                                                                                 
                                                                                               
                                                                                                     
                                          
import base64, io, json, sys
import os
if os.environ.get("PHYRE_PKG_DIR"):                                                                                                          
    sys.path.insert(0, os.environ["PHYRE_PKG_DIR"])
import numpy as np
import phyre
from PIL import Image

PROTO = sys.stdout; sys.stdout = sys.stderr
task_id = sys.argv[1]
MAX_ATTEMPTS = 100                       
MAX_ACTIONS = 300                                                
sim = phyre.initialize_simulator([task_id], "ball")


def png(scene):
    rgb = (phyre.observations_to_float_rgb(scene) * 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(rgb).save(buf, format="PNG"); return base64.b64encode(buf.getvalue()).decode()


def emit(o):
    PROTO.write(json.dumps(o) + "\n"); PROTO.flush()


INTRO = ("PHYRE (official benchmark, single-ball tier). Place ONE red ball in the scene; after the placement the physics "
         "simulation runs. The task is solved when the green object touches a blue or purple object (and stays in contact for "
         "the required time). Colours: green = goal object, blue/purple = target, grey/black = static or dynamic scene objects, "
         "red = your ball. Action: x, y (ball centre, 0..1 from the left / bottom edge of the scene) and radius (0..1, mapped by "
         "PHYRE to its allowed ball size range). A placement that overlaps an object is INVALID_INPUT and does not count. "
         f"You have up to {MAX_ATTEMPTS} valid attempts; solving with fewer attempts scores higher (AUCCESS).")
attempts, actions, first_success = 0, 0, None
images = [png(sim.initial_scenes[0])]
text = f"{INTRO}\n\nTask {task_id}. Initial scene attached. Valid attempts used: 0/{MAX_ATTEMPTS}."
history = []
while True:
    emit({"kind": "player_request", "message": text, "images": images, "attempts": attempts})
    line = sys.stdin.readline()
    if not line: raise SystemExit("player stream closed")
    a = json.loads(line); actions += 1
    try:
        act = np.array([float(a["x"]), float(a["y"]), float(a["radius"])], dtype=np.float32)
        act = np.clip(act, 0.0, 1.0)
        res = sim.simulate_action(0, act, need_images=True, stride=60)
        status = res.status
    except Exception as e:
        status = None; err = str(e)
    if status is None:
        text = f"Malformed action ({err}); no simulation ran. Valid attempts used: {attempts}/{MAX_ATTEMPTS}."; images = []
    elif status.is_invalid():
        text = f"Placement x={act[0]:.3f}, y={act[1]:.3f}, r={act[2]:.3f}: INVALID_INPUT (overlaps an object; not counted). Valid attempts used: {attempts}/{MAX_ATTEMPTS}."
        images = []
    else:
        attempts += 1
        solved = status.is_solved()
        if solved and first_success is None: first_success = attempts
        frames = res.images
        pick = [frames[len(frames) // 2], frames[-1]] if frames is not None and len(frames) else []
        images = [png(f) for f in pick]
        text = (f"Attempt {attempts}: x={act[0]:.3f}, y={act[1]:.3f}, r={act[2]:.3f} -> {'SOLVED' if solved else 'NOT_SOLVED'}. "
                f"Attached: middle and last frame of the rollout. Valid attempts used: {attempts}/{MAX_ATTEMPTS}.")
    if first_success is not None or attempts >= MAX_ATTEMPTS or actions >= MAX_ACTIONS:
        emit({"kind": "terminal", "solved": first_success is not None, "firstSuccessAttempt": first_success, "attempts": attempts,
              "actions": actions, "lastMessage": text, "reason": "solved" if first_success else ("attempt_budget" if attempts >= MAX_ATTEMPTS else "action_cap")})
        break
