                                                                                   

                                                                                                      
                                                                                                   
                                                                                                    
                                                                                                                                                                      
                                                                
   
import json
import os
import subprocess
import threading
import time

import Quartz

RECORDINGS_DIR = os.environ.get(
    "BUILDARENA_RECORDINGS", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recordings"))


def besiege_window():
    pass                                                                                      
    for w in Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, Quartz.kCGNullWindowID):
        if w.get("kCGWindowOwnerName") == "Besiege" and w.get("kCGWindowLayer") == 0:
            b = w.get("kCGWindowBounds")
            return int(w.get("kCGWindowNumber")), {k: float(b[k]) for k in ("X", "Y", "Width", "Height")}
    return None, None


def window_shot(path):
    wid, _ = besiege_window()
    if wid is None:
        return False
    return subprocess.run(["screencapture", "-x", "-o", "-l", str(wid), path]).returncode == 0


def start_video(path, seconds):                                                              
    _, b = besiege_window()
    if b is None:
        return None
    rect = f"{int(b['X'])},{int(b['Y'])},{int(b['Width'])},{int(b['Height'])}"
    return subprocess.Popen(["screencapture", "-x", "-v", "-V", str(int(seconds)), "-R", rect, path],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


WINCAP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "wincap")


def start_window_video(path, fps=30):
    pass                                                                                                
    wid, _ = besiege_window()
    if wid is None:
        return None
    proc = subprocess.Popen([WINCAP, str(wid), path, str(fps)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = proc.stdout.readline()                                                 
    if not line.startswith("recording"):
        proc.kill()
        raise RuntimeError(f"window recorder did not start: {line.strip()} {proc.stderr.read()[:300]}")
    return proc


def stop_window_video(proc):
    proc.send_signal(subprocess.signal.SIGINT)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False
    return proc.returncode == 0


def wrap(run_simulation_sequence):
    def recorded(machine_name, output_dir, duration, *args, **kwargs):
        out = os.path.join(RECORDINGS_DIR, machine_name, f"attempt-{os.environ.get('BUILDARENA_ATTEMPT', '1')}")
        os.makedirs(out, exist_ok=True)
        meta = {"machine_name": machine_name, "output_dir": output_dir, "duration": duration,
                "recorder": "tools/wincap (ScreenCaptureKit, Besiege window only, 30 fps)"}
        window_shot(os.path.join(out, "01-before.png"))
        video = start_window_video(os.path.join(out, "simulation.mov"))
        meta["video_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            result = run_simulation_sequence(machine_name, output_dir, duration, *args, **kwargs)
            meta["simulation_returned_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        finally:
            ok = stop_window_video(video) if video is not None else False
            meta["video_stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            meta["video_ok"] = ok
            window_shot(os.path.join(out, "02-after.png"))
            with open(os.path.join(out, "recording.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=1)
        if not ok:
            raise RuntimeError(f"recording of {machine_name} is incomplete")
        return result
    return recorded


def install():
    pass                                                                      
    import simulation.operations as ops
    if not getattr(ops.run_simulation_sequence, "_h0_recorded", False):
        ops.run_simulation_sequence = wrap(ops.run_simulation_sequence)
        ops.run_simulation_sequence._h0_recorded = True
