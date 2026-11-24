                    

                                                                  
                                                                          
                                                                             
                                                         

                                                                              
                  
   

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
from arcengine import GameAction, GameState

try:
    from ..agent import Agent
except Exception:

    class Agent:                          
        pass


FIELD = 4
BACKGROUND = 5
INSTRUCTION_COLORS = {0, 2, 3}
SPECIAL_CLICK_COLOR = 6
SPRITE = 6
STEP = 8


@dataclass(frozen=True)
class Patch:
    x: int
    y: int
    micro: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + 3, self.y + 3)

    @property
    def center_color(self) -> int:
        return self.micro[1][1]

    @property
    def flat(self) -> tuple[int, ...]:
        return tuple(v for row in self.micro for v in row)

    @property
    def is_uniform(self) -> bool:
        vals = self.flat
        return all(v == vals[0] for v in vals)

    @property
    def has_special_click_shape(self) -> bool:
        return SPECIAL_CLICK_COLOR in self.flat


@dataclass(frozen=True)
class Constraint:
    tile: Patch
    center_color: int
    equal: bool
    source: Patch
    offset: tuple[int, int]

    def satisfied(self) -> bool:
        color = self.tile.center_color
        return color == self.center_color if self.equal else color != self.center_color


def board_from_frame(frame):
    arr = np.array(frame, dtype=np.int16)
    return arr[-1] if arr.ndim == 3 else arr


def _block_color(block: np.ndarray) -> int:
    vals, counts = np.unique(block, return_counts=True)
    return int(vals[counts.argmax()])


def _micro(grid: np.ndarray, y: int, x: int):
    return tuple(
        tuple(_block_color(grid[y + r * 2 : y + r * 2 + 2, x + c * 2 : x + c * 2 + 2]) for c in range(3))
        for r in range(3)
    )


def _ring_score(grid: np.ndarray, y: int, x: int, color: int = FIELD) -> int:
    y0, y1 = max(0, y - 2), min(grid.shape[0], y + SPRITE + 2)
    x0, x1 = max(0, x - 2), min(grid.shape[1], x + SPRITE + 2)
    outer = grid[y0:y1, x0:x1].copy()
    inner_y0, inner_y1 = y - y0, y - y0 + SPRITE
    inner_x0, inner_x1 = x - x0, x - x0 + SPRITE
    outer[inner_y0:inner_y1, inner_x0:inner_x1] = -99
    return int((outer == color).sum())


def _valid_micro_patch(grid: np.ndarray, y: int, x: int) -> bool:
    if y + SPRITE > grid.shape[0] or x + SPRITE > grid.shape[1]:
        return False
                                                                            
    for r in range(3):
        for c in range(3):
            b = grid[y + r * 2 : y + r * 2 + 2, x + c * 2 : x + c * 2 + 2]
            vals, counts = np.unique(b, return_counts=True)
            if int(counts.max()) < 3:
                return False
    return True


def scan_patches(grid: np.ndarray) -> dict[tuple[int, int], Patch]:
    patches: dict[tuple[int, int], Patch] = {}
    for y in range(0, grid.shape[0] - SPRITE + 1, 2):
        for x in range(0, grid.shape[1] - SPRITE + 1, 2):
            if _ring_score(grid, y, x, FIELD) < 6:
                continue
            if not _valid_micro_patch(grid, y, x):
                continue
            micro = _micro(grid, y, x)
            flat = tuple(v for row in micro for v in row)
            if FIELD in flat or BACKGROUND in flat:
                continue
            if len(set(flat)) == 1 and flat[0] in (FIELD, BACKGROUND):
                continue
            patches[(x, y)] = Patch(x=x, y=y, micro=micro)
    return patches


def classify_patches(patches: dict[tuple[int, int], Patch]):
    clickables: dict[tuple[int, int], Patch] = {}
    glyphs: list[Patch] = []

    for key, patch in patches.items():
        if patch.is_uniform and patch.center_color not in (FIELD, BACKGROUND):
            clickables[key] = patch
        elif patch.has_special_click_shape:
            clickables[key] = patch

    for patch in patches.values():
        if patch.is_uniform or patch.has_special_click_shape:
            continue
        if patch.center_color in INSTRUCTION_COLORS | {FIELD, BACKGROUND, SPECIAL_CLICK_COLOR}:
            continue
        neighbor_count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                if (patch.x + dc * STEP, patch.y + dr * STEP) in clickables:
                    neighbor_count += 1
        if neighbor_count:
            glyphs.append(patch)

    return clickables, glyphs


def read_constraints(grid: np.ndarray) -> list[Constraint]:
    patches = scan_patches(grid)
    clickables, glyphs = classify_patches(patches)
    constraints: list[Constraint] = []

    for glyph in glyphs:
        for r in range(3):
            for c in range(3):
                if (r, c) == (1, 1):
                    continue
                dc, dr = c - 1, r - 1
                tile = clickables.get((glyph.x + dc * STEP, glyph.y + dr * STEP))
                if tile is None:
                    continue
                equal = glyph.micro[r][c] == 0
                constraints.append(
                    Constraint(
                        tile=tile,
                        center_color=glyph.center_color,
                        equal=equal,
                        source=glyph,
                        offset=(dr, dc),
                    )
                )
    return constraints


