                                                                           
                                                                      
                                                                                
                                                                                  
                                                                                 
                                                                               
                                                               

                                                                                 
                                                                            
                                                                      

        
                                                                               
                                                        
                                                                    
                                                         
                                                  
                            

                                                            
   

from __future__ import annotations

from collections import Counter

import numpy as np

try:
    from .representation import detect_background, parse_objects
except Exception:
    from representation import detect_background, parse_objects

DIR = {
    1: (0, -1),
    2: (0, 1),
    3: (-1, 0),
    4: (1, 0),
}                                      


def _board(frame):
    a = np.array(frame, dtype=np.int16)
    return a[-1] if a.ndim == 3 else a


def _click_play_diff(prev, cur):
    pass                                                                           
    raw = prev != cur
    play = raw.copy()
    play[:2, :] = False
    play[-2:, :] = False
    play[:, :1] = False
    play[:, -1:] = False
    return raw, play


def _bbox_touches_diff(bbox, diff):
    y0, x0, y1, x1 = bbox
    return bool(diff[y0 : y1 + 1, x0 : x1 + 1].any())


def _match_object_translation(prev_objs, cur_objs, exp_drow, exp_dcol, diff):
    pass                                                                             
                                                                               
    for oc in cur_objs:
                                                                               
                                                                      
        if oc.size < 4:
            continue
        for op in prev_objs:
            if (
                op.color == oc.color
                and op.size == oc.size
                and op.shape_hash == oc.shape_hash
            ):
                if not (
                    _bbox_touches_diff(op.bbox, diff)
                    or _bbox_touches_diff(oc.bbox, diff)
                ):
                    continue
                drow = oc.centroid[0] - op.centroid[0]
                dcol = oc.centroid[1] - op.centroid[1]
                if (
                    abs(drow - exp_drow) < 1.6
                    and abs(dcol - exp_dcol) < 1.6
                    and (abs(drow) + abs(dcol)) > 0.4
                ):
                    return True
    return False


def _multicolor_body_floor_swap(prev, cur):
    pass                                                                     

                                                                                  
                                                                             
                                                                              
                                                  
       
    changed = prev != cur
    if not changed.any():
        return False

    pair_counts = Counter(zip(prev[changed].tolist(), cur[changed].tolist()))
    colors = {c for pair in pair_counts for c in pair}
    for anchor in colors:
        out_others = {
            b
            for (a, b), n in pair_counts.items()
            if a == anchor and b != anchor and n >= 2
        }
        in_others = {
            a
            for (a, b), n in pair_counts.items()
            if b == anchor and a != anchor and n >= 2
        }
        shared = out_others & in_others
        if len(shared) >= 2:
            out_total = sum(
                n for (a, b), n in pair_counts.items() if a == anchor and b in shared
            )
            in_total = sum(
                n for (a, b), n in pair_counts.items() if b == anchor and a in shared
            )
            if min(out_total, in_total) >= 8:
                return True
    return False


def classify_delta(prev, cur, action_id):
    diff = prev != cur
    n = int(diff.sum())
    if n == 0:
        return {"vote": "STATIC", "changed": 0, "action": action_id}
    H, W = prev.shape
    area_frac = n / (H * W)
    ys, xs = np.where(diff)
    bbox = (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))

    if action_id in DIR:
        dx, dy = DIR[action_id]
        exp_drow, exp_dcol = dy, dx
                                                                               
                                                                          
        bg_p, bg_c = detect_background(prev), detect_background(cur)
        prev_objs = parse_objects(prev, bg_p)
        cur_objs = parse_objects(cur, bg_c)
        if _match_object_translation(
            prev_objs, cur_objs, exp_drow, exp_dcol, diff
        ) or _multicolor_body_floor_swap(prev, cur):
            vote = "AVATAR_NAV"
        elif area_frac > 0.10:
            vote = "BOARD_TRANSFORM"
        else:
            vote = "CURSOR_SELECT"
    elif action_id == 6:
        raw_diff, play_diff = _click_play_diff(prev, cur)
        raw_n = int(raw_diff.sum())
        play_n = int(play_diff.sum())
        if play_n == 0:
            return {
                "vote": "STATIC",
                "changed": 0,
                "raw_changed": raw_n,
                "action": action_id,
            }
        ys, xs = np.where(play_diff)
        bbox = (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))
        n = play_n
        area_frac = play_n / (H * W)
        vote = "CLICK_TOGGLE" if area_frac < 0.25 else "BOARD_TRANSFORM"
    else:
        vote = "CURSOR_SELECT" if area_frac < 0.10 else "BOARD_TRANSFORM"

    return {
        "vote": vote,
        "changed": n,
        "bbox": bbox,
        "area_frac": round(area_frac, 4),
        "action": action_id,
    }


class SchemaClassifier:
    def __init__(self):
        self.votes = Counter()
        self.steps = 0
        self.evidence = []

    def observe(self, prev_frame, cur_frame, action_id):
        prev, cur = _board(prev_frame), _board(cur_frame)
        if prev.shape != cur.shape:
            return None
        ev = classify_delta(prev, cur, action_id)
        if ev["vote"] != "STATIC":
            self.votes[ev["vote"]] += 1
        self.steps += 1
        self.evidence.append(ev)
        return ev

    def label(self):
        if not self.votes:
            return ("UNKNOWN", 0.0)
        total = sum(self.votes.values())
        top, cnt = self.votes.most_common(1)[0]
        return (top, round(cnt / total, 3))

    def report(self):
        lab, conf = self.label()
        return {
            "schema": lab,
            "confidence": conf,
            "votes": dict(self.votes),
            "steps": self.steps,
        }


if __name__ == "__main__":
    H = W = 32

    def blank():
        return np.zeros((H, W), dtype=np.int16)

                                                         
    a = blank()
    a[10:12, 10:12] = 3
    b = blank()
    b[10:12, 11:13] = 3
    sc = SchemaClassifier()
    print("avatar:", sc.observe(a, b, 4)["vote"], "(want AVATAR_NAV)")
                                                      
    a = blank()
    a[2:8, 2:20] = 7
    a[20, 5] = 9
    b = a.copy()
    b[20, 5] = 0
    b[20, 9] = 9
    sc = SchemaClassifier()
    print("cursor:", sc.observe(a, b, 3)["vote"], "(want CURSOR_SELECT)")
                                     
    a = blank()
    a[5:8, 5:8] = 8
    b = a.copy()
    b[5:8, 5:8] = 9
    sc = SchemaClassifier()
    print("toggle:", sc.observe(a, b, 6)["vote"], "(want CLICK_TOGGLE)")
                                                      
    a = blank()
    a[0:20, 0:20] = 4
    a[0:10, 0:20] = 5
    b = a.copy()
    b[0:20, 0:20] = np.rot90(a[0:20, 0:20])
    sc = SchemaClassifier()
    print("transform:", sc.observe(a, b, 5)["vote"], "(want BOARD_TRANSFORM)")
    print("✅ schema classifier v2 self-test ran")
