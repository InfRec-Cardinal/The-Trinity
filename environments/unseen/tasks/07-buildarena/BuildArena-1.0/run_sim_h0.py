                                                                                

                                                                                           
                                                                                      
                                                                                                           
                                                                             
                                                                                                         
                                                                                                            
                                 
                                                                       
                                                                                                               
                                                                                                               
                                                                                    
                                                                                                             
                                     
                                                                                                        
                                                                
                                                                                                       
                                                                                                                    
                                                                                   
                                                                                  
   
import atexit
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTSOURCE = os.path.join(os.path.dirname(HERE), "tools", "inputsource")

                                                               
_previous = subprocess.run([INPUTSOURCE, "get"], capture_output=True, text=True).stdout.strip()
subprocess.run([INPUTSOURCE, "set", "com.apple.keylayout.ABC"], check=True, capture_output=True)
if _previous and _previous != "com.apple.keylayout.ABC":
    atexit.register(lambda: subprocess.run([INPUTSOURCE, "set", _previous], capture_output=True))

                                                                                             
import pyautogui              
import gui_probe              
import simulation.operations as ops              

_official_delete_text = ops.delete_text


def delete_text(num: int):
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    _official_delete_text(num)


ops.delete_text = delete_text

                                                                                                          
                                                                                                         
                                                                                                        
_official_copy_text = ops.copy_text


def _line_time(line):
    try:
        return float(line.split(",", 1)[0])
    except ValueError:
        return None


_SIM_START = {"t": None}
_official_click = ops.click_fractional_position


def sim_state():
    pass                                                                                                       
    from PIL import Image
    shot = os.path.join(HERE, "datacache", "_play_icon_probe.png")
    subprocess.run(["screencapture", "-x", "-R", "117,78,24,24", shot], check=True)
    px = list(Image.open(shot).convert("RGB").getdata())
    red = sum(1 for r, g, b in px if r > 150 and g < 90)
    green = sum(1 for r, g, b in px if g > 140 and r < 120)
    return "running" if green > 100 else "build" if red > 100 else "unknown"


def click_fractional_position(fraction_xy, debug=False):
                                                                                                              
                                                                                                       
    from config import POS_START_SIMU
    _guard_user()
    if tuple(fraction_xy) != tuple(POS_START_SIMU):
        return _official_click(fraction_xy, debug)
    before = sim_state()
    want = "build" if before == "running" else "running"
    for _ in range(4):
        _official_click(fraction_xy, debug)
        time.sleep(0.7)
        if sim_state() == want:
            break
    else:
        raise RuntimeError(f"play/stop click did not reach state {want}")
    if want == "running" and _SIM_START["t"] is None:
        _SIM_START["t"] = time.time()


def reset_to_build_mode():
    pass                                                                                                          
    from config import POS_START_SIMU
    ops.focus_window("Besiege")
    time.sleep(1.0)
    if sim_state() == "running":
        click_fractional_position(POS_START_SIMU)
    if lua_panel_open():
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.6)
    ensure_free_build()
                                                                                                
    from config import POS_CONFIRM
    for _ in range(4):
        sc = gui_probe.scene()
        if sc == "load_dialog":
            ops.os_click(1254, 178)                                                         
        elif sc == "destroy_dialog":
            ops.click_fractional_position(POS_CONFIRM)                                                    
        else:
            return
        time.sleep(1.0)
    raise RuntimeError("could not return Besiege to a clean build scene")


def free_build_on():
    r, g, b = _mean_rgb("1050,70,50,40")                                                                      
    return r > 150 and g < 90


def ensure_free_build():
    pass                                                                                                       
                                                                                                        
                                                                                                            
    if os.environ.get("BUILDARENA_FREE_BUILD") != "1":
        return
    for _ in range(3):
        if free_build_on():
            return
        ops.os_click(1075, 90)
        time.sleep(0.8)
        ops.os_click(1300, 160)                                                                            
        time.sleep(0.5)
    if not free_build_on():
        raise RuntimeError("could not switch on Free Build Mode")


