                                                

                                                                    
                                                                           
                                                                         
                                                                       
                                                                       

                                                                      
                                                                    
   
import base64
import importlib.util
import io
import json
import os
import random
import re

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_TOOLKIT = os.path.join(ROOT, "src", "toolkit")
ASSET = os.path.join(ROOT, "data", "asset")
INSTANCES_PATH = os.path.join(ROOT, "instances.json")
MAX_SIDE = int(os.environ.get("ACTIVIEW_MAX_SIDE", "1024"))


def _load_official_prompts():
    spec = importlib.util.spec_from_file_location(
        "actiview_official_prompts_config", os.path.join(SRC_TOOLKIT, "prompts_config.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load_official_prompts()

                                                                             
IMAGE_VIEWS = ["upperleft", "lowerleft", "upperright", "lowerright"]
SETTINGS = ["zoom", "shift-R", "shift-E", "shift-M", "shift-H"]
LEVEL_KEY = {"shift-E": "easy", "shift-M": "medium", "shift-H": "hard"}
STEP_CAP = {"zoom": 2, "shift-R": 5, "shift-E": 5, "shift-M": 5, "shift-H": 5}

_DATA = None


def load_data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(ASSET, "data.json")) as fr:
            _DATA = json.loads(fr.read())["data"]
    return _DATA


def image_path(d, k):
    pass                                                                            
    name = d["images"][k].split("/")[-1]
    return os.path.join(ASSET, "images" if k == 0 else "images_split", name)


def option_string(d):
                                                                               
    return '; '.join([chr(ord('A') + i) + f'. {op}' for i, op in enumerate(d['options'])])


def start_views():
    pass                                                                           

                                                                              
                                                                              
                                                                             
                                                 
       
    with open(os.path.join(ASSET, "shifting_level.json")) as fr:
        lv = json.loads(fr.read())
    n = len(load_data())
    rng = random.Random(1234)
    out = {"shift-R": [rng.randint(0, 3) for _ in range(n)]}
    for s, k in LEVEL_KEY.items():
        out[s] = lv[k]
        assert len(out[s]) == n
    return out


                                                                          
                                                                           
                                                                               
_P_DIGIT = re.compile(r'\d')
_P_STR = re.compile('upperleft|lowerleft|upperright|lowerright|left|right|upper|lower')
_STR_MAPPER = {"left": [1, 2], "right": [3, 4], "upper": [1, 3], "upper": [2, 4],              
               "upperleft": [1], "lowerleft": [2], "upperright": [3], "lowerright": [4]}


def parse_zoom_selection(g):
    pass                                                                   

                                                                               
                                                                               
                                                                            
                                                                      
                                                                
       
    _select, dropped = [], []
    if '.' in g:
        g = g.replace('.', ',')                           
    for _g in g.split(','):
        if _g == '':
            continue
        m = _P_DIGIT.match(_g)
        if m:
            try:
                _se = int(_g)
            except ValueError:
                dropped.append(_g)
                continue
            _select.append(_se)
        else:
            m = _P_STR.match(_g)
            if m:
                try:
                    _se = _STR_MAPPER[m.group()]
                except KeyError:
                    dropped.append(_g)
                    continue
                _select.extend(_se)
    _select = sorted(set(_select))
    dropped += [s for s in _select if not 1 <= s <= 4]
    return [s for s in _select if 1 <= s <= 4], dropped


_ANS_OPTIONS = ["A", "B", "C", "D", "E", "F", "G", "H", "Z"]


def official_pred_index(p, ops, y):
    pass                                                                          
    try:
        if "Answer:" in p:
            p = p.split('Answer:')[1].strip()
        p = _ANS_OPTIONS.index(p.split('.')[0])
    except Exception:
        if p.lower().strip() == ops[y].lower():
            p = y
        else:
            p = -1
    return p


                                                                           
LEGAL_ZOOM_SELECT = ("Part numbers to zoom into (1=upperleft, 2=lowerleft, 3=upperright, 4=lowerright), "
                     "comma-separated with no spaces, e.g. '1,3'. Official parser: each ','-token must start "
                     "with a digit (or a view word); anything else is ignored; nothing parsed = no zoom.")
LEGAL_SHIFT_DECISION = ("'Yes' = need more visual information (the next view in the official fixed order is added) "
                        "or 'No' = stop and answer. Only a reply equal to 'no' (case-insensitive) stops.")
LEGAL_ANSWER = ("The option letter, e.g. 'B' (or 'B. <option text>'). Official cal_acc: text before the first '.' "
                "must be a letter A-H (after an optional 'Answer:'), or the reply must equal the gold option text.")


def zoom_episode(d):
    pass                                                                  
                                                              
                                                                  
                                                                                
    img_placeholder = 'Image 1'
    msg = P.ZOOM_MANUAL_DECISION_TEMPLATES_CHAT.format(
        image=img_placeholder, num_splits=4, description_of_splits=P.DESC_4_SPLITS, question=d['question'])
    selection_raw = yield {"message": msg, "images": [image_path(d, 2)], "legal": LEGAL_ZOOM_SELECT}

                                                                                           
    _select, dropped = parse_zoom_selection(selection_raw)
    zoomed_images = ""
    images = [image_path(d, 1)]
    for i, _se in enumerate(_select):
        images.append(image_path(d, _se + 2))
        zoomed_images += f'<image{i+2}> is your selected {IMAGE_VIEWS[_se-1]} view. '
    msg = P.ZOOM_QA_TEMPLATES_CHAT.format(image='Image 1', zoomed_images=zoomed_images,
                                          question=d['question'], option=option_string(d))
    pred = yield {"message": msg, "images": images, "legal": LEGAL_ANSWER}
    return {"viewsUsed": [IMAGE_VIEWS[s - 1] for s in _select], "prediction": pred,
            "zoomSelectionRaw": selection_raw, "zoomSelection": _select, "droppedTokens": dropped}


def shift_episode(d, start_index):
    pass                                                                           
                                                                           
    view_order = IMAGE_VIEWS[start_index:] + IMAGE_VIEWS[:start_index]
    images, used_views, decisions = [], [], []
    img_str = ""
    i = 0
    while view_order:
        view = view_order.pop(0)
        view_idx = IMAGE_VIEWS.index(view)
        images.append(image_path(d, view_idx + 3))
        used_views.append(view_idx)
        img_str += f" image {i+1}, the {view} view,"
        msg = P.SHIFT_DECISION_TEMPLATES_CHAT.format(images=img_str, question=d['question'])
        generation = yield {"message": msg, "images": list(images), "legal": LEGAL_SHIFT_DECISION}
        decisions.append(generation)
        if generation.lower() == 'no':
            break
        i += 1
    msg = P.QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option_string(d))
    pred = yield {"message": msg, "images": list(images), "legal": LEGAL_ANSWER}
    return {"viewsUsed": [IMAGE_VIEWS[v] for v in used_views], "prediction": pred,
            "startView": IMAGE_VIEWS[start_index], "decisions": decisions}


def make_episode(inst):
    d = load_data()[inst["dataIndex"]]
    assert d["id"] == inst["questionId"], "instances.json does not match data.json"
    if inst["setting"] == "zoom":
        return d, zoom_episode(d)
    return d, shift_episode(d, inst["startView"])


def finish(inst, d, result, steps):
    y = d["answer"]
    p_idx = official_pred_index(result["prediction"], d["options"], y)
    rec = {"kind": "terminal", "correct": p_idx == y, "prediction": result["prediction"],
           "predictionIndex": p_idx, "gold": chr(ord('A') + y), "goldIndex": y,
           "goldText": d["options"][y], "setting": inst["setting"], "viewsUsed": result["viewsUsed"],
           "steps": steps, "id": inst["id"], "questionId": inst["questionId"]}
    for k, v in result.items():
        if k not in rec:
            rec[k] = v
    return rec


def png_b64(path, max_side=MAX_SIDE):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if max(w, h) > max_side:
        s = max_side / max(w, h)
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def load_instances():
    with open(INSTANCES_PATH) as fr:
        return json.load(fr)
