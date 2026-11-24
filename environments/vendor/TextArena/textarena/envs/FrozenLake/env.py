import re, random
from collections import deque
from typing import Optional, Dict, Tuple, List, Any

import textarena as ta

class FrozenLakeEnv(ta.Env):
    def __init__(self, size: int = 4, num_holes: int = 3, randomize_start_goal: bool = False):
        pass             
                                                             
                                                                                        
           
        self.size = size
        self.num_holes = num_holes
        self.cell_mapping = {i: (i // size, i % size) for i in range(size * size)}
        self.randomize_start_goal = randomize_start_goal
        
                         
        self.actions = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}

    def reset(self, num_players: int = 1, seed: Optional[int] = None):
        self.state = ta.SinglePlayerState(num_players=num_players, seed=seed, max_turns=100)
        grid, player_pos, goal_pos = self._generate_grid(randomize_start_goal=self.randomize_start_goal)                    
        self.state.reset(game_state={"grid": grid, "player_pos": player_pos, "goal_pos": goal_pos}, player_prompt_function=self._prompt)
        self._observe_current_state()

    def _generate_grid(self, randomize_start_goal: bool = False) -> List[List[str]]:
        pass                                                                                                      
        max_attempts = 100                          
        
                                                              
        total_cells = self.size * self.size
        available_cells = total_cells - 2                                    

                                         
        if self.randomize_start_goal:
            self.player_pos = random.choice([(0, 0), (0, self.size-1), (self.size-1, 0), (self.size-1, self.size-1)])                                              
            self.goal_pos = (self.size - 1 - self.player_pos[0], self.size - 1 - self.player_pos[1])                                     
        else:
                                                                   
            self.player_pos = (0, 0)
            self.goal_pos = (self.size - 1, self.size - 1)
        
        if self.num_holes >= available_cells:
            print(f"Warning: Too many holes requested ({self.num_holes}). Maximum possible is {available_cells-1}. Using maximum.")
            actual_holes = min(self.num_holes, available_cells - 1)                           
        else:
            actual_holes = self.num_holes
        
        for attempt in range(max_attempts):
            grid = [[' ' for _ in range(self.size)] for _ in range(self.size)]
            
                                                                    
            available_positions = []
            for r in range(self.size):
                for c in range(self.size):
                    if (r, c) not in [self.player_pos, self.goal_pos]:
                        available_positions.append((r, c))
            
                                                 
            hole_positions = random.sample(available_positions, actual_holes)
            
                                               
            for r, c in hole_positions:
                grid[r][c] = 'H'            
            
                                
            grid[self.goal_pos[0]][self.goal_pos[1]] = 'G'            
            
                                                              
            if self._has_valid_path(grid, self.player_pos, self.goal_pos):
                return grid, self.player_pos, self.goal_pos
        
                                                                                             
        print(f"Warning: Could not generate a solvable random grid with {actual_holes} holes after {max_attempts} attempts. Creating a safe fallback grid.")
        return self._create_fallback_grid(actual_holes), self.player_pos, self.goal_pos
    
    def _has_valid_path(self, grid: List[List[str]], start: Tuple[int, int], goal: Tuple[int, int]) -> bool:
        pass                                                             
        if grid[start[0]][start[1]] == 'H' or grid[goal[0]][goal[1]] == 'H': return False
        queue = deque([start])
        visited = {start}
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]                         
        
        while queue:
            r, c = queue.popleft()
            if (r, c) == goal: return True
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.size and 0 <= nc < self.size and 
                    (nr, nc) not in visited and grid[nr][nc] != 'H'):
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return False
    
    def _create_fallback_grid(self, num_holes: int) -> List[List[str]]:
        grid = [[' ' for _ in range(self.size)] for _ in range(self.size)]
                                                                                              
        safe_path = set()
                                                                           
                                                       
        pr, pc = self.player_pos
        gr, gc = self.goal_pos
                                                          
        current_r, current_c = pr, pc
                                 
        if pc < gc:              
            for c in range(pc, gc + 1): safe_path.add((current_r, c))
        else:             
            for c in range(gc, pc + 1): safe_path.add((current_r, c))
        
                                               
        if pr < gr:             
            for r in range(pr, gr + 1): safe_path.add((r, gc))
        else:           
            for r in range(gr, pr + 1): safe_path.add((r, gc))
        
                                                  
        available_for_holes = []
        for r in range(self.size):
            for c in range(self.size):
                if ((r, c) not in safe_path):
                    available_for_holes.append((r, c))
        
                     
        holes_to_place = min(num_holes, len(available_for_holes))
        if holes_to_place > 0:
            hole_positions = random.sample(available_for_holes, holes_to_place)
            for r, c in hole_positions:
                grid[r][c] = 'H'
        
                                                         
        grid[self.goal_pos[0]][self.goal_pos[1]] = 'G'  
        
        return grid

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        return self.m("player_prompt", "intro")

    def _observe_current_state(self) -> None:
        available_actions = ", ".join(["[up]", "[down]", "[left]", "[right]", "[w]", "[a]", "[s]", "[d]"])
        self.state.add_observation(message=self.m("board", "current_board", board=self._render_board(), actions=available_actions), observation_type=ta.ObservationType.GAME_BOARD)

    def _render_board(self) -> str:
        grid = self.state.game_state["grid"]
        player_pos = self.state.game_state["player_pos"]
        
                                                                   
        display_grid = [row[:] for row in grid]             
        pr, pc = player_pos
        
                                                 
        if display_grid[pr][pc] == 'G': display_grid[pr][pc] = 'P/G'
        else:                           display_grid[pr][pc] = 'P'
        
                                         
        cell_width = 3                       
        def build_hline() -> str:
            line_parts = ["-" * (cell_width + 2) for _ in range(self.size)]
            return "+" + "+".join(line_parts) + "+"
        lines = []
        lines.append(build_hline())
        
        for r in range(self.size):
            row_cells = []
            for c in range(self.size):
                cell_content = display_grid[r][c]
                cell_str = f" {cell_content:^{cell_width}} "
                row_cells.append(cell_str)
            row_line = "|" + "|".join(row_cells) + "|"
            lines.append(row_line)
            lines.append(build_hline())
        return "\n".join(lines)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                    
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)                          
        match = re.compile(r"\[\s*(up|down|left|right|w|a|s|d)\s*\]", re.IGNORECASE).search(action)                                                     
        if match is None: self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "wrong_format"))
        else:               
            raw_action = match.group(1).lower()
            wasd_mapping = {'w': 'up', 'a': 'left', 's': 'down', 'd': 'right'}                                 
            action_name = wasd_mapping.get(raw_action, raw_action)
            if action_name not in self.actions: self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "unknown_action", action=raw_action))
            else:                               self._execute_move(action_name)                   
        self._observe_current_state()                      
        if self.state.check_turn_limit():
            completion_pct = self._get_percentage_completion()
            self.state.set_outcome(reward=completion_pct, reason=self.m("outcome", "turn_limit", pct=round(completion_pct * 100)))
        return self.state.step()

    def _execute_move(self, action_name: str) -> None:
        pass                                                              
        dr, dc = self.actions[action_name]
        current_pos = self.state.game_state["player_pos"]
        new_r = current_pos[0] + dr
        new_c = current_pos[1] + dc
        
                      
        if not (0 <= new_r < self.size and 0 <= new_c < self.size):
            self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "hit_wall", action=action_name))
            return
        
                              
        new_pos = (new_r, new_c)
        self.state.game_state["player_pos"] = new_pos
        
                                          
        grid = self.state.game_state["grid"]
        cell_type = grid[new_r][new_c]
        
        self.state.add_observation(message=self.m("game_action", "moved", action=action_name, row=new_r, col=new_c), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        if cell_type == 'H':    self.state.set_outcome(reward=self._get_percentage_completion(), reason=self.m("outcome", "fell_in_hole", pct=round(self._get_percentage_completion() * 100)))                                                          
        elif cell_type == 'G':  self.state.set_outcome(reward=1.0, reason=self.m("outcome", "win"))                          
    
    def _get_percentage_completion(self) -> float:
        pass                                                                              
                                                                                
           
                                                                           
        start_pos = self.player_pos                             
        goal_pos = self.state.game_state["goal_pos"]                 
        current_pos = self.state.game_state["player_pos"]                            
        grid = self.state.game_state["grid"]
        max_distance = self._bfs_distance_ignoring_holes(start_pos, goal_pos, grid)                                                                               
        distance_traveled = self._bfs_distance_ignoring_holes(start_pos, current_pos, grid)                                                             
        
                                                                                              
        if max_distance == -1 or distance_traveled == -1:
            max_distance = abs(goal_pos[0] - start_pos[0]) + abs(goal_pos[1] - start_pos[1])
            distance_traveled = abs(current_pos[0] - start_pos[0]) + abs(current_pos[1] - start_pos[1])
        
                                         
                                                                                
        completion = min(distance_traveled / max_distance, 0.95) if max_distance > 0 else 0.0
        
                                                                 
        if current_pos != start_pos: completion = max(completion, 0.1)                           
        return completion

    def _bfs_distance_ignoring_holes(self, start: tuple, target: tuple, grid: list) -> int:
        pass                                                                                
                                                                           
                                     
           
        if start == target: return 0
        
        queue = deque([(start, 0)])                        
        visited = {start}
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]                         
        
        while queue:
            (r, c), dist = queue.popleft()
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < self.size and 0 <= nc < self.size): continue               
                if (nr, nc) in visited: continue                          
                visited.add((nr, nc))                                                                             
                if (nr, nc) == target: return dist + 1
                queue.append(((nr, nc), dist + 1))
        return -1                 