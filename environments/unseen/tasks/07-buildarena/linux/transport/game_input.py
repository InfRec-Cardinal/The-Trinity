                                                                               
import os
import time

if os.environ.get('DISPLAY', '').split('.')[0] != ':97':
    raise RuntimeError('Set DISPLAY=:97; real-desktop input is prohibited')

import pyautogui as gui
from Xlib import X, display


def focus_game():
    d = display.Display(':97')
    matches = []
    def visit(parent):
        for w in parent.query_tree().children:
            if w.get_wm_name() == 'Besiege' and w.get_attributes().map_state == X.IsViewable:
                matches.append(w)
            visit(w)
    visit(d.screen().root)
    if len(matches) != 1:
        raise RuntimeError('Besiege window missing or ambiguous on isolated display')
    matches[0].set_input_focus(X.RevertToParent, X.CurrentTime)
    d.sync()
    d.close()


def click(x, y):
    focus_game()
    gui.moveTo(x, y)
    time.sleep(.15)
                                                                         
                                                                              
    gui.mouseDown(_pause=False)
    time.sleep(.06)
    gui.mouseUp(_pause=False)
    time.sleep(.2)


def key(*keys):
    focus_game()
    for k in keys:
        gui.keyDown(k)
    time.sleep(.25)
    for k in reversed(keys):
        gui.keyUp(k)
    time.sleep(.2)
