import pyautogui
import pyperclip
from pynput.mouse import Controller, Button
import csv
import time
import subprocess
import platform
import os

                           
if platform.system() == 'Darwin':         
    from Quartz.CoreGraphics import CGEventCreateMouseEvent, CGEventPost
    from Quartz.CoreGraphics import kCGHIDEventTap
    from Quartz.CoreGraphics import kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp
    from Quartz.CoreGraphics import kCGMouseButtonLeft

def windows_click(x, y):
    pass                                                 
    import win32api, win32con
                                    
    x = int(x)
    y = int(y)
                
    win32api.SetCursorPos((x, y))
    time.sleep(0.1)
           
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

def macos_click(x, y):
    pass                                                            
                
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.2)

                     
    click_down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, click_down)
    time.sleep(0.02)

                   
    click_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, click_up)

def os_click(x, y):
    pass                                                                                             
    if platform.system() == 'Darwin':         
        macos_click(x, y)
    else:           
        windows_click(x, y)

def windows_focus_window(window_name):
    pass                                                     
    import win32gui
    def _window_enum_callback(hwnd, wildcard):
        if str(wildcard).lower() in str(win32gui.GetWindowText(hwnd)).lower():
            win32gui.SetForegroundWindow(hwnd)
            return True
    try:
        win32gui.EnumWindows(_window_enum_callback, window_name)
    except Exception as e:
        raise RuntimeError(f"Warning: Could not focus window '{window_name}'. Error: {e}")
        return False
    return True

def macos_focus_window(window_name):
    pass                                                                     
    script_check = f"""
    tell application "System Events"
        count (every process whose name is "{window_name}")
    end tell
    """
    result = subprocess.run(["osascript", "-e", script_check], capture_output=True, text=True)
    if result.stdout.strip() == "0":
        raise RuntimeError(f"Warning: The specified window '{window_name}' does not exist. Please open the game window through Steam first.")
        return False

    script_focus = f"""
    tell application "System Events"
        set frontmost of the first application process whose name is "{window_name}" to true
    end tell
    """
    subprocess.run(["osascript", "-e", script_focus])
    return True

def focus_window(window_name):
    pass                                                                                        
    if platform.system() == 'Darwin':         
        return macos_focus_window(window_name)
    else:           
        return windows_focus_window(window_name)

def click_fractional_position(fraction_xy: tuple, debug: bool = False):
    pass                                                       
    fraction_x, fraction_y = fraction_xy
    screen_width, screen_height = pyautogui.size()
    x = int(screen_width * fraction_x)
    y = int(screen_height * fraction_y)
    if debug:   
        print(f"Clicking at: ({x}, {y}) - fractional: ({fraction_x:.3f}, {fraction_y:.3f})")
    os_click(x, y)

def wait(seconds: float):
    pass                                    
    time.sleep(seconds)

def select_all():
    pass            
    if platform.system() == 'Darwin':
        pyautogui.hotkey("command", "a")
    else:
        pyautogui.hotkey("ctrl", "a")

def copy_text():
    pass                          
    select_all()
    time.sleep(0.2)                                          
    if platform.system() == 'Darwin':
        pyautogui.hotkey("command", "c")
        time.sleep(0.2)                                        
    else:
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)                                        
    return pyperclip.paste()

def save_to_csv(text, output_file: str):
    pass                                                                    
    with open(output_file, "a", newline="", encoding='utf-8') as file:
        writer = csv.writer(file)
        for line in text.splitlines():
            row = [item.strip() for item in line.split(",")]
            writer.writerow(row)

def delete_text(num: int):
    pass             
    for i in range(num):
        pyautogui.press("backspace")
        time.sleep(0.01)

def input_text(text: str):
    pass            
    pyautogui.typewrite(text, interval=0)
    time.sleep(0.1 * len(text))

def activate_lua_script():
    pass                         
    pyautogui.hotkey("ctrl", "l")

def deactivate_lua_script():
    pass                           
    pyautogui.hotkey("ctrl", "l")

def start_simulation():
    pass                      
    pyautogui.press("space")

def stop_simulation():
    pass                     
    pyautogui.press("space")

