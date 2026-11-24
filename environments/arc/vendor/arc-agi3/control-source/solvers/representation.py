                                                                                   
                                                                              
                                                                                
                                                                               
                                                   

                                                                               
                                                                          
                                                                                
                                                                               
                                                                               
                                                                               
                                                                                  

                                             
                                                                                  
                                                                          
                                                                         

                                                                  
                                                                                 
                                                                                  
                                                                 
                                                                                   
                                                                                    
                                                                           
                                                                               
                                                                     
                                                                                    
                                                                                  
                                                                                
                                                                                
                                                                       
                                                                                   
                                                                                    
                                                                             

                                                                                
                                       
   

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

import numpy as np


                                                                             
                                                                              
                                                                             
@dataclass
class Obj:
    color: int
    cells: frozenset                                    
    bbox: tuple                              
    centroid: tuple                  
    shape_hash: str                                            
    size: int


def _components(grid: np.ndarray, background: int) -> list[tuple[int, list]]:
    pass                                                                
                                                         
    H, W = grid.shape
    seen = np.zeros((H, W), dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y, x] or grid[y, x] == background:
                continue
            color = int(grid[y, x])
            q = deque([(y, x)])
            seen[y, x] = True
            cells = []
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if (
                        0 <= ny < H
                        and 0 <= nx < W
                        and not seen[ny, nx]
                        and grid[ny, nx] == color
                    ):
                        seen[ny, nx] = True
                        q.append((ny, nx))
            out.append((color, cells))
    return out


def _canonical_shape_hash(cells: list) -> str:
    pass                                                                  
                                                                           
                                                                        
    ys = [c[0] for c in cells]
    xs = [c[1] for c in cells]
    y0, x0 = min(ys), min(xs)
    h = max(ys) - y0 + 1
    w = max(xs) - x0 + 1
    mask = np.zeros((h, w), dtype=np.uint8)
    for cy, cx in cells:
        mask[cy - y0, cx - x0] = 1
    variants = []
    m = mask
    for _ in range(4):
        variants.append(m.tobytes() + bytes(m.shape))
        variants.append(np.fliplr(m).tobytes() + bytes(np.fliplr(m).shape))
        m = np.rot90(m)
    best = min(variants)
    return hashlib.sha256(best).hexdigest()[:12]


def detect_background(grid: np.ndarray) -> int:
    pass                                                                      
    vals, counts = np.unique(grid, return_counts=True)
    return int(vals[counts.argmax()])


def parse_objects(grid: np.ndarray, background: Optional[int] = None) -> list[Obj]:
    if background is None:
        background = detect_background(grid)
    objs = []
    for color, cells in _components(grid, background):
        ys = [c[0] for c in cells]
        xs = [c[1] for c in cells]
        bbox = (min(ys), min(xs), max(ys), max(xs))
        centroid = (sum(ys) / len(cells), sum(xs) / len(cells))
        objs.append(
            Obj(
                color=color,
                cells=frozenset(cells),
                bbox=bbox,
                centroid=centroid,
                shape_hash=_canonical_shape_hash(cells),
                size=len(cells),
            )
        )
    return objs


                                                                             
                                                                                 
                                                                             
