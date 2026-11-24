                                                                                                             
                                                                                                         
                                                                             
import time
import pyautogui
from Quartz.CoreGraphics import CGEventCreateKeyboardEvent, CGEventPost, CGEventSetFlags, kCGHIDEventTap, kCGEventFlagMaskShift

SHIFTED = {"_": 27}                  

def type_text(text, interval=0.05):
    for ch in text:
        if ch in SHIFTED:
            for down in (True, False):
                ev = CGEventCreateKeyboardEvent(None, SHIFTED[ch], down)
                CGEventSetFlags(ev, kCGEventFlagMaskShift)
                CGEventPost(kCGHIDEventTap, ev)
                time.sleep(0.02)
        else:
            pyautogui.typewrite(ch, interval=0)
        time.sleep(interval)
