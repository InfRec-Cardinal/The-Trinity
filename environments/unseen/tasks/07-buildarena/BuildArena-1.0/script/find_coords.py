import pyautogui
from pynput.mouse import Controller
import time
import keyboard

def find_coordinates():
    pass                                                                                                 
    mouse = Controller()
    screen_width, screen_height = pyautogui.size()
    
    print("Move your mouse to desired position and press 'p' to get coordinates")
    print(f"Screen size: {screen_width}x{screen_height}")
    
    while True:
        if keyboard.is_pressed('p'):
            x, y = mouse.position
                                              
            frac_x = x / screen_width
            frac_y = y / screen_height
            print(f"\nAbsolute coordinates: ({x}, {y})")
            print(f"Fractional coordinates: ({frac_x:.3f}, {frac_y:.3f})")
            time.sleep(0.5)                           
        elif keyboard.is_pressed('q'):
            print("\nQuitting coordinate finder")
            break
        
if __name__ == "__main__":
    find_coordinates()
