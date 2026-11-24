                             

                                                                             
                                                                            
                                                  
   

from __future__ import annotations

import argparse
import importlib.util
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from arcengine import GameAction, GameState

try:
    from ..agent import Agent
except Exception:

    class Agent:                          
        pass

try:
    from .vc33_model import ColoredRect, Rect, ShiftHandle, Vc33Problem, Vc33State, astar
except Exception:
    from vc33_model import ColoredRect, Rect, ShiftHandle, Vc33Problem, Vc33State, astar


BACKGROUND = 3
PADDING = 4
STEP_BAR = 7
VESSEL = 0
SWAP_BAR = 1
WALL = 5
HANDLE = 9
PAYLOAD_COLORS = {11, 14, 15}

LEVEL_SPECS = [
    ((32, 32), (2, 0)),
    ((32, 32), (-2, 0)),
    ((52, 52), (0, 2)),
    ((64, 64), (0, 3)),
    ((64, 64), (3, 0)),
    ((64, 64), (-3, 0)),
    ((48, 48), (0, -2)),
]


@dataclass(frozen=True)
class PixelModel:
    problem: Vc33Problem
    state: Vc33State
    click_xy: dict[tuple[str, int], tuple[int, int]]
    grid: np.ndarray


def latest_board(frame: Any) -> np.ndarray | None:
    raw = getattr(frame, "frame", frame)
    if raw is None:
        return None
    arr = np.array(raw, dtype=np.int16)
    if arr.ndim == 3:
        return arr[-1]
    if arr.ndim == 2:
        return arr
    return None


def _mode_without_step(block: np.ndarray) -> int:
    vals = [int(v) for v in block.ravel() if int(v) != STEP_BAR]
    if not vals:
        return int(block.ravel()[0])
    values, counts = np.unique(np.array(vals, dtype=np.int16), return_counts=True)
    return int(values[counts.argmax()])


def display_to_grid(display: np.ndarray, level_index: int) -> np.ndarray:
    grid_size, _ = LEVEL_SPECS[level_index]
    gw, gh = grid_size
    if display.shape == (gh, gw):
        return display.copy()
    if display.shape != (64, 64):
        return display.copy()
    if gw == 32 and gh == 32:
        out = np.zeros((32, 32), dtype=np.int16)
        for y in range(32):
            for x in range(32):
                out[y, x] = _mode_without_step(display[y * 2 : y * 2 + 2, x * 2 : x * 2 + 2])
        return out
    if gw in (48, 52):
        offset = (64 - gw) // 2
        return display[offset : offset + gh, offset : offset + gw].copy()
    return display.copy()


def grid_to_display_xy(rect: Rect, level_index: int) -> tuple[int, int]:
    (gw, _), _ = LEVEL_SPECS[level_index]
    if gw == 32:
        scale = 2
        offset = 0
    else:
        scale = 1
        offset = (64 - gw) // 2 if gw in (48, 52) else 0
    x = offset + rect.x * scale + max(0, rect.w * scale - 1) // 2
    y = offset + rect.y * scale + max(0, rect.h * scale - 1) // 2
    return int(max(0, min(63, x))), int(max(0, min(63, y)))