def run_simulation_sequence(machine_name: str, output_dir: str, duration: float, set_ground: bool = False):
    pass                                              
                                                        
                                 
                             
                 
                                                     
                               
                                  
                   
                                                     
                       
                                                                            
                                                           
                                            
                         
                      
                      
                    
                     
       
    from config import (POS_OPEN_FOLDER, POS_ENTER_NAME, POS_OPEN_MACHINE, 
                       POS_LOG_WINDOW, POS_EMPTY_SPACE, POS_START_SIMU, POS_DELETE, POS_CONFIRM, POS_SET_GROUND)
    
                             
    csv_file = f"{output_dir}/simulation_log_{machine_name}.csv"

                               
    if os.path.exists(csv_file):
        os.remove(csv_file)
    
    print(f"Starting simulation sequence for machine: {machine_name}")
    print(f"Duration: {duration} seconds")
    print(f"Output CSV: {csv_file}")
    
                                                               
    focus_window("Besiege")
    wait(1.0)
    
                                        
    print("Step 1: Clicking Open Folder...")
    click_fractional_position(POS_OPEN_FOLDER)
    wait(1.0)
    
                                    
    print("Step 2: Clicking Enter Name frame...")
    click_fractional_position(POS_ENTER_NAME)
    wait(1.0)
    
                        
    print("Step 3: Selecting all text...")
    select_all()
    wait(0.2)
    
                                              
    print("Step 4: Deleting text...")
    delete_text(2)
    wait(0.2)
    
                                   
    print(f"Step 5: Typing machine name: {machine_name}")
    input_text(machine_name)
    wait(1.0)
    
                                         
    print("Step 6: Clicking Open Machine...")
    click_fractional_position(POS_OPEN_MACHINE)
    wait(3.0)

    if set_ground:
        print("Step 6: Clicking Set Ground...")
        click_fractional_position(POS_SET_GROUND)
        wait(0.5)
    
                          
    print("Step 7: Activating Lua script...")
    activate_lua_script()
    wait(0.5)
    
                                                         
    print("Step 8: Starting simulation...")
    start_time = time.time()
    click_fractional_position(POS_START_SIMU)
    wait(0.5)
    
                              
    print("Step 9: Clicking Log Window...")
    click_fractional_position(POS_LOG_WINDOW)
    wait(0.5)
    
                                                                
    print(f"Step 10: Starting periodic logging every 1 seconds for {duration} seconds...")

                      
    click_fractional_position(POS_LOG_WINDOW)
    log_text = copy_text()
    
                                
    save_to_csv(log_text, csv_file)
    
    last_log_time = start_time
    while (time.time() - start_time) < duration:
        current_time = time.time()
        
                             
        if (current_time - last_log_time) >= 1.0:
            
                              
            click_fractional_position(POS_LOG_WINDOW)
            log_text = copy_text()
            
                                        
            save_to_csv(log_text, csv_file)
            
            last_log_time = current_time
    
                              
    print("Step 11: Stopping simulation...")
    click_fractional_position(POS_START_SIMU)
    wait(0.5)

                                                   
    print("Step 12: Final log capture...")
    click_fractional_position(POS_LOG_WINDOW)
    wait(0.5)
    final_log_text = copy_text()
    
    save_to_csv(final_log_text, csv_file)
    
                                
    print("Step 13: Clicking Empty Space...")
    click_fractional_position(POS_EMPTY_SPACE)
    wait(0.5)
    
                             
    print("Step 14: Deactivating Lua script...")
    deactivate_lua_script()
    wait(0.5)

                             
    print("Step 15: Cleaning CSV file...")
    clean_simulation_csv(csv_file)
    wait(0.5)
    
                           
    print("Step 16: Clicking Delete...")
    click_fractional_position(POS_DELETE)
    wait(0.5)
    
                            
    print("Step 17: Clicking Confirm...")
    click_fractional_position(POS_CONFIRM)
    wait(0.5)
    
    print(f"Simulation sequence completed! Log saved to: {csv_file}")

    return csv_file

def clean_simulation_csv(csv_file_path: str, output_file_path: str = None):
    pass                                        
                                                                      
                                          
                                                                 
    
         
                                                 
                                                                                      
       
    if output_file_path is None:
        output_file_path = csv_file_path
    
                                 
    rows = []
    seen_rows = set()
    
    with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
                             
            if not row:
                continue
            
                                               
            if len(row) < 2:
                continue

                                                          
            if row[-1].strip().endswith(("-", ".", ",")):
                continue
            
                                                             
            try:                
                                                                        
                row_key = tuple(row)
                
                                                           
                if row_key in seen_rows:
                    continue
                
                seen_rows.add(row_key)
                rows.append(row)
                
            except (ValueError, IndexError):
                                                                       
                continue
    
                                                            
    rows.sort(key=lambda x: float(x[0]))
    
                            
    with open(output_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in rows:
            writer.writerow(row)
    
    print(f"CSV cleaned: {len(rows)} unique rows written to {output_file_path}")
    return len(rows)

def main():
    pass                                                                 
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Run Besiege simulation sequence')
    parser.add_argument('--name', required=True, help='Machine name to load')
    parser.add_argument('--output_dir', required=True, help='Output directory for logs')
    parser.add_argument('--duration', type=float, required=True, help='Simulation duration in seconds')
    parser.add_argument('--window_name', default='Besiege', help='Name of the Besiege window to focus')
    args = parser.parse_args()

                                    
    os.makedirs(args.output_dir, exist_ok=True)
    
                                   
    print(f"Focusing on window: {args.window_name}")
    if not focus_window(args.window_name):
        raise RuntimeError(f"Failed to focus window '{args.window_name}'. Please make sure Besiege is running.")
        return
    
    wait(1.0)                                 
    
                                 
    try:
        csv_file = run_simulation_sequence(args.name, args.output_dir, args.duration)
    except KeyboardInterrupt:
        raise KeyboardInterrupt("\nSimulation interrupted by user")
    except Exception as e:
        print(f"Error during simulation: {e}")
        raise

if __name__ == "__main__":
    main()
