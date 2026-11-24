                                                                                                                 
import sys, time, Quartz
from Quartz.CoreGraphics import CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap, kCGEventMouseMoved, kCGMouseButtonLeft

def zoom(lines, at=(735, 500)):
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventMouseMoved, at, kCGMouseButtonLeft)); time.sleep(0.2)
    step = 1 if lines > 0 else -1
    for _ in range(abs(int(lines))):
        CGEventPost(kCGHIDEventTap, Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitLine, 1, step))
        time.sleep(0.03)

if __name__ == "__main__":
    zoom(int(sys.argv[1]))
