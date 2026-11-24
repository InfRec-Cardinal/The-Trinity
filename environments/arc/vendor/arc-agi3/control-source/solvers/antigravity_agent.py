import base64
import io
import json
import logging
import os
from collections import deque
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from arcengine import FrameData, GameAction, GameState
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from ..agent import Agent

logger = logging.getLogger(__name__)


class AntigravityActionResponse(BaseModel):
    reasoning: str = Field(description="Step-by-step analysis of the current frame, diffs, and plans.")
    action_mapping: Dict[str, str] = Field(
        description="Current verified mapping of what each action (ACTION1 to ACTION7) does."
    )
    hypotheses: List[str] = Field(description="Active hypotheses about game elements, colors, and rules.")
    current_goal: str = Field(description="The immediate subgoal we are working on.")
    game_action: Literal["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7", "RESET"] = Field(
        description="The action to execute."
    )
    x: Optional[int] = Field(default=0, description="Click target X coordinate (0-63), only used for ACTION6.")
    y: Optional[int] = Field(default=0, description="Click target Y coordinate (0-63), only used for ACTION6.")


def round_half_up(val: float) -> int:
    return int(val + 0.5) if val >= 0 else int(val - 0.5)


class AntigravityReasoningAgent(Agent):
    pass                                                                                                                    

    MAX_ACTIONS = 2000
    MODEL = "gpt-4o-mini"
    
    action_mapping: Dict[str, str]
    hypotheses: List[str]
    current_goal: str
    history_log: List[str]
    previous_grid: Optional[List[List[int]]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.action_mapping = {}
        self.hypotheses = ["Unknown game rules."]
        self.current_goal = "Discover what the simple inputs (ACTION1 to ACTION5, ACTION7) do."
        self.history_log = []
        self.previous_grid = None
        self.current_offline_target = None
        self.current_offline_subgoal = ""

                     
        self.base_shapes = [
                                  
            [[1, 1, 0],
             [0, 1, 1],
             [1, 0, 1]],
                                  
            [[0, 1, 0],
             [0, 1, 0],
             [1, 1, 1]],
                                  
            [[1, 0, 1],
             [1, 0, 1],
             [1, 1, 1]],
                                  
            [[0, 1, 1],
             [1, 0, 1],
             [0, 1, 0]],
                                  
            [[0, 1, 0],
             [1, 1, 0],
             [0, 1, 1]],
                                  
            [[1, 1, 1],
             [0, 0, 1],
             [1, 0, 1]]
        ]

        def rotate_clockwise(matrix):
            return [
                [matrix[2][0], matrix[1][0], matrix[0][0]],
                [matrix[2][1], matrix[1][1], matrix[0][1]],
                [matrix[2][2], matrix[1][2], matrix[0][2]]
            ]

        self.shape_rotations = {}
        for s_idx, base in enumerate(self.base_shapes):
            self.shape_rotations[s_idx] = {}
            curr = base
            for angle in [0, 90, 180, 270]:
                self.shape_rotations[s_idx][angle] = curr
                curr = rotate_clockwise(curr)

        self.dir_to_action = {
            (0, -1): "ACTION1",      
            (0, 1): "ACTION2",         
            (-1, 0): "ACTION3",        
            (1, 0): "ACTION4",          
        }
        self.action_to_dir = {
            GameAction.ACTION1: (0, -1),
            GameAction.ACTION2: (0, 1),
            GameAction.ACTION3: (-1, 0),
            GameAction.ACTION4: (1, 0),
        }

                                            
        self.discovered_walls = set()
        self.discovered_refills = set()
        self.discovered_exit_gates = {}
        self.discovered_rotation_switchers = set()
        self.discovered_shape_switchers = set()
        self.discovered_color_switchers = set()
        self.discovered_walkable = set()
        self.discovered_pistons = set()
        self.has_shape_switcher = False
        self.has_color_switcher = False
        self.has_rotation_switcher = False
        
        self.prev_steps = None
        self.last_action_taken = None
        self.last_player_pos = None
        self.step_in_run = 0
        self.heuristic_initialized = False
        self.current_level = 0
        self.tested_actions = set()
        self.prev_player_state = None
        self.current_decrement = 2

    def is_done(self, frames: List[FrameData], latest_frame: FrameData) -> bool:
        pass                                             
        return latest_frame.state in [GameState.WIN, GameState.GAME_OVER]

    def grid_to_visual_image(self, grid: List[List[int]], cell_size: int = 8, margin: int = 24) -> Image.Image:
        pass                                                                                
        if not grid or not grid[0]:
            return Image.new("RGB", (100, 100), "black")

        height = len(grid)
        width = len(grid[0])

        img_width = width * cell_size + margin
        img_height = height * cell_size + margin

        img = Image.new("RGB", (img_width, img_height), "black")
        draw = ImageDraw.Draw(img)

                                 
        colors = [
            (255, 255, 255),           
            (204, 204, 204),               
            (153, 153, 153),                   
            (102, 102, 102),             
            (51, 51, 51),                  
            (0, 0, 0),                 
            (229, 58, 163),              
            (255, 123, 204),                   
            (249, 60, 49),           
            (30, 147, 255),           
            (136, 216, 241),                 
            (255, 220, 0),               
            (255, 133, 27),              
            (146, 18, 49),               
            (79, 204, 48),              
            (163, 86, 214),              
        ]

                         
        for y in range(height):
            for x in range(width):
                color_idx = grid[y][x] % 16
                color = colors[color_idx]
                draw.rectangle(
                    [
                        margin + x * cell_size,
                        margin + y * cell_size,
                        margin + (x + 1) * cell_size - 1,
                        margin + (y + 1) * cell_size - 1
                    ],
                    fill=color
                )

                                                  
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

                                       
        for y in range(height):
            for x in range(width):
                x_pos = margin + x * cell_size
                y_pos = margin + y * cell_size
                draw.rectangle(
                    [x_pos, y_pos, x_pos + cell_size, y_pos + cell_size],
                    outline=(40, 40, 40),
                    width=1
                )

                                                    
        for i in range(0, max(width, height) + 1, 8):
            if i <= width:
                x_pos = margin + i * cell_size
                draw.line([(x_pos, margin), (x_pos, img_height)], fill=(255, 215, 0), width=1)             
                if font:
                    draw.text((x_pos - 4, 4), str(i), fill="white", font=font)

            if i <= height:
                y_pos = margin + i * cell_size
                draw.line([(margin, y_pos), (img_width, y_pos)], fill=(255, 215, 0), width=1)             
                if font:
                    draw.text((4, y_pos - 6), str(i), fill="white", font=font)

        return img

    def get_grid_diff(self, grid_a: Optional[List[List[int]]], grid_b: List[List[int]]) -> str:
        pass                                                                  
        if not grid_a:
            return "Initial frame / full reset (no previous comparison frame)."
        if len(grid_a) != len(grid_b) or len(grid_a[0]) != len(grid_b[0]):
            return f"Grid size changed from {len(grid_a[0])}x{len(grid_a)} to {len(grid_b[0])}x{len(grid_b)}."

        changes = []
        for y in range(len(grid_b)):
            for x in range(len(grid_b[0])):
                if grid_a[y][x] != grid_b[y][x]:
                    changes.append(f"({x},{y}): color {grid_a[y][x]} -> {grid_b[y][x]}")

        if not changes:
            return "No grid changes detected (blocked move or wall collision)."
        if len(changes) > 40:
            return f"{len(changes)} cells changed color (scrolling or major screen update)."
        return ", ".join(changes)

    def _match_shape_rotation(self, matrix):
        for s_idx in range(6):
            for angle in [0, 90, 180, 270]:
                if self.shape_rotations[s_idx][angle] == matrix:
                    return s_idx, angle
        return None, None

    def _simulate_push(self, start_x, start_y, pdx, pdy, walkable_cells, exit_gate_cells, current_matching_gate):
        cx, cy = start_x, start_y
        steps = 0
        while True:
            nx, ny = cx + pdx, cy + pdy
            if 0 <= nx < 12 and 0 <= ny < 12:
                is_passable = False
                if (nx, ny) in walkable_cells:
                    is_passable = True
                elif (nx, ny) in exit_gate_cells:
                    if (nx, ny) == current_matching_gate:
                        is_passable = True
                if not is_passable:
                    break
                cx, cy = nx, ny
                steps += 1
            else:
                break
        if steps == 0:
            return start_x - pdx, start_y - pdy
        return cx, cy

    def _bfs_path(self, start, target, walkable_cells, exit_gate_cells, current_matching_gate, pistons=None):
        if start == target:
            return []
        if pistons is None:
            pistons = {}
        queue = deque([(start[0], start[1], [])])
        visited = {start}
        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) == target:
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < 12 and 0 <= ny < 12:
                    lx, ly = nx, ny
                    if (nx, ny) in pistons:
                        pdx, pdy = pistons[(nx, ny)]
                        lx, ly = self._simulate_push(nx, ny, pdx, pdy, walkable_cells, exit_gate_cells, current_matching_gate)
                    
                    if (lx, ly) not in visited:
                        is_passable = False
                        if (nx, ny) == target or (lx, ly) == target:
                            if (nx, ny) in exit_gate_cells:
                                is_passable = ((nx, ny) == current_matching_gate)
                            elif (lx, ly) in exit_gate_cells:
                                is_passable = ((lx, ly) == current_matching_gate)
                            else:
                                is_passable = True
                        elif (nx, ny) in walkable_cells:
                            is_passable = True
                        elif (nx, ny) in exit_gate_cells:
                            is_passable = ((nx, ny) == current_matching_gate)
                        if is_passable:
                            visited.add((lx, ly))
                            queue.append((lx, ly, path + [(dx, dy)]))
        return None

    def choose_offline_action(self, latest_frame: FrameData, current_grid: List[List[int]], grid_diffs: str) -> GameAction:
        pass                                                             
        height = len(current_grid)
        width = len(current_grid[0]) if height > 0 else 0
        if height == 0 or width == 0:
            return GameAction.RESET

        self.step_in_run += 1
        target_colors = {8, 9, 12, 14}

        current_shape_switchers = set()
        current_color_switchers = set()
        current_rotation_switchers = set()

                                                                
        p_cell = None
        for r in range(12):
            for c in range(12):
                px = 4 + 5 * c
                py = 5 * r
                if py >= 60:
                    continue
                c12 = sum(1 for y in range(py, py+5) for x in range(px, px+5) if current_grid[y][x] == 12)
                c9  = sum(1 for y in range(py, py+5) for x in range(px, px+5) if current_grid[y][x] == 9)
                if c12 >= 8 and c9 >= 8:
                    p_cell = (c, r)
                    break
            if p_cell:
                break

                           
        if not p_cell:
            player_pixels = []
            for y in range(60):
                for x in range(64):
                    if current_grid[y][x] in {12, 9}:
                        player_pixels.append((x, y))
            if player_pixels:
                px = sum(p[0] for p in player_pixels) // len(player_pixels)
                py = sum(p[1] for p in player_pixels) // len(player_pixels)
                col = max(0, min(11, (px - 4) // 5))
                row = max(0, min(11, py // 5))
                p_cell = (col, row)

        if not p_cell:
            p_cell = (5, 8)

                                             
        if self.last_action_taken and self.last_action_taken in self.action_to_dir:
            if self.last_player_pos and p_cell == self.last_player_pos:
                dx, dy = self.action_to_dir[self.last_action_taken]
                blocked_cell = (self.last_player_pos[0] + dx, self.last_player_pos[1] + dy)
                if 0 <= blocked_cell[0] < 12 and 0 <= blocked_cell[1] < 12:
                                                                   
                    if (blocked_cell not in self.discovered_exit_gates
                        and blocked_cell not in self.discovered_rotation_switchers
                        and blocked_cell not in self.discovered_shape_switchers
                        and blocked_cell not in self.discovered_color_switchers
                        and blocked_cell not in self.discovered_pistons):
                        self.discovered_walls.add(blocked_cell)
                        if blocked_cell in self.discovered_walkable:
                            self.discovered_walkable.remove(blocked_cell)
                        if blocked_cell in self.discovered_refills:
                            self.discovered_refills.remove(blocked_cell)
                        logger.info(f"Blocked movement! Marked cell {blocked_cell} as Wall.")

        self.last_player_pos = p_cell

                                   
        for r in range(12):
            for c in range(12):
                if (c, r) in self.discovered_walls:
                    continue
                if c == 0 and r == 11:
                    self.discovered_walls.add((c, r))
                    continue
                px = 4 + 5 * c
                py = 5 * r
                if py >= 60:
                    continue

                counts = {}
                for y in range(py, py+5):
                    for x in range(px, px+5):
                        val = current_grid[y][x]
                        counts[val] = counts.get(val, 0) + 1

                                                           
                if counts.get(5, 0) == 25:
                    continue

                c3 = counts.get(3, 0)
                c4 = counts.get(4, 0)
                c5 = counts.get(5, 0)
                c11 = counts.get(11, 0)
                c1 = counts.get(1, 0)
                c0 = counts.get(0, 0)

                if (c, r) in self.discovered_rotation_switchers:
                    if c1 >= 1 and c3 >= 15:
                        current_rotation_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    continue

                if (c, r) in self.discovered_shape_switchers:
                    if c0 >= 1 and c3 >= 15:
                        current_shape_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    continue

                if (c, r) in self.discovered_color_switchers:
                    if sum(counts.get(col, 0) for col in target_colors) >= 3 and c3 >= 15:
                        current_color_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    continue

                if (c, r) == p_cell:
                    self.discovered_walkable.add((c, r))
                    if (c, r) in self.discovered_refills:
                        self.discovered_refills.remove((c, r))
                    continue

                                                         
                if c5 >= 10 and any(counts.get(col, 0) > 0 for col in target_colors):
                    goal_matrix = [[0]*3 for _ in range(3)]
                    g_color = None
                    for dy in range(3):
                        for dx in range(3):
                            val = current_grid[py + 1 + dy][px + 1 + dx]
                            if val in target_colors:
                                g_color = val
                                goal_matrix[dy][dx] = 1
                    g_shape, g_rot = self._match_shape_rotation(goal_matrix)
                    existing = self.discovered_exit_gates.get((c, r))
                    if existing:
                        if g_color is None:
                            g_color = existing["color"]
                        if g_shape is None:
                            g_shape = existing["shape"]
                            g_rot = existing["rotation"]
                    self.discovered_exit_gates[(c, r)] = {
                        "color": g_color,
                        "shape": g_shape,
                        "rotation": g_rot
                    }
                    continue

                                                                              
                if (c, r) in self.discovered_exit_gates and c5 < 10:
                    del self.discovered_exit_gates[(c, r)]



                if c1 >= 1 and c4 >= 10:
                    self.discovered_walls.add((c, r))
                elif c4 >= 15:
                    self.discovered_walls.add((c, r))
                elif c11 >= 8:
                    self.discovered_refills.add((c, r))
                    self.discovered_walkable.add((c, r))
                elif c1 >= 1 and c3 >= 15:
                    current_rotation_switchers.add((c, r))
                    self.discovered_rotation_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    self.has_rotation_switcher = True
                elif sum(counts.get(col, 0) for col in target_colors) >= 3 and c3 >= 15:
                    current_color_switchers.add((c, r))
                    self.discovered_color_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    self.has_color_switcher = True
                elif c0 >= 1 and c3 >= 15:
                    current_shape_switchers.add((c, r))
                    self.discovered_shape_switchers.add((c, r))
                    self.discovered_walkable.add((c, r))
                    self.has_shape_switcher = True
                elif c3 >= 15:
                    self.discovered_walkable.add((c, r))
                elif counts.get(5, 0) > 0:
                                                                    
                    pass
                else:
                    self.discovered_walls.add((c, r))

                                                 
        pistons = {}
        for r_p in range(12):
            for c_p in range(12):
                px_p = 4 + 5 * c_p
                py_p = 5 * r_p
                if py_p >= 60:
                    continue
                counts_p = {}
                for y_p in range(py_p, py_p+5):
                    for x_p in range(px_p, px_p+5):
                        val_p = current_grid[y_p][x_p]
                        counts_p[val_p] = counts_p.get(val_p, 0) + 1
                c4_p = counts_p.get(4, 0)
                c1_p = counts_p.get(1, 0)
                if c1_p >= 1 and c4_p >= 10:
                    has_bottom = sum(1 for x_p in range(5) if current_grid[py_p+4][px_p+x_p] == 1) >= 3
                    has_top = sum(1 for x_p in range(5) if current_grid[py_p][px_p+x_p] == 1) >= 3
                    has_left = sum(1 for y_p in range(5) if current_grid[py_p+y_p][px_p] == 1) >= 3
                    has_right = sum(1 for y_p in range(5) if current_grid[py_p+y_p][px_p+4] == 1) >= 3
                    
                    if has_bottom:
                        if r_p + 1 < 12:
                            pistons[(c_p, r_p + 1)] = (0, 1)
                    elif has_top:
                        if r_p - 1 >= 0:
                            pistons[(c_p, r_p - 1)] = (0, -1)
                    elif has_right:
                        if c_p + 1 < 12:
                            pistons[(c_p + 1, r_p)] = (1, 0)
                    elif has_left:
                        if c_p - 1 >= 0:
                            pistons[(c_p - 1, r_p)] = (-1, 0)
        self.discovered_pistons = set(pistons.keys())
        logger.info(f"Discovered Pistons: {pistons}")

                                                   
        player_color = None
        player_preview_matrix = [[0]*3 for _ in range(3)]
        for dy in range(3):
            for dx in range(3):
                val = current_grid[55 + 2*dy][3 + 2*dx]
                if val in target_colors:
                    player_color = val
                    player_preview_matrix[dy][dx] = 1
        player_shape, player_rot = self._match_shape_rotation(player_preview_matrix)

        if player_color is None: player_color = 9
        if player_shape is None: player_shape = 5
        if player_rot is None: player_rot = 270

        state_changed = False
        if hasattr(self, "prev_player_state") and self.prev_player_state is not None:
            state_changed = (self.prev_player_state != (player_color, player_shape, player_rot))
        self.prev_player_state = (player_color, player_shape, player_rot)

        logger.info(f"Decoded player: color={player_color}, shape={player_shape}, rot={player_rot} | state_changed={state_changed}")

                                     
        remaining_steps = sum(1 for x in range(13, 55) if current_grid[61][x] == 11)
        if self.prev_steps is not None:
            diff = self.prev_steps - remaining_steps
            if 0 < diff <= 4:
                self.current_decrement = diff
        self.prev_steps = remaining_steps
        decrement = self.current_decrement
        logger.info(f"Remaining Steps: {remaining_steps} | Decrement: {decrement}")

                                      
        best_gate = None
        best_gate_sw_actions = None
        if self.discovered_exit_gates:
            best_gate_cost = 9999
            color_order = [12, 9, 14, 8]
            r_order = [0, 90, 180, 270]

            for gate_pos, goal in self.discovered_exit_gates.items():
                g_color = goal["color"] if goal["color"] is not None else player_color
                g_shape = goal["shape"] if goal["shape"] is not None else player_shape
                g_rot = goal["rotation"] if goal["rotation"] is not None else player_rot

                s_visits = (g_shape - player_shape) % 6
                
                if g_color in color_order and player_color in color_order:
                    c_visits = (color_order.index(g_color) - color_order.index(player_color)) % 4
                else:
                    c_visits = 0

                if g_rot in r_order and player_rot in r_order:
                    r_visits = (r_order.index(g_rot) - r_order.index(player_rot)) % 4
                else:
                    r_visits = 0

                total_visits = s_visits + c_visits + r_visits
                dist = abs(gate_pos[0] - p_cell[0]) + abs(gate_pos[1] - p_cell[1])
                cost = dist + total_visits * 10

                if cost < best_gate_cost:
                    best_gate_cost = cost
                    best_gate = gate_pos
                    best_gate_sw_actions = {
                        "shape": s_visits,
                        "color": c_visits,
                        "rotation": r_visits
                    }

                                                                            
        target_cell = None
        subgoal = ""
        keep_target = False
        if self.current_offline_target is not None:
            if self.current_offline_subgoal == "refill":
                if self.current_offline_target in self.discovered_refills:
                    keep_target = True
            elif self.current_offline_subgoal == "shape":
                if best_gate_sw_actions and best_gate_sw_actions.get("shape", 0) > 0:
                    if self.current_offline_target in current_shape_switchers or (not current_shape_switchers and p_cell == self.current_offline_target):
                        keep_target = True
            elif self.current_offline_subgoal == "color":
                if best_gate_sw_actions and best_gate_sw_actions.get("color", 0) > 0:
                    if self.current_offline_target in current_color_switchers or (not current_color_switchers and p_cell == self.current_offline_target):
                        keep_target = True
            elif self.current_offline_subgoal == "rotation":
                if best_gate_sw_actions and best_gate_sw_actions.get("rotation", 0) > 0:
                    if self.current_offline_target in current_rotation_switchers or (not current_rotation_switchers and p_cell == self.current_offline_target):
                        keep_target = True
            elif self.current_offline_subgoal == "exit":
                if best_gate_sw_actions and self.current_offline_target == best_gate:
                    if best_gate_sw_actions.get("shape", 0) == 0 and best_gate_sw_actions.get("color", 0) == 0 and best_gate_sw_actions.get("rotation", 0) == 0:
                        keep_target = True
            elif self.current_offline_subgoal == "explore":
                if p_cell != self.current_offline_target:
                    keep_target = True

        if keep_target:
            target_cell = self.current_offline_target
            subgoal = self.current_offline_subgoal
        else:
            t_cell = None
            subg = ""

                                                                                       
                                                                                           
                                                                                          
            maintained_type = False
            if self.current_offline_subgoal in ("shape", "color", "rotation") and best_gate_sw_actions:
                sg_type = self.current_offline_subgoal
                curr_map = {
                    "shape": current_shape_switchers,
                    "color": current_color_switchers,
                    "rotation": current_rotation_switchers,
                }
                disc_map = {
                    "shape": self.discovered_shape_switchers,
                    "color": self.discovered_color_switchers,
                    "rotation": self.discovered_rotation_switchers,
                }
                
                if best_gate_sw_actions.get(sg_type, 0) > 0:
                    map_to_use = curr_map[sg_type] if curr_map[sg_type] else disc_map[sg_type]
                    if map_to_use:
                        nearest = min(map_to_use, key=lambda s: abs(s[0]-p_cell[0])+abs(s[1]-p_cell[1]))
                        t_cell = nearest
                        subg = sg_type
                        maintained_type = True

            if not maintained_type and best_gate_sw_actions:
                candidates = []
                if best_gate_sw_actions.get("shape", 0) > 0:
                    map_to_use = current_shape_switchers if current_shape_switchers else self.discovered_shape_switchers
                    if map_to_use:
                        s_cell = min(map_to_use, key=lambda s: abs(s[0]-p_cell[0])+abs(s[1]-p_cell[1]))
                        candidates.append((s_cell, "shape"))
                if best_gate_sw_actions.get("color", 0) > 0:
                    map_to_use = current_color_switchers if current_color_switchers else self.discovered_color_switchers
                    if map_to_use:
                        c_cell = min(map_to_use, key=lambda s: abs(s[0]-p_cell[0])+abs(s[1]-p_cell[1]))
                        candidates.append((c_cell, "color"))
                if best_gate_sw_actions.get("rotation", 0) > 0:
                    map_to_use = current_rotation_switchers if current_rotation_switchers else self.discovered_rotation_switchers
                    if map_to_use:
                        r_cell = min(map_to_use, key=lambda s: abs(s[0]-p_cell[0])+abs(s[1]-p_cell[1]))
                        candidates.append((r_cell, "rotation"))

                if candidates:
                    best_cand = min(candidates, key=lambda c: abs(c[0][0]-p_cell[0])+abs(c[0][1]-p_cell[1]))
                    t_cell = best_cand[0]
                    subg = best_cand[1]
                else:
                    t_cell = best_gate
                    subg = "exit"
            
            target_cell = t_cell
            subgoal = subg
            if target_cell is None:
                target_cell = best_gate
                subgoal = "exit"
            self.current_offline_target = target_cell
            self.current_offline_subgoal = subgoal

        logger.info(f"Target selected: cell={target_cell}, subgoal={subgoal} | best_gate={best_gate} | exit_gates={list(self.discovered_exit_gates.keys())}")

                                                
        bfs_walkable = set((c, r) for r in range(12) for c in range(12))
        bfs_walkable.difference_update(self.discovered_walls)

                              
        player_matches_gate = False
        if best_gate in self.discovered_exit_gates:
            goal = self.discovered_exit_gates[best_gate]
            g_color = goal["color"] if goal["color"] is not None else player_color
            g_shape = goal["shape"] if goal["shape"] is not None else player_shape
            g_rot = goal["rotation"] if goal["rotation"] is not None else player_rot
            if player_color == g_color and player_shape == g_shape and player_rot == g_rot:
                player_matches_gate = True

        curr_matching_gate = best_gate if player_matches_gate else None

                                               
        for gate in self.discovered_exit_gates:
            if gate != curr_matching_gate:
                bfs_walkable.discard(gate)

        def get_path_avoiding_refills(start, target, walkable_set):
            if subgoal != "refill" and self.discovered_refills:
                walkable_no_refills = set(walkable_set)
                for r_cell in self.discovered_refills:
                    if r_cell != start and r_cell != target:
                        walkable_no_refills.discard(r_cell)
                p = self._bfs_path(start, target, walkable_no_refills, self.discovered_exit_gates, curr_matching_gate, pistons=pistons)
                if p is not None:
                    return p
            return self._bfs_path(start, target, walkable_set, self.discovered_exit_gates, curr_matching_gate, pistons=pistons)

                                                                                        
        bfs_walkable_lax = set(bfs_walkable)
        if best_gate_sw_actions:
            if best_gate_sw_actions.get("shape", 0) == 0:
                for cell in current_shape_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_lax.discard(cell)
            if best_gate_sw_actions.get("color", 0) == 0:
                for cell in current_color_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_lax.discard(cell)
            if best_gate_sw_actions.get("rotation", 0) == 0:
                for cell in current_rotation_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_lax.discard(cell)

                                                                                   
        bfs_walkable_strict = set(bfs_walkable)
        if best_gate_sw_actions:
            if best_gate_sw_actions.get("shape", 0) == 0:
                for cell in self.discovered_shape_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_strict.discard(cell)
            if best_gate_sw_actions.get("color", 0) == 0:
                for cell in self.discovered_color_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_strict.discard(cell)
            if best_gate_sw_actions.get("rotation", 0) == 0:
                for cell in self.discovered_rotation_switchers:
                    if cell != p_cell and cell != target_cell:
                        bfs_walkable_strict.discard(cell)

        original_target_cell = target_cell
        path_strict = None
        target_strict = target_cell
        
                                   
        if p_cell == target_strict and subgoal in {"shape", "color", "rotation"} and state_changed:
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = p_cell[0] + dx, p_cell[1] + dy
                if 0 <= nx < 12 and 0 <= ny < 12:
                    is_floor = (
                        (nx, ny) in bfs_walkable_strict
                        and (nx, ny) not in self.discovered_rotation_switchers
                        and (nx, ny) not in self.discovered_shape_switchers
                        and (nx, ny) not in self.discovered_color_switchers
                        and (nx, ny) not in self.discovered_exit_gates
                    )
                    if is_floor:
                        neighbors.append((nx, ny))
            if not neighbors:
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = p_cell[0] + dx, p_cell[1] + dy
                    if 0 <= nx < 12 and 0 <= ny < 12:
                        if (nx, ny) in bfs_walkable_strict and (nx, ny) not in self.discovered_exit_gates:
                            neighbors.append((nx, ny))
            if neighbors:
                target_strict = neighbors[0]
            
        path_strict = get_path_avoiding_refills(p_cell, target_strict, bfs_walkable_strict)
        
        if path_strict is not None:
            path = path_strict
            target_cell = target_strict
            bfs_walkable = bfs_walkable_strict
            if target_strict != original_target_cell:
                logger.info(f"Stepping off target switcher (strict) to {target_strict} temporarily.")
        else:
                                     
                                    
            target_lax = target_cell
            if p_cell == target_lax and subgoal in {"shape", "color", "rotation"} and state_changed:
                neighbors = []
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = p_cell[0] + dx, p_cell[1] + dy
                    if 0 <= nx < 12 and 0 <= ny < 12:
                        is_floor = (
                            (nx, ny) in bfs_walkable_lax
                            and (nx, ny) not in self.discovered_rotation_switchers
                            and (nx, ny) not in self.discovered_shape_switchers
                            and (nx, ny) not in self.discovered_color_switchers
                            and (nx, ny) not in self.discovered_exit_gates
                        )
                        if is_floor:
                            neighbors.append((nx, ny))
                if not neighbors:
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = p_cell[0] + dx, p_cell[1] + dy
                        if 0 <= nx < 12 and 0 <= ny < 12:
                            if (nx, ny) in bfs_walkable_lax and (nx, ny) not in self.discovered_exit_gates:
                                neighbors.append((nx, ny))
                if neighbors:
                    target_lax = neighbors[0]
                    
            path = get_path_avoiding_refills(p_cell, target_lax, bfs_walkable_lax)
            target_cell = target_lax
            bfs_walkable = bfs_walkable_lax
            if target_lax != original_target_cell:
                logger.info(f"Stepping off target switcher (lax fallback) to {target_lax} temporarily.")

                                                                                   
        if path is None or len(path) == 0:
            logger.info("Main target unreachable or None. Trying frontier exploration.")
                                 
            frontier_cells = []
            for r in range(12):
                for c in range(12):
                    if (c, r) in self.discovered_walls or (c, r) in self.discovered_exit_gates or (c, r) in self.discovered_walkable:
                        continue
                                                         
                    has_walkable_neighbor = False
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = c + dx, r + dy
                        if 0 <= nx < 12 and 0 <= ny < 12:
                            if (nx, ny) in self.discovered_walkable:
                                has_walkable_neighbor = True
                                break
                    if has_walkable_neighbor:
                        frontier_cells.append((c, r))
            
                                                  
            frontier_cells.sort(key=lambda f: abs(f[0]-p_cell[0]) + abs(f[1]-p_cell[1]))
            
                                                                    
            for f_cell in frontier_cells:
                f_path = get_path_avoiding_refills(p_cell, f_cell, bfs_walkable)
                if f_path is not None and len(f_path) > 0:
                    path = f_path
                    target_cell = f_cell
                    subgoal = "explore"
                    logger.info(f"Frontier exploration: Path found to frontier {f_cell}")
                    break

                         
        need_refill_check = False
        steps_needed = 0
        if self.discovered_refills and subgoal != "refill":
            if path is None:
                need_refill_check = True
                steps_needed = 9999
            else:
                moves_to_target = len(path)
                dist_to_refill = 9999
                for r_cell in self.discovered_refills:
                    d = abs(r_cell[0] - target_cell[0]) + abs(r_cell[1] - target_cell[1])
                    if d < dist_to_refill:
                        dist_to_refill = d

                if self.discovered_refills:
                    if best_gate is not None and len(self.discovered_exit_gates) == 1 and target_cell == best_gate:
                        next_step_dist = 0
                    else:
                        next_step_dist = dist_to_refill
                else:
                    next_step_dist = 0
                
                steps_needed = (moves_to_target + next_step_dist) * decrement + 4
                if steps_needed >= remaining_steps:
                    need_refill_check = True

        if need_refill_check:
            closest_refill = None
            closest_refill_dist_to_target = 9999
            closest_refill_path_len = 9999
            for r_cell in self.discovered_refills:
                r_path = self._bfs_path(p_cell, r_cell, bfs_walkable, self.discovered_exit_gates, curr_matching_gate, pistons=pistons)
                if r_path is not None and len(r_path) * decrement <= remaining_steps:
                    d_to_target = abs(r_cell[0] - target_cell[0]) + abs(r_cell[1] - target_cell[1])
                    if d_to_target < closest_refill_dist_to_target:
                        closest_refill_dist_to_target = d_to_target
                        closest_refill_path_len = len(r_path)
                        closest_refill = r_cell
                    elif d_to_target == closest_refill_dist_to_target:
                        if len(r_path) < closest_refill_path_len:
                            closest_refill_path_len = len(r_path)
                            closest_refill = r_cell

            if closest_refill:
                logger.info(f"Low energy (needed {steps_needed} steps, have {remaining_steps}), redirecting to refill {closest_refill}")
                self.current_offline_target = closest_refill
                self.current_offline_subgoal = "refill"
                target_cell = closest_refill
                subgoal = "refill"
                path = self._bfs_path(p_cell, target_cell, bfs_walkable, self.discovered_exit_gates, curr_matching_gate, pistons=pistons)

                             
        if path is not None and len(path) == 0 and target_cell == p_cell:
                                                      
                                                             
            blocked_dir = None
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = p_cell[0] + dx, p_cell[1] + dy
                if not (0 <= nx < 12 and 0 <= ny < 12) or (nx, ny) in self.discovered_walls:
                    blocked_dir = (dx, dy)
                    break
            if blocked_dir:
                action = GameAction.from_name(self.dir_to_action[blocked_dir])
                action.reasoning = f"Offline Wait: Standing still at {p_cell} by moving {blocked_dir}"
                self.last_action_taken = action
                return action
            else:
                                                                                 
                neighbors = []
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = p_cell[0] + dx, p_cell[1] + dy
                    if 0 <= nx < 12 and 0 <= ny < 12:
                        if (nx, ny) in bfs_walkable and (nx, ny) not in self.discovered_exit_gates:
                            neighbors.append((dx, dy))
                if neighbors:
                    chosen_dir = neighbors[0]
                    action = GameAction.from_name(self.dir_to_action[chosen_dir])
                    action.reasoning = f"Offline Wait: Oscillating step to {(p_cell[0]+chosen_dir[0], p_cell[1]+chosen_dir[1])}"
                    self.last_action_taken = action
                    return action

        if path is None or len(path) == 0:
            logger.info("No BFS path found. Taking a random walkable step.")
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = p_cell[0] + dx, p_cell[1] + dy
                if 0 <= nx < 12 and 0 <= ny < 12:
                    if (nx, ny) in bfs_walkable and (nx, ny) not in self.discovered_exit_gates:
                        neighbors.append((dx, dy))
            if neighbors:
                import random
                chosen_dir = random.choice(neighbors)
                action = GameAction.from_name(self.dir_to_action[chosen_dir])
                action.reasoning = f"Offline Fallback: Random step to {(p_cell[0]+chosen_dir[0], p_cell[1]+chosen_dir[1])}"
                self.last_action_taken = action
                return action
            else:
                logger.info("No walkable neighbors. Resetting level.")
                self.last_action_taken = GameAction.RESET
                return GameAction.RESET

        first_step_dir = path[0]
        action = GameAction.from_name(self.dir_to_action[first_step_dir])
        action.reasoning = f"Offline Pathfinding: Navigating to {target_cell} (subgoal={subgoal})"
        self.last_action_taken = action
        return action

    def choose_action(self, frames: List[FrameData], latest_frame: FrameData) -> GameAction:
        pass                                                                                         
        if len(frames) <= 1 or latest_frame.state in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
                                                      
            self.discovered_walls.clear()
            self.discovered_refills.clear()
            self.discovered_exit_gates.clear()
            self.discovered_rotation_switchers.clear()
            self.discovered_shape_switchers.clear()
            self.discovered_color_switchers.clear()
            self.discovered_walkable.clear()
            self.discovered_pistons.clear()
            self.has_shape_switcher = False
            self.has_color_switcher = False
            self.has_rotation_switcher = False

            self.last_action_taken = None
            self.last_player_pos = None
            self.step_in_run = 0
            self.heuristic_initialized = True
            self.current_level = latest_frame.levels_completed
            self.tested_actions = set()
            self.prev_steps = None
            self.current_offline_target = None
            self.current_offline_subgoal = ""
            self.prev_player_state = None
            self.current_decrement = 2

            self.action_mapping = {}
            self.hypotheses = ["Game needs initialization."]
            self.current_goal = "Initialize the game by sending RESET."
            self.previous_grid = None
            if latest_frame.state in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
                return GameAction.RESET

        if latest_frame.full_reset:
            self.step_in_run = 0
            self.prev_steps = None
            self.current_offline_target = None
            self.current_offline_subgoal = ""
            self.last_action_taken = None
            self.last_player_pos = None
            self.previous_grid = None
            self.prev_player_state = None
            self.current_decrement = 2

                                    
        if self.heuristic_initialized and latest_frame.levels_completed != self.current_level:
            logger.info(f"Level transition detected: {self.current_level} -> {latest_frame.levels_completed}")
            self.current_level = latest_frame.levels_completed
            self.discovered_walls.clear()
            self.discovered_refills.clear()
            self.discovered_exit_gates.clear()
            self.discovered_rotation_switchers.clear()
            self.discovered_shape_switchers.clear()
            self.discovered_color_switchers.clear()
            self.discovered_walkable.clear()
            self.discovered_pistons.clear()
            self.has_shape_switcher = False
            self.has_color_switcher = False
            self.has_rotation_switcher = False

            self.last_player_pos = None
            self.step_in_run = 0
            self.previous_grid = None
            self.tested_actions = set()
            self.prev_steps = None
            self.current_offline_target = None
            self.current_offline_subgoal = ""
            self.prev_player_state = None
            self.current_decrement = 2

        current_grid = latest_frame.frame[-1] if latest_frame.frame else []
        grid_diffs = self.get_grid_diff(self.previous_grid, current_grid)

                                          
        api_key = os.getenv("OPENAI_API_KEY", "")
        is_offline = (
            not api_key
            or api_key == "your_openai_api_key_here"
            or os.getenv("OPERATION_MODE", "").strip().lower() == "offline"
        )
        if is_offline:
            action = self.choose_offline_action(latest_frame, current_grid, grid_diffs)
            self.previous_grid = current_grid
            return action

        self.previous_grid = current_grid

                                        
        img = self.grid_to_visual_image(current_grid)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        b64_image = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

                                           
        system_prompt = (
            "You are an AI agent playing a top-down pixel-art interactive game on a grid (max 64x64).\n"
            "COORDINATE SYSTEM:\n"
            "- Top-left corner is (0, 0).\n"
            "- X coordinate increases to the right. Y coordinate increases downwards.\n"
            "OBJECTIVE:\n"
            "- Discover the rules of the level, reach the exit/win condition with minimal actions, and avoid GAME_OVER.\n"
            "AVAILABLE CONTROLS:\n"
            "- Simple actions: ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, ACTION7.\n"
            "- Complex action: ACTION6 (requires clicking a target x,y coordinate).\n"
            "- RESET: Start or restart the level.\n\n"
            "EXPLORATION RULE:\n"
            "- First map out controls! Systematic exploration of ACTION1 to ACTION5, ACTION7 is crucial to find movement directions.\n"
            "- If an action does not change the frame, it may be blocked or not mapped. Do not repeat actions that did nothing."
        )

        available_action_names = [GameAction.from_id(aid).name for aid in latest_frame.available_actions]

        user_prompt = (
            f"Current state: {latest_frame.state.name}\n"
            f"Level index: {latest_frame.levels_completed}\n"
            f"Total actions taken: {self.action_counter}\n\n"
            f"Available actions for this turn: {available_action_names}\n"
            f"Current Action Mappings: {json.dumps(self.action_mapping)}\n"
            f"Current Hypotheses: {json.dumps(self.hypotheses)}\n"
            f"Current Subgoal: {self.current_goal}\n\n"
            f"Grid changes since last step:\n{grid_diffs}\n\n"
            "Analyze the attached grid image (which has coordinate labels on the edges and light gridlines) and diff text. "
            "Update your goal, action mappings, hypotheses, and choose your next action."
        )

                                       
        try:
            logger.info("Calling OpenAI Structured Output...")
            completion = self.client.beta.chat.completions.parse(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format=AntigravityActionResponse,
            )
            response = completion.choices[0].message.parsed
            if not response:
                raise ValueError("Structured response was None.")

                                 
            self.action_mapping = response.action_mapping
            self.hypotheses = response.hypotheses
            self.current_goal = response.current_goal
            logger.info(f"Agent reasoning: {response.reasoning}")
            logger.info(f"Chosen Action: {response.game_action} (Goal: {response.current_goal})")

            action = GameAction.from_name(response.game_action)
            if action.is_complex():
                action.set_data({"x": response.x, "y": response.y})
            action.reasoning = {
                "reasoning": response.reasoning,
                "current_goal": response.current_goal,
                "hypotheses": response.hypotheses,
                "action_mapping": response.action_mapping
            }
            return action

        except Exception as e:
            logger.error(f"Error during OpenAI API call: {e}. Falling back to Smart Heuristic Solver.", exc_info=True)
            fallback_action = self.choose_offline_action(latest_frame, current_grid, grid_diffs)
            return fallback_action