def choose_unsatisfied(grid: np.ndarray) -> tuple[Patch | None, list[Constraint]]:
    constraints = read_constraints(grid)
    by_tile: dict[tuple[int, int], list[Constraint]] = {}
    for con in constraints:
        by_tile.setdefault((con.tile.x, con.tile.y), []).append(con)

    for key in sorted(by_tile, key=lambda p: (p[1], p[0])):
        cons = by_tile[key]
        if all(c.satisfied() for c in cons):
            continue
                                                                                   
                                                                                
                                               
        equal_targets = {c.center_color for c in cons if c.equal}
        if len(equal_targets) > 1:
            continue
        if equal_targets:
            target = next(iter(equal_targets))
            if any((not c.equal) and c.center_color == target for c in cons):
                continue
        return cons[0].tile, constraints
    return None, constraints


def solve_summary(grid: np.ndarray) -> dict[str, Any]:
    constraints = read_constraints(grid)
    unsatisfied = [c for c in constraints if not c.satisfied()]
    return {
        "constraints": len(constraints),
        "tiles": len({(c.tile.x, c.tile.y) for c in constraints}),
        "glyphs": len({(c.source.x, c.source.y) for c in constraints}),
        "unsatisfied": len(unsatisfied),
        "clicks": [c.tile.center for c in unsatisfied],
        "details": [
            {
                "tile": c.tile.center,
                "tile_color": c.tile.center_color,
                "center": c.center_color,
                "equal": c.equal,
                "glyph": c.source.center,
                "satisfied": c.satisfied(),
            }
            for c in constraints
        ],
    }


class Ft09Csp(Agent):
    MAX_ACTIONS = 600

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_level = None
        self.actions_on_level = 0

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state in (GameState.WIN, GameState.GAME_OVER)

    def choose_action(self, frames, latest_frame) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.last_level = None
            self.actions_on_level = 0
            return GameAction.RESET

        if self.last_level != latest_frame.levels_completed:
            self.last_level = latest_frame.levels_completed
            self.actions_on_level = 0

        grid = board_from_frame(latest_frame.frame)
        tile, constraints = choose_unsatisfied(grid)
        print(
            "[FT09CSP] "
            f"level={latest_frame.levels_completed} constraints={len(constraints)} "
            f"unsat={sum(not c.satisfied() for c in constraints)} "
            f"action_count={self.actions_on_level}"
        )

        if tile is None:
                                                                                  
                                                                              
            action = GameAction.ACTION6
            action.set_data({"x": 0, "y": 0})
            return action

        self.actions_on_level += 1
        action = GameAction.ACTION6
        x, y = tile.center
        action.set_data({"x": x, "y": y})
        print(f"[FT09CSP] click x={x} y={y} tile_color={tile.center_color}")
        return action


def oracle_targets_from_source(src_path):
    p = pathlib.Path(src_path)
    spec = importlib.util.spec_from_file_location("ft09src", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)                            
    results = {}
    for li, lev in enumerate(module.levels):
        colors = lev.get_data("cwU") or []
        tiles = sorted(
            [(s.x, s.y) for s in lev._sprites if getattr(s, "name", "") == "Hkx" or "NTi" in getattr(s, "tags", [])],
            key=lambda q: (q[1], q[0]),
        )
        constraints = []
        for glyph in [s for s in lev._sprites if "bsT" in getattr(s, "tags", [])]:
            center = int(glyph.pixels[1][1])
            for r in range(3):
                for c in range(3):
                    if (r, c) == (1, 1):
                        continue
                    pos = (glyph.x + (c - 1) * 4, glyph.y + (r - 1) * 4)
                    if pos not in tiles:
                        continue
                    constraints.append((pos, center, int(glyph.pixels[r][c]) == 0))
        results[li] = {"colors": colors, "tiles": tiles, "constraints": constraints}
    return results


def rendered_source_frames(src_path):
    p = pathlib.Path(src_path)
    spec = importlib.util.spec_from_file_location("ft09src", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)                            
    game = module.Ft09()
    for i in range(len(module.levels)):
        game.set_level(i)
        yield i, game.camera.render(game.current_level.get_sprites())


def board_from_recording(path):
    for line in pathlib.Path(path).open():
        if not line.strip():
            continue
        data = json.loads(line)["data"]
        if data.get("frame") is not None:
            return board_from_frame(data["frame"])
    raise ValueError(f"no frame in {path}")


def main(argv):
    if len(argv) > 2 and argv[1] == "oracle":
        for li, r in oracle_targets_from_source(argv[2]).items():
            print(
                f"level {li}: colors={r['colors']} tiles={len(r['tiles'])} "
                f"constraints={len(r['constraints'])}"
            )
        return

    if len(argv) > 2 and argv[1] == "validate":
        oracle = oracle_targets_from_source(argv[2])
        for li, grid in rendered_source_frames(argv[2]):
            summary = solve_summary(grid)
            print(
                f"level {li}: pixel_constraints={summary['constraints']} "
                f"oracle_constraints={len(oracle[li]['constraints'])} "
                f"pixel_tiles={summary['tiles']} oracle_tiles={len(oracle[li]['tiles'])} "
                f"unsatisfied={summary['unsatisfied']} clicks={summary['clicks'][:12]}"
            )
        return

    if len(argv) > 1:
        grid = board_from_recording(argv[1])
        summary = solve_summary(grid)
        print("from-pixels solve:")
        print(
            f"  constraints={summary['constraints']} tiles={summary['tiles']} "
            f"glyphs={summary['glyphs']} unsatisfied={summary['unsatisfied']}"
        )
        print(f"  clicks={summary['clicks']}")
        for detail in summary["details"]:
            print(f"  {detail}")
        return

    print("usage:")
    print("  ft09_csp_solver.py <recording.jsonl>")
    print("  ft09_csp_solver.py oracle <environment_files/.../ft09.py>")
    print("  ft09_csp_solver.py validate <environment_files/.../ft09.py>")


if __name__ == "__main__":
    main(sys.argv)