def connected_components(grid: np.ndarray, color: int) -> list[Rect]:
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    rects: list[Rect] = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or int(grid[y, x]) != color:
                continue
            q = deque([(x, y)])
            seen[y, x] = True
            xs = []
            ys = []
            while q:
                cx, cy = q.popleft()
                xs.append(cx)
                ys.append(cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and int(grid[ny, nx]) == color:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            rects.append(Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return rects


def mask_components(mask: np.ndarray) -> list[Rect]:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    rects: list[Rect] = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or not bool(mask[y, x]):
                continue
            q = deque([(x, y)])
            seen[y, x] = True
            xs = []
            ys = []
            while q:
                cx, cy = q.popleft()
                xs.append(cx)
                ys.append(cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and bool(mask[ny, nx]):
                        seen[ny, nx] = True
                        q.append((nx, ny))
            rects.append(Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return rects


def extract_vessels(grid: np.ndarray, level_index: int) -> list[Rect]:
                                                                                
                                                                            
                                                                            
    comps = mask_components(np.isin(grid, [VESSEL, HANDLE]))
    vessels = []
    for rect in comps:
        crop = grid[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w]
        if int((crop == VESSEL).sum()) == 0:
            continue
        if area(rect) < 10:
            continue
        vessels.append(rect)
    return normalize_top_occlusion(vessels, VESSEL, level_index)


def _runs(mask: np.ndarray, horizontal_scan: bool) -> list[Rect]:
    h, w = mask.shape
    rects: list[Rect] = []
    outer = h if horizontal_scan else w
    inner = w if horizontal_scan else h
    for a in range(outer):
        b = 0
        while b < inner:
            if not (mask[a, b] if horizontal_scan else mask[b, a]):
                b += 1
                continue
            start = b
            while b < inner and (mask[a, b] if horizontal_scan else mask[b, a]):
                b += 1
            if b - start >= 2:
                rects.append(Rect(start, a, b - start, 1) if horizontal_scan else Rect(a, start, 1, b - start))
    return rects


def _merge_line_rects(rects: list[Rect], horizontal_bar: bool, max_gap: int = 8) -> list[Rect]:
    changed = True
    out = rects[:]
    while changed:
        changed = False
        nxt: list[Rect] = []
        used = [False] * len(out)
        for i, a in enumerate(out):
            if used[i]:
                continue
            cur = a
            used[i] = True
            for j in range(i + 1, len(out)):
                if used[j]:
                    continue
                b = out[j]
                if horizontal_bar:
                    same_band = cur.y == b.y and cur.h == b.h
                    gap = max(b.x - (cur.x + cur.w), cur.x - (b.x + b.w), 0)
                    overlap = not (cur.x + cur.w < b.x or b.x + b.w < cur.x)
                    if same_band and (gap <= max_gap or overlap):
                        x0 = min(cur.x, b.x)
                        x1 = max(cur.x + cur.w, b.x + b.w)
                        cur = Rect(x0, cur.y, x1 - x0, cur.h)
                        used[j] = True
                        changed = True
                else:
                    same_band = cur.x == b.x and cur.w == b.w
                    gap = max(b.y - (cur.y + cur.h), cur.y - (b.y + b.h), 0)
                    overlap = not (cur.y + cur.h < b.y or b.y + b.h < cur.y)
                    if same_band and (gap <= max_gap or overlap):
                        y0 = min(cur.y, b.y)
                        y1 = max(cur.y + cur.h, b.y + b.h)
                        cur = Rect(cur.x, y0, cur.w, y1 - y0)
                        used[j] = True
                        changed = True
            nxt.append(cur)
        out = nxt
    return out


def _merge_parallel_bars(rects: list[Rect], horizontal_bar: bool) -> list[Rect]:
    changed = True
    out = rects[:]
    while changed:
        changed = False
        nxt: list[Rect] = []
        used = [False] * len(out)
        for i, a in enumerate(out):
            if used[i]:
                continue
            cur = a
            used[i] = True
            for j in range(i + 1, len(out)):
                if used[j]:
                    continue
                b = out[j]
                if horizontal_bar:
                    if cur.x == b.x and cur.w == b.w:
                        y0 = min(cur.y, b.y)
                        y1 = max(cur.y + cur.h, b.y + b.h)
                        cur = Rect(cur.x, y0, cur.w, y1 - y0)
                        used[j] = True
                        changed = True
                else:
                    if cur.y == b.y and cur.h == b.h:
                        x0 = min(cur.x, b.x)
                        x1 = max(cur.x + cur.w, b.x + b.w)
                        cur = Rect(x0, cur.y, x1 - x0, cur.h)
                        used[j] = True
                        changed = True
            nxt.append(cur)
        out = nxt
    return out


def extract_bars(grid: np.ndarray, *, want_horizontal: bool | None = None) -> list[Rect]:
    mask = grid == WALL
    horizontal = reconstruct_bands(mask, True)
    vertical = reconstruct_bands(mask, False)
    if want_horizontal is True:
        candidates = horizontal
    elif want_horizontal is False:
        candidates = vertical
    else:
        candidates = horizontal + vertical
    bars = [r for r in candidates if area(r) >= 4 and max(r.w, r.h) >= 4]
                                                     
    seen: set[Rect] = set()
    unique: list[Rect] = []
    for bar in bars:
        if bar not in seen:
            seen.add(bar)
            unique.append(bar)
    return unique


def reconstruct_bands(mask: np.ndarray, horizontal_bar: bool) -> list[Rect]:
    pass                                                        

                                                                             
                                                                             
                                                                               
       
    raw_runs = _runs(mask, horizontal_bar)
    long_runs = [r for r in raw_runs if (r.w if horizontal_bar else r.h) >= 4]
    if not long_runs:
        return []

    key_fn = (lambda r: r.y) if horizontal_bar else (lambda r: r.x)
    long_runs.sort(key=key_fn)
    bands: list[list[Rect]] = []
    for run in long_runs:
        if not bands or key_fn(run) > key_fn(bands[-1][-1]) + 1:
            bands.append([run])
        else:
            bands[-1].append(run)

    rects: list[Rect] = []
    for band in bands:
        k0 = min(key_fn(r) for r in band)
        k1 = max(key_fn(r) + (r.h if horizontal_bar else r.w) for r in band)
        band = [r for r in raw_runs if k0 <= key_fn(r) < k1]
        if horizontal_bar:
            x0 = min(r.x for r in band)
            x1 = max(r.x + r.w for r in band)
            y0 = min(r.y for r in band)
            y1 = max(r.y + r.h for r in band)
            rects.append(Rect(x0, y0, x1 - x0, y1 - y0))
        else:
            x0 = min(r.x for r in band)
            x1 = max(r.x + r.w for r in band)
            y0 = min(r.y for r in band)
            y1 = max(r.y + r.h for r in band)
            rects.append(Rect(x0, y0, x1 - x0, y1 - y0))
    return rects


def area(rect: Rect) -> int:
    return rect.w * rect.h


def collides(a: Rect, b: Rect) -> bool:
    return a.x < b.x + b.w and a.x + a.w > b.x and a.y < b.y + b.h and a.y + a.h > b.y


def positive(gravity: tuple[int, int]) -> bool:
    return gravity[0] > 0 or gravity[1] > 0


def horizontal(gravity: tuple[int, int]) -> bool:
    return gravity[0] != 0


def axis(gravity: tuple[int, int], rect: Rect) -> int:
    return rect.y if horizontal(gravity) else rect.x


def cross(gravity: tuple[int, int], rect: Rect) -> int:
    return rect.x if horizontal(gravity) else rect.y


def thickness(gravity: tuple[int, int], rect: Rect) -> int:
    return rect.h if horizontal(gravity) else rect.w


def length(gravity: tuple[int, int], rect: Rect) -> int:
    return rect.w if horizontal(gravity) else rect.h


def far(gravity: tuple[int, int], rect: Rect) -> int:
    return cross(gravity, rect) + length(gravity, rect) if positive(gravity) else cross(gravity, rect)


def near(gravity: tuple[int, int], rect: Rect) -> int:
    return cross(gravity, rect) if positive(gravity) else cross(gravity, rect) + length(gravity, rect)


def source_side_ok(gravity: tuple[int, int], vessel: Rect, handle: Rect) -> bool:
    return far(gravity, vessel) >= near(gravity, handle) if positive(gravity) else far(gravity, vessel) <= near(gravity, handle)


def build_shift_graph(gravity: tuple[int, int], vessels: tuple[Rect, ...], handles: tuple[Rect, ...]) -> tuple[ShiftHandle, ...]:
    shifts: list[ShiftHandle] = []
    for handle in handles:
        same_axis = [
            (i, v)
            for i, v in enumerate(vessels)
            if axis(gravity, v) == axis(gravity, handle) and source_side_ok(gravity, v, handle)
        ]
        if same_axis:
            side = [
                (i, v)
                for i, v in enumerate(vessels)
                if axis(gravity, v) + thickness(gravity, v) == axis(gravity, handle) - thickness(gravity, handle)
                and source_side_ok(gravity, v, handle)
            ]
            if not side:
                continue
            key = (lambda item: cross(gravity, item[1]))
            src = min(side, key=key)[0] if positive(gravity) else max(side, key=key)[0]
            dst = min(same_axis, key=key)[0] if positive(gravity) else max(same_axis, key=key)[0]
            shifts.append(ShiftHandle(handle, src, dst))
            continue

        spanning = [
            (i, v)
            for i, v in enumerate(vessels)
            if axis(gravity, v) < axis(gravity, handle)
            and axis(gravity, v) + thickness(gravity, v) > axis(gravity, handle)
            and source_side_ok(gravity, v, handle)
        ]
        if not spanning:
            continue
        other = [
            (i, v)
            for i, v in enumerate(vessels)
            if axis(gravity, v) == axis(gravity, handle) + thickness(gravity, handle) * 2
            and source_side_ok(gravity, v, handle)
        ]
        if not other:
            continue
        key = (lambda item: cross(gravity, item[1]))
        span_id = min(spanning, key=key)[0] if positive(gravity) else max(spanning, key=key)[0]
        other_id = min(other, key=key)[0] if positive(gravity) else max(other, key=key)[0]
        shifts.append(ShiftHandle(handle, other_id, span_id))
    return tuple(shifts)


def has_marker_body(grid: np.ndarray, rect: Rect) -> bool:
    y0 = max(0, rect.y - 5)
    y1 = min(grid.shape[0], rect.y + rect.h + 5)
    x0 = max(0, rect.x - 5)
    x1 = min(grid.shape[1], rect.x + rect.w + 5)
    crop = grid[y0:y1, x0:x1].copy()
                                                                                   
                                                                           
    yy, xx = np.where(crop == PADDING)
    if len(xx) == 0:
        return False
    cx = rect.x + rect.w / 2 - x0
    cy = rect.y + rect.h / 2 - y0
    return bool(np.any(np.abs(xx - cx) <= 4) and np.any(np.abs(yy - cy) <= 4))


def expand_target_marker(grid: np.ndarray, colored: ColoredRect) -> Rect | None:
    color = colored.color
    seed = colored.rect
    h, w = grid.shape
    allowed = (grid == color) | (grid == PADDING)
    q = deque()
    seen: set[tuple[int, int]] = set()
    for y in range(seed.y, seed.y + seed.h):
        for x in range(seed.x, seed.x + seed.w):
            if 0 <= x < w and 0 <= y < h and bool(allowed[y, x]):
                q.append((x, y))
                seen.add((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if (nx, ny) in seen or not bool(allowed[ny, nx]):
                continue
            seen.add((nx, ny))
            q.append((nx, ny))
    if not seen:
        return None
    xs = [x for x, _ in seen]
    ys = [y for _, y in seen]
    rect = Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                                                                            
    if area(rect) > 64 or area(rect) <= area(seed):
        return None
    return rect


def _payload_extent(visible_cross_size: int) -> int:
    return visible_cross_size * 2 if visible_cross_size >= 3 else visible_cross_size + 1


def expand_payload_rect(gravity: tuple[int, int], rect: Rect) -> Rect:
    dx, dy = gravity
    if dx > 0:
        full_w = _payload_extent(rect.h)
        return Rect(rect.x - (full_w - rect.w), rect.y, full_w, rect.h)
    if dx < 0:
        full_w = _payload_extent(rect.h)
        return Rect(rect.x, rect.y, full_w, rect.h)
    if dy > 0:
        full_h = _payload_extent(rect.w)
        return Rect(rect.x, rect.y - (full_h - rect.h), rect.w, full_h)
    full_h = _payload_extent(rect.w)
    return Rect(rect.x, rect.y, rect.w, full_h)


def refine_floors(grid: np.ndarray, floors: list[Rect], walls: list[Rect], gravity: tuple[int, int]) -> list[Rect]:
    refined: list[Rect] = []
    for floor in floors:
        if horizontal(gravity):
                                                                        
            cuts = sorted({floor.y, floor.y + floor.h} | {w.y for w in walls if collides(floor, w)} | {w.y + w.h for w in walls if collides(floor, w)})
            pieces = [Rect(floor.x, cuts[i], floor.w, cuts[i + 1] - cuts[i]) for i in range(len(cuts) - 1)]
        else:
                                                                        
            cuts = sorted({floor.x, floor.x + floor.w} | {w.x for w in walls if collides(floor, w)} | {w.x + w.w for w in walls if collides(floor, w)})
            pieces = [Rect(cuts[i], floor.y, cuts[i + 1] - cuts[i], floor.h) for i in range(len(cuts) - 1)]
        for piece in pieces:
            if piece.w <= 0 or piece.h <= 0:
                continue
            if any(collides(piece, wall) for wall in walls):
                continue
            crop = grid[piece.y : piece.y + piece.h, piece.x : piece.x + piece.w]
            density = float((crop == WALL).sum()) / max(1, area(piece))
            if density >= 0.5 and area(piece) >= 4:
                refined.append(piece)
    return refined


def normalize_top_occlusion(rects: list[Rect], color: int, level_index: int) -> list[Rect]:
                                                                               
                                                                       
    if LEVEL_SPECS[level_index][0] != (64, 64) or color not in (VESSEL, WALL):
        return rects
    out = []
    for r in rects:
        if r.y == 1:
            out.append(Rect(r.x, 0, r.w, r.h + 1))
        else:
            out.append(r)
    return out


def build_model_from_grid(grid: np.ndarray, level_index: int) -> PixelModel | None:
    _, gravity = LEVEL_SPECS[level_index]
    vessels = tuple(sorted(extract_vessels(grid, level_index), key=lambda r: (r.x, r.y, r.w, r.h)))
    handles = tuple(sorted(connected_components(grid, HANDLE), key=lambda r: (r.x, r.y, r.w, r.h)))
    swaps = tuple(sorted(connected_components(grid, SWAP_BAR), key=lambda r: (r.x, r.y, r.w, r.h)))
    gray = normalize_top_occlusion(extract_bars(grid, want_horizontal=horizontal(gravity)), WALL, level_index)
    floor_gray = normalize_top_occlusion(extract_bars(grid, want_horizontal=not horizontal(gravity)), WALL, level_index)

    colored: list[ColoredRect] = []
    for color in sorted(PAYLOAD_COLORS):
        for rect in connected_components(grid, color):
            colored.append(ColoredRect(color, rect))

    targets_list: list[ColoredRect] = []
    payload_list: list[ColoredRect] = []
    for component in colored:
        expanded = expand_target_marker(grid, component)
        if expanded is not None and has_marker_body(grid, component.rect):
            targets_list.append(ColoredRect(component.color, expanded))
        else:
            payload_list.append(ColoredRect(component.color, expand_payload_rect(gravity, component.rect)))
    target_rects = tuple(targets_list)
    payload_candidates = tuple(payload_list)
    if not vessels or not handles or not target_rects or not payload_candidates:
        return None

                                                                                  
                                                                              
    walls = list(gray)
    floors = refine_floors(grid, list(floor_gray), walls, gravity)

    payloads = []
    for payload in payload_candidates:
        wall_id = None
        for i, wall in enumerate(walls):
            if collides(wall, payload.rect):
                wall_id = i
                break
        payloads.append(ColoredRect(payload.color, payload.rect, wall_id))

    shifts = build_shift_graph(gravity, vessels, handles)
    if len(shifts) != len(handles):
        return None

    problem = Vc33Problem(
        gravity=gravity,
        grid_size=LEVEL_SPECS[level_index][0],
        vessels0=vessels,
        targets0=target_rects,
        payloads=tuple(payloads),
        walls=tuple(walls),
        floors=tuple(floors),
        shifts=shifts,
        swaps=swaps,
    )
    state = Vc33State(vessels, target_rects)
    click_xy: dict[tuple[str, int], tuple[int, int]] = {}
    for i, handle in enumerate(handles):
        click_xy[("shift", i)] = grid_to_display_xy(handle, level_index)
    for i, swap_rect in enumerate(swaps):
        click_xy[("swap", i)] = grid_to_display_xy(swap_rect, level_index)
    return PixelModel(problem, state, click_xy, grid)


def build_model_from_frame(frame: Any, level_index: int) -> PixelModel | None:
    display = latest_board(frame)
    if display is None:
        return None
    grid = display_to_grid(display, level_index)
    return build_model_from_grid(grid, level_index)


def action6(x: int, y: int, reasoning: dict[str, Any] | None = None) -> GameAction:
    action = GameAction.ACTION6
    action.set_data({"x": int(x), "y": int(y)})
    if reasoning is not None:
        setattr(action, "reasoning", reasoning)
    return action


class Vc33Solver(Agent):
    MAX_ACTIONS = 260

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.level_index = -1
        self.plan: list[tuple[str, int]] = []
        self.plan_i = 0
        self.click_xy: dict[tuple[str, int], tuple[int, int]] = {}

    def is_done(self, frames: list[Any], latest_frame: Any) -> bool:
        return latest_frame.state is GameState.WIN

    def _reset_plan_if_new_level(self, latest_frame: Any) -> None:
        level_index = int(getattr(latest_frame, "levels_completed", 0) or 0)
        if level_index != self.level_index:
            self.level_index = level_index
            self.plan = []
            self.plan_i = 0
            self.click_xy = {}

    def choose_action(self, frames: list[Any], latest_frame: Any) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.plan = []
            return GameAction.RESET
        self._reset_plan_if_new_level(latest_frame)
        if self.level_index >= len(LEVEL_SPECS):
            return action6(32, 32)

        if not self.plan or self.plan_i >= len(self.plan):
            model = build_model_from_frame(latest_frame, self.level_index)
            if model is None:
                print(f"[VC33] pixel extraction failed level={self.level_index + 1}")
                return action6(32, 32)
            plan, expansions, seen = astar(model.problem, model.state, max_expansions=1_000_000)
            if not plan:
                print(f"[VC33] planner failed level={self.level_index + 1} expansions={expansions} seen={seen}")
                return action6(32, 32)
            self.plan = plan
            self.plan_i = 0
            self.click_xy = model.click_xy
            print(f"[VC33] level={self.level_index + 1} planned={len(plan)} expansions={expansions} seen={seen}")

        action = self.plan[self.plan_i]
        self.plan_i += 1
        x, y = self.click_xy[action]
        return action6(
            x,
            y,
            {"agent": "vc33solver", "level": self.level_index + 1, "action": str(action)},
        )


def load_source(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("vc33_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_display(module: Any, level_index: int) -> np.ndarray:
    game = module.Vc33()
    game.set_level(level_index)
    return game.camera.render(game.current_level.get_sprites())


def source_counts(module: Any, level_index: int) -> dict[str, int]:
    game = module.Vc33()
    game.set_level(level_index)
    return {
        "vessels": len(game.current_level.get_sprites_by_tag("0043nzrtobajqi")),
        "handles": len(game.current_level.get_sprites_by_tag("0022jvmlspyigc")),
        "swaps": len(game.current_level.get_sprites_by_tag("0004sttgkofqwb")),
        "targets": len(game.current_level.get_sprites_by_tag("0016uciqlhjlom")),
        "payloads": len(game.current_level.get_sprites_by_tag("0010gnulkywfpz")),
    }


def validate_pixels(source_path: Path) -> bool:
    module = load_source(source_path)
    ok_all = True
    for level_index in range(len(LEVEL_SPECS)):
        display = source_display(module, level_index)
        model = build_model_from_frame(display, level_index)
        expected = source_counts(module, level_index)
        if model is None:
            print(f"[VC33_PIXEL] level={level_index + 1} extraction=FAIL expected={expected}")
            ok_all = False
            continue
        got = {
            "vessels": len(model.problem.vessels0),
            "handles": len(model.problem.shifts),
            "swaps": len(model.problem.swaps),
            "targets": len(model.problem.targets0),
            "payloads": len(model.problem.payloads),
        }
        plan, expansions, seen = astar(model.problem, model.state, max_expansions=1_000_000)
        matched = got == expected
        won = bool(plan)
        ok = matched and won
        ok_all = ok_all and ok
        print(
            f"[VC33_PIXEL] level={level_index + 1} ok={ok} counts_match={matched} "
            f"got={got} expected={expected} plan_depth={len(plan) if plan else None} "
            f"expansions={expansions} seen={seen}"
        )
    return ok_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-source", type=Path)
    args = parser.parse_args()
    if args.validate_source:
        raise SystemExit(0 if validate_pixels(args.validate_source) else 1)


if __name__ == "__main__":
    main()
