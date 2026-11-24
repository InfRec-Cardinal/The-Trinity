                                                                                                       

                                                                                                      
                                                                                                        
                                                                                                        
                                                                      
                                                                                                          
   
import os
import subprocess
import tempfile

import numpy as np

from PIL import Image, ImageStat

_SHOT = os.path.join(tempfile.gettempdir(), "besiege_probe.png")


def screen():
    subprocess.run(["screencapture", "-x", "-o", _SHOT], check=True)
    im = Image.open(_SHOT).convert("RGB")
    return im, im.width / 1470.0


def _crop(im, s, x, y, w, h):
    return im.crop((int(x * s), int(y * s), int((x + w) * s), int((y + h) * s)))


def _bright_frac(region, thr=200):
    a = np.asarray(region)
    return float((a.min(axis=2) > thr).mean()) if a.size else 0.0


def _dark(region, limit=110):
    return max(ImageStat.Stat(region).mean) < limit


def features(im=None, s=None, origin=(0, 0)):
    pass                                                                                                  
    if im is None:
        im, s = screen()
    ox, oy = origin
    c = lambda x, y, w, h: _crop(im, s, x - ox, y - oy, w, h)
    return {
        "workshop_blue": ImageStat.Stat(c(1090, 98, 140, 26)).mean,
        "check": _bright_frac(c(772, 522, 22, 22)),
        "cross": _bright_frac(c(671, 522, 22, 22)),
        "title": _bright_frac(c(680, 405, 110, 26)),
        "gap_bright": _bright_frac(c(712, 522, 44, 22)),
        "box_dark": _dark(c(592, 548, 40, 12)) and _dark(c(838, 548, 40, 12)) and _dark(c(712, 522, 44, 22)),
    }


def classify(f):
    r, g, b = f["workshop_blue"]
    if b > 120 and b > r + 40:
        return "load_dialog"
                                                                                                                
                                                                                                 
    if f["check"] > 0.04 and f["cross"] > 0.04 and f["title"] > 0.04 and f["gap_bright"] < 0.02 and f["box_dark"]:
        return "destroy_dialog"
    return "scene"


def scene():
    return classify(features())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:                                                                    
        for f in sys.argv[1:]:
            im = Image.open(f).convert("RGB")
            ft = features(im, im.width / 1262.0, (104, 35 - 0))
            print(f, classify(ft), {k: (round(v, 3) if isinstance(v, float) else v) for k, v in ft.items() if k != "workshop_blue"})
    else:
        print(features(), scene())
