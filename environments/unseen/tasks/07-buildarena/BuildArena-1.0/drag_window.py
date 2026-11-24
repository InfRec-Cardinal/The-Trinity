                                                          
import sys, time
from Quartz.CoreGraphics import (CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap, kCGEventMouseMoved,
                                 kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventLeftMouseDragged, kCGMouseButtonLeft)

def drag(x0, y0, x1, y1, steps=30):
    post = lambda ev, p: CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, ev, p, kCGMouseButtonLeft))
    post(kCGEventMouseMoved, (x0, y0)); time.sleep(0.2)
    post(kCGEventLeftMouseDown, (x0, y0)); time.sleep(0.2)
    for i in range(1, steps + 1):
        post(kCGEventLeftMouseDragged, (x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)); time.sleep(0.02)
    time.sleep(0.2); post(kCGEventLeftMouseUp, (x1, y1)); time.sleep(0.3)

if __name__ == "__main__":
    drag(*map(float, sys.argv[1:5]))