def _mean_rgb(rect):
    from PIL import Image
    shot = os.path.join(HERE, "datacache", "_overlay_probe.png")
    subprocess.run(["screencapture", "-x", "-R", rect, shot], check=True)
    px = list(Image.open(shot).convert("RGB").getdata())
    return tuple(sum(c[i] for c in px) // len(px) for i in range(3))


ops.click_fractional_position = click_fractional_position


                                                                                                                  
                                                                                                        
def _frontmost():
    from AppKit import NSWorkspace
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.localizedName() if app else ""


def _idle_seconds():
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "HIDIdleTime" in line:
            return int(line.split("=")[-1].strip()) / 1e9
    return 1e9


def _guard_user():
    if _frontmost() == "Besiege":
        return
    print(f"[run_sim_h0] {_frontmost()!r} is in front (user active): waiting for 60 s idle", flush=True)
    while _idle_seconds() < 60:
        time.sleep(5)
    _official_focus("Besiege")
    time.sleep(1.0)


_official_focus = ops.focus_window
_official_os_click = ops.os_click


def _guarded_os_click(x, y):
    _guard_user()
    _official_os_click(x, y)


ops.os_click = _guarded_os_click



def copy_text():
    import pyperclip
    from config import POS_LOG_WINDOW
                                                                                                          
                                                                                                              
                                                                                                
    text = ""
    for attempt in range(5):
        pyperclip.copy("")                                                                                  
        pyautogui.hotkey("command", "a")
        time.sleep(0.03)
        pyautogui.hotkey("command", "c")
        time.sleep(0.15)
        text = pyperclip.paste()
        if text.strip():
            break
        _official_click(POS_LOG_WINDOW)
        time.sleep(0.1)
    first = next((t for t in map(_line_time, text.splitlines()) if t is not None), None)
    elapsed = time.time() - _SIM_START["t"] if _SIM_START["t"] is not None else None
    if os.environ.get("BUILDARENA_DEBUG_COPY"):
        with open(os.environ["BUILDARENA_DEBUG_COPY"], "a") as f:
            f.write(f"first={first} elapsed={elapsed} lines={len(text.splitlines())}\n")
    if first is not None and elapsed is not None and first > elapsed + 1.5:
        return ""                                                                           
    kept, last = [], None
    for line in text.splitlines():
        t = _line_time(line)
        if t is not None and last is not None and t > last + 1e-9:
            break
        if t is not None:
            last = t
        kept.append(line)
    return "\n".join(kept)


ops.copy_text = copy_text


                                                                                                            
                                                                                                          
                                                                                                             
def lua_panel_open():
    pass                                                                                                          
                                                                                            
    import numpy as np
    from PIL import Image
    shot = os.path.join(HERE, "datacache", "_lua_panel_probe.png")
    subprocess.run(["screencapture", "-x", "-R", "130,190,150,120", shot], check=True)
    a = np.asarray(Image.open(shot).convert("RGB")).astype(int)
    k = a.shape[0] / 120.0
    band = lambda y0, h: a[int(y0 * k):int((y0 + h) * k)]
    red = lambda b: float(((b[..., 0] > 120) & (b[..., 1] < 70) & (b[..., 2] < 90)).mean())
    buttons, gap1, gap2 = band(5, 12), band(29, 6), band(109, 6)                                    
    dark = lambda b: b.reshape(-1, 3).mean(0).max() < 100
    return red(buttons) > 0.3 and red(gap1) < 0.1 and red(gap2) < 0.1 and dark(gap1) and dark(gap2)


def _ensure_lua_panel(want_open):
    for _ in range(4):
        if lua_panel_open() == want_open:
            return
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.6)
    raise RuntimeError(f"could not set the Lua panel {'open' if want_open else 'closed'}")


