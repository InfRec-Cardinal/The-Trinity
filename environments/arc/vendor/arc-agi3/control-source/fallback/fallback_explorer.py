                                                                              
                                                                             
                                                                              
                                                                                  
                                                                                  
                                                                            
                                                            
                                                                                 
                                                                                 
                                                                             
                                                   
                                                                                
                                                               
                                                                                  
                                           
                                               
 
                                                                                  
                                                                                   
                                                                              
import hashlib
from collections import deque, defaultdict
import numpy as np

try:
    from arcengine import GameAction, GameState
except Exception:                                            
    GameAction = None
    GameState = None


                                                                               
def _board(latest_frame):
    f = getattr(latest_frame, "frame", None)
    if f is None:
        return None
    a = np.array(f, dtype=np.int16)
                                                                                  
    return a[-1] if a.ndim == 3 else (a if a.ndim == 2 else None)


def _mask_borders(grid, border=2):
    pass                                                                           
                                                                      
    g = grid.copy()
    g[:border, :] = 0
    g[-border:, :] = 0
    g[:, :border] = 0
    g[:, -border:] = 0
    return g


def _components(grid, bg):
    pass                                                               
                                                         
    H, W = grid.shape
    seen = np.zeros((H, W), bool)
    comps = []
    for y in range(H):
        for x in range(W):
            if seen[y, x] or grid[y, x] == bg:
                continue
            c = int(grid[y, x])
            q = deque([(y, x)])
            seen[y, x] = True
            cells = [(y, x)]
            while q:
                cy, cx = q.popleft()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and grid[ny, nx] == c:
                        seen[ny, nx] = True
                        q.append((ny, nx))
                        cells.append((ny, nx))
            ys = [p[0] for p in cells]
            xs = [p[1] for p in cells]
            comps.append((c, len(cells), (sum(ys) / len(cells), sum(xs) / len(cells))))
    return comps


