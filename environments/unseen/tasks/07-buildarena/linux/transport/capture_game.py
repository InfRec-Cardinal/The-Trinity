                                                                                   
import argparse
import json
from pathlib import Path
from Xlib import X, display
from PIL import Image


def capture(target, display_name=':97'):
    if display_name.split('.')[0] != ':97':
        raise RuntimeError('Only the dedicated :97 display is allowed')
    d = display.Display(display_name)
    root = d.screen().root
    matches = []

    def visit(parent):
        for w in parent.query_tree().children:
            try:
                if w.get_wm_name() == 'Besiege' and w.get_attributes().map_state == X.IsViewable:
                    matches.append(w)
                visit(w)
            except Exception:
                continue

    visit(root)
    if len(matches) != 1:
        raise RuntimeError(f'Expected one mapped Besiege window, found {len(matches)}')
    w = matches[0]
    geom = w.get_geometry()
                                                                                
                                                                               
    raw = w.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
    Image.frombytes('RGB', (geom.width, geom.height), raw.data, 'raw', 'BGRX').save(target)
    result = dict(display=display_name, window_id=hex(w.id), title=w.get_wm_name(),
                  width=geom.width, height=geom.height, path=str(Path(target).resolve()),
                  capture_method='XGetImage on game window drawable; no root capture')
    d.close()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    args = parser.parse_args()
    print(json.dumps(capture(args.output)))