def _ensure_log_window_right():
    pass                                                                                                         
                                                                                                                    
                                                                                             
    strip, default = _mean_rgb("1215,300,140,300"), _mean_rgb("340,300,380,300")
    if max(strip) < 90:
        return
    if max(default) < 90:                                                                                      
        import drag_window
        drag_window.drag(400, 155, 1270, 146)
        time.sleep(0.5)
    if max(_mean_rgb("1215,300,140,300")) >= 90:
        raise RuntimeError("Lua Log window is not at the right edge of the game window")


def _activate_lua():
    _ensure_lua_panel(True)
    _ensure_log_window_right()


ops.activate_lua_script = _activate_lua
ops.deactivate_lua_script = lambda: _ensure_lua_panel(False)


                                                                                                                 
def _with_retry(sequence):
    def run(machine_name, output_dir, duration, *args, **kwargs):
                                                                                                              
                                                                         
        rec = os.path.join(recorder.RECORDINGS_DIR, machine_name)
        base = max([int(d.split("-")[1]) for d in os.listdir(rec) if d.startswith("attempt-") and d.split("-")[1].isdigit()]
                   or [0]) if os.path.isdir(rec) else 0
        for attempt in range(1, 4):
            os.environ["BUILDARENA_ATTEMPT"] = str(base + attempt)
            _SIM_START["t"] = None
            try:
                reset_to_build_mode()
                csv_file = sequence(machine_name, output_dir, duration, *args, **kwargs)
            except Exception as exc:                                                            
                err_dir = os.path.join(recorder.RECORDINGS_DIR, machine_name, f"attempt-{base + attempt}")
                os.makedirs(err_dir, exist_ok=True)
                subprocess.run(["screencapture", "-x", "-o", os.path.join(err_dir, "error-screen.png")])
                with open(os.path.join(err_dir, "error.txt"), "w") as f:
                    f.write(repr(exc))
                print(f"[run_sim_h0] {machine_name}: attempt {attempt} failed: {exc!r}; retrying", flush=True)
                continue
            rows = [l for l in open(csv_file, encoding="utf-8").read().splitlines() if _line_time(l) is not None]
            if rows:
                return csv_file
            print(f"[run_sim_h0] {machine_name}: no log rows in attempt {attempt}; retrying", flush=True)
        raise RuntimeError(f"simulation of {machine_name} failed in 3 attempts")
    return run



                                                                                                                
                                                                                                           
                                                                            
def _scene():
    return gui_probe.scene()


def camera_zoom():
    pass                                                                                                      
                                                                                    
    lines = int(os.environ.get("BUILDARENA_ZOOM", "0"))
    if lines:
        import zoom_camera
        zoom_camera.zoom(lines)
        time.sleep(0.3)


def _until(check, action, what, tries=4, pause=1.0):
    for _ in range(tries):
        if check():
            return
        action()
        time.sleep(pause)
    if not check():
        raise RuntimeError(f"GUI step failed: {what}")