def _signature(grid):
    pass                                                                          
                                                                       
    if grid is None:
        return "none"
    g = _mask_borders(grid)
    vals, counts = np.unique(g, return_counts=True)
    bg = int(vals[counts.argmax()]) if len(vals) else 0
    comps = _components(g, bg)
                                                                   
    items = sorted((c, s, int(cy) // 4, int(cx) // 4) for (c, s, (cy, cx)) in comps)
    h = hashlib.md5(repr(items).encode()).hexdigest()[:16]
    return h


def _normalize_actions(latest_frame):
    pass                                                                                
    out = []
    raw = getattr(latest_frame, "available_actions", None) or []
    for aid in raw:
        if GameAction is not None and isinstance(aid, GameAction):
            a = aid
        elif GameAction is not None:
            a = None
            for cand in GameAction:
                if cand.value == int(aid):
                    a = cand
                    break
        else:
            a = int(aid)
        if a is not None and (GameAction is None or a is not GameAction.RESET):
            out.append(a)
    return out


class FallbackExplorer:
    pass                                                                              
                                                

    def __init__(self):
                                                               
        self.edges = defaultdict(dict)
                                                                       
        self.untried = {}
                                                                      
        self.path = []
                                                                                     
        self.hist = []
        self.prev_sig = None
        self.prev_action_key = None
        self.reset_tested = False
        self.replay_queue = deque()                                                  

                                                                                 
    @staticmethod
    def _key(action, xy=None):
        v = action.value if (GameAction is not None and hasattr(action, "value")) else action
        return f"{v}" if xy is None else f"{v}:{xy[0]},{xy[1]}"

    def _click_candidates(self, grid, prev_grid):
        pass                                                                   
                                                 
        cands = []
        if grid is None:
            return [(32, 32)]
        g = _mask_borders(grid)
        vals, counts = np.unique(g, return_counts=True)
        bg = int(vals[counts.argmax()]) if len(vals) else 0
        for (_, _, (cy, cx)) in _components(g, bg):
            cands.append((int(round(cx)), int(round(cy))))                       
        if prev_grid is not None and prev_grid.shape == grid.shape:
            ys, xs = np.where(prev_grid != grid)
            for y, x in list(zip(ys, xs))[:12]:
                cands.append((int(x), int(y)))
                     
        seen = set()
        out = []
        for c in cands:
            if c not in seen:
                seen.add(c)
                out.append(c)
            if len(out) >= 28:
                break
        return out or [(32, 32)]

    def _enumerate_action_keys(self, latest_frame, grid, prev_grid):
        pass                                                                            
        acts = _normalize_actions(latest_frame)
        keys = []
        meta = {}                                
        for a in acts:
            is_complex = (hasattr(a, "is_complex") and a.is_complex())
            if is_complex:
                for xy in self._click_candidates(grid, prev_grid):
                    k = self._key(a, xy)
                    keys.append(k)
                    meta[k] = (a, xy)
            else:
                k = self._key(a)
                keys.append(k)
                meta[k] = (a, None)
        return keys, meta

    def choose_action(self, frames, latest_frame):
                        
        state = getattr(latest_frame, "state", None)
        if GameState is not None and state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.prev_sig = None
            self.prev_action_key = None
            return GameAction.RESET

        grid = _board(latest_frame)
        prev_grid = _board(frames[-1]) if frames else None
        sig = _signature(grid)

                                                     
        if self.prev_sig is not None and self.prev_action_key is not None:
            self.edges[self.prev_sig][self.prev_action_key] = sig
            if self.prev_action_key in self.untried.get(self.prev_sig, set()):
                self.untried[self.prev_sig].discard(self.prev_action_key)
                                                
            self.path.append(self.prev_action_key)
            self.hist.append(self.prev_sig)

        keys, meta = self._enumerate_action_keys(latest_frame, grid, prev_grid)
        if sig not in self.untried:
            self.untried[sig] = set(keys)
        else:
                                                                          
            self.untried[sig] &= set(keys) if keys else self.untried[sig]

                                                                           
        choice_key = None
        if self.untried.get(sig):
                                                                                 
            untried_sorted = sorted(self.untried[sig], key=lambda k: (":" in k, k))
            choice_key = untried_sorted[0]

                                                                                     
        if choice_key is None:
            target = self._find_frontier()
            if target is not None:
                replay = self._path_to(target)
                if replay:
                    choice_key = replay[0]
                                                                            
            if choice_key is None and keys:
                choice_key = keys[0]

        if choice_key is None:
                                                      
            if not self.reset_tested and GameAction is not None:
                self.reset_tested = True
                self.prev_sig = sig
                self.prev_action_key = None
                return GameAction.RESET
                                                                
            return self._safe_action(latest_frame, grid)

        action, xy = meta.get(choice_key, (None, None))
        if action is None:
            return self._safe_action(latest_frame, grid)
        if xy is not None and hasattr(action, "set_data"):
            action.set_data({"x": int(xy[0]), "y": int(xy[1])})
        self.prev_sig = sig
        self.prev_action_key = choice_key
        return action

    def _find_frontier(self):
        pass                                                                         
        for s, acts in self.untried.items():
            if acts:
                return s
        return None

    def _path_to(self, target):
        pass                                                              
                                                                             
                                                        
        start = self.prev_sig
        if start is None:
            return []
        q = deque([(start, [])])
        seen = {start}
        while q:
            node, acts = q.popleft()
            if node == target:
                return acts
            for ak, nxt in self.edges.get(node, {}).items():
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, acts + [ak]))
        return []

    def _safe_action(self, latest_frame, grid):
        acts = _normalize_actions(latest_frame)
        if acts:
            a = acts[0]
            if hasattr(a, "is_complex") and a.is_complex():
                a.set_data({"x": 32, "y": 32})
            return a
        if GameAction is not None:
            return GameAction.RESET
        return 0

    def _safe_fallback_action(self, latest_frame):
        return self._safe_action(latest_frame, None)


                                                                              
if __name__ == "__main__":
                                                                          
    g0 = np.zeros((64, 64), dtype=np.int16)
    g0[10:14, 10:14] = 3
    g1 = g0.copy()
    g1[10:14, 11:15] = 3
    g1[10:14, 10] = 0
    print("sig g0:", _signature(g0))
    print("sig g1:", _signature(g1))
    print("different signatures?", _signature(g0) != _signature(g1))
    print("status-bar mask: borders zeroed?", _mask_borders(np.ones((64, 64), dtype=np.int16))[0, 0] == 0)
    comps = _components(_mask_borders(g0), 0)
    print("components found in g0:", len(comps))
    print("click candidates bounded?", len(FallbackExplorer()._click_candidates(g0, g1)) <= 28)
    print("OK fallback explorer self-test ran")