class RoleInferencer:
    pass                                                                      
                                                               

                                                                               
                                                                             
                                                                                
                                       
                                                                                       
       

    def __init__(self):
                                                                                   
                                                                                   
        self.move_evidence = defaultdict(int)
        self.avatar_key = None                             
        self.avatar_attr_history = []
        self.prev_objs = None
        self.level_advanced_recently = False

    @staticmethod
    def _key(o: Obj):
        return (o.color, o.size, o.shape_hash)

    def update(self, objs, last_action_was_move, level_advanced, action_dir=None):
        pass                                                               
                                                                                 
                                                                                    
        if (
            self.prev_objs is not None
            and last_action_was_move
            and action_dir is not None
        ):
            dx, dy = action_dir
            exp_row, exp_col = dy, dx                           
            for oc in objs:
                                                                                 
                best = None
                bestd = 1e9
                for op in self.prev_objs:
                    if op.color != oc.color or op.size != oc.size:
                        continue
                    d = (
                        (oc.centroid[0] - op.centroid[0]) ** 2
                        + (oc.centroid[1] - op.centroid[1]) ** 2
                    ) ** 0.5
                    if d < bestd:
                        bestd = d
                        best = op
                if best is None:
                    continue
                drow = oc.centroid[0] - best.centroid[0]
                dcol = oc.centroid[1] - best.centroid[1]
                moved_right_way = (
                    abs(drow - exp_row) < 1.5
                    and abs(dcol - exp_col) < 1.5
                    and (abs(drow) + abs(dcol)) > 0.4
                )
                if moved_right_way:
                    self.move_evidence[self._key(oc)] += 2
        if self.move_evidence:
            self.avatar_key = max(self.move_evidence, key=self.move_evidence.get)
        av = self.avatar(objs)
        if av is not None:
            cur = (av.color, av.shape_hash)
            if not self.avatar_attr_history or self.avatar_attr_history[-1] != cur:
                self.avatar_attr_history.append(cur)
        self.prev_objs = objs
        self.level_advanced_recently = level_advanced

    @property
    def avatar_shape_hash(self):
        return self.avatar_key[2] if self.avatar_key else None

    def avatar(self, objs):
        if self.avatar_key is None:
            return None
        col, sz, sh = self.avatar_key
        exact = [o for o in objs if (o.color, o.size, o.shape_hash) == self.avatar_key]
        if exact:
            return exact[0]
        relaxed = [o for o in objs if o.color == col and o.size == sz]
        return relaxed[0] if relaxed else None

    def candidate_goals(self, objs, grid_shape=None):
        pass                                                                    
                                                                                 
                                                                             
                                            
        av_hash = self.avatar_shape_hash
        H = W = 64
        if grid_shape is not None:
            H, W = grid_shape

        def is_border_junk(o):
            y0, x0, y1, x1 = o.bbox
                                                              
            if y0 == y1 and (x1 - x0) >= W * 0.6:                  
                return True
            if x0 == x1 and (y1 - y0) >= H * 0.6:                
                return True
                                                                
            touches_edge = y0 == 0 or x0 == 0 or y1 == H - 1 or x1 == W - 1
            if touches_edge and o.size >= max(H, W):
                return True
            return False

        non_avatar = [
            o for o in objs if o.shape_hash != av_hash and not is_border_junk(o)
        ]
        by_color = defaultdict(list)
        for o in non_avatar:
            by_color[o.color].append(o)
        ranked = sorted(non_avatar, key=lambda o: (len(by_color[o.color]), o.size))
        return ranked


                                                                             
                                                                      
                                                                             
def infer_goal_relation(
    role: RoleInferencer, objs: list[Obj], grid_shape=None
) -> Optional[dict]:
    pass                                                                            
                                                                                  
                                                            

                                                                                   
                                                                           
    av = role.avatar(objs)
    if av is None:
        return None
    goals = role.candidate_goals(objs, grid_shape=grid_shape)
    if not goals:
        return None
    goal = goals[0]
                                                                               
    if goal.shape_hash != av.shape_hash:
        return {
            "type": "shape_match",
            "target_shape_hash": goal.shape_hash,
            "goal_obj": goal,
            "avatar_shape_hash": av.shape_hash,
        }
                                             
    return {"type": "reach", "goal_obj": goal}


                                                                             
                                                          
                                                                             
class PerceptionMonitor:
    pass                                                                   
                                                                          
                                                                             
                                                    

    def __init__(self, swing_tol: float = 0.5):
        self.prev_count = None
        self.swing_tol = swing_tol
        self.last_trusted = None

    def check(self, objs: list[Obj]) -> tuple[bool, list[Obj]]:
        n = len(objs)
        trusted = True
        if self.prev_count is not None and self.prev_count > 0:
            swing = abs(n - self.prev_count) / max(1, self.prev_count)
            if swing > self.swing_tol:
                trusted = False
        self.prev_count = n
        if trusted or self.last_trusted is None:
            self.last_trusted = objs
            return True, objs
                                            
        return False, self.last_trusted


                                                                             
           
                                                                             
if __name__ == "__main__":
    g = np.zeros((16, 16), dtype=np.int8)
                                                                             
    for y, x in [(2, 2), (3, 2), (4, 2), (4, 3)]:
        g[y, x] = 3
    for y, x in [(10, 10), (10, 11), (10, 12), (9, 12)]:
        g[y, x] = 5
    objs = parse_objects(g)
    print(f"background={detect_background(g)}  objects={len(objs)}")
    for o in objs:
        print(
            f"  color={o.color} size={o.size} shape={o.shape_hash} centroid={tuple(round(c, 1) for c in o.centroid)}"
        )
                                                                      
    hs = {o.color: o.shape_hash for o in objs}
    print("same canonical shape (rotation-invariant)?", hs.get(3) == hs.get(5))
    print("✅ representation layer self-test ran")