def run_simulation_sequence_verified(machine_name, output_dir, duration, set_ground=False):
    from config import (POS_OPEN_FOLDER, POS_ENTER_NAME, POS_OPEN_MACHINE, POS_LOG_WINDOW, POS_EMPTY_SPACE,
                        POS_START_SIMU, POS_DELETE, POS_CONFIRM, POS_SET_GROUND)
    c = ops.click_fractional_position
    csv_file = f"{output_dir}/simulation_log_{machine_name}.csv"
    if os.path.exists(csv_file):
        os.remove(csv_file)
    print(f"Starting simulation sequence for machine: {machine_name} (duration {duration}s)", flush=True)
    ops.focus_window("Besiege"); ops.wait(1.0)
                                                                   
    _until(lambda: _scene() == "load_dialog", lambda: c(POS_OPEN_FOLDER), "open Load Machine dialog")
    c(POS_ENTER_NAME); ops.wait(1.0)
    pyautogui.hotkey("ctrl", "a"); ops.wait(0.2)                                                             
    ops.delete_text(2); ops.wait(0.2)                                                                               
    ops.input_text(machine_name); ops.wait(1.0)
    c(POS_OPEN_MACHINE); ops.wait(3.0)
    _until(lambda: _scene() != "load_dialog", lambda: c(POS_OPEN_MACHINE), "load the machine", pause=2.0)
    if set_ground:
        c(POS_SET_GROUND); ops.wait(0.5)
    camera_zoom()                                                                                      
                                                                                     
    ops.activate_lua_script(); ops.wait(0.5)
    start_time = time.time()
    c(POS_START_SIMU); ops.wait(0.5)
    c(POS_LOG_WINDOW); ops.wait(0.5)
    c(POS_LOG_WINDOW)
    ops.save_to_csv(ops.copy_text(), csv_file)
    last = start_time
    while time.time() - start_time < duration:
        now = time.time()
        if now - last >= 0.5:                                                                                 
            c(POS_LOG_WINDOW)
            ops.save_to_csv(ops.copy_text(), csv_file)
            last = now
                                                   
    c(POS_START_SIMU); ops.wait(0.5)
    c(POS_LOG_WINDOW); ops.wait(0.5)
    ops.save_to_csv(ops.copy_text(), csv_file)
                                                                                       
    c(POS_EMPTY_SPACE); ops.wait(0.5)
    ops.deactivate_lua_script(); ops.wait(0.5)
    ops.clean_simulation_csv(csv_file); ops.wait(0.5)
                                                             
    _until(lambda: _scene() == "destroy_dialog", lambda: c(POS_DELETE), "open Destroy dialog")
    _until(lambda: _scene() != "destroy_dialog", lambda: c(POS_CONFIRM), "confirm Destroy")
    print(f"Simulation sequence completed! Log saved to: {csv_file}", flush=True)
    return csv_file


ops.run_simulation_sequence = run_simulation_sequence_verified
import recorder              
recorder.install()
ops.run_simulation_sequence = _with_retry(ops.run_simulation_sequence)

                                              
import agents              
from h0_client import H0ChatCompletionClient              
agents.model_clients["h0-opus-5"] = H0ChatCompletionClient()

def load_level(name):
    pass                                                                                                        
                                                                                                          
    from config import POS_ENTER_NAME
    ops.focus_window("Besiege"); time.sleep(1.0)
    reset_to_build_mode()
    ops.os_click(143, 158); time.sleep(1.2)                                                 
    ops.os_click(177, 200); time.sleep(2.0)                                    
    if gui_probe.scene() != "load_dialog":
        raise RuntimeError("Load Level dialog did not open")
    ops.click_fractional_position(POS_ENTER_NAME); time.sleep(0.8)
    pyautogui.hotkey("ctrl", "a"); time.sleep(0.2)
    for _ in range(4):
        pyautogui.press("backspace"); time.sleep(0.02)
    ops.input_text(name); time.sleep(0.8)
    ops.os_click(902, 249); time.sleep(8.0)                   
    if gui_probe.scene() == "load_dialog":
        raise RuntimeError(f"level {name} did not load")
    ops.os_click(323, 149); time.sleep(1.0)                                           
    print(f"[run_sim_h0] level {name} loaded", flush=True)


if __name__ == "__main__":
    if "--load-level" in sys.argv:
        load_level(sys.argv[sys.argv.index("--load-level") + 1])
    elif "--machine" in sys.argv:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--machine", required=True)
        ap.add_argument("--category", required=True, choices=["transport", "support", "lift"])
        ap.add_argument("--level", required=True, choices=["soft", "medium", "hard"])
        a = ap.parse_args()
        import importlib
        mod = importlib.import_module(f"simulation.simulation_{a.category}")
        print(mod.main(a.machine, a.level))
    else:
        import runpy
        sys.argv[0] = os.path.join(HERE, "script", "run_simulation.py")
        runpy.run_module("script.run_simulation", run_name="__main__")
