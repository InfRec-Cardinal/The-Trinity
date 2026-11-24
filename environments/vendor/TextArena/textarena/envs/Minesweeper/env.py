import re, random
from collections import deque
from typing import Optional, Tuple, List, Dict, Any

import textarena as ta
from textarena.envs.Minesweeper.renderer import create_board_str

class MinesweeperEnv(ta.Env):
    def __init__(self, rows: int=8, cols: int=8, num_mines: int=10, max_turns: int=100):
        pass             
                                          
                                             
                                                
           
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.max_turns = max_turns

    def get_board_str(self):
        return create_board_str(self.grid, self.revealed, self.flags)
    
    def reset(self, num_players: int, seed: Optional[int]=None):
        self.state = ta.SinglePlayerState(num_players=num_players, seed=seed, max_turns=self.max_turns)                              

                                    
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.flags = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.first_move = True                                                     

                               
        game_state = {
            "grid": self.grid, 
            "revealed": self.revealed, 
            "first_move": self.first_move, 
            "rendered_board": self._render_board()}
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self.state.add_observation(message=self.m("board", "game_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)

    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        prompt = self.m("player_prompt", "intro")                                
        return prompt

    def _observe_current_state(self) -> None:
        pass                                                
           

        self.state.add_observation(
            message=self.m("board", "current_board", board=self._render_board()),
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def _render_board(self) -> str:
        pass                         
        board_str = "   " + " ".join([str(c).rjust(2) for c in range(self.cols)]) + "\n"
        for r in range(self.rows):
            row_str = f"{r:2} "
            for c in range(self.cols):
                if self.revealed[r][c]:
                    if self.grid[r][c] == -1:
                        row_str += " * "
                    else:
                        row_str += f" {self.grid[r][c]} "
                else:
                    row_str += " . "
            board_str += row_str + "\n"
        return board_str
        
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)                          
        match = re.compile(r"\[(\d+)\s(\d+)\]").search(action)             
        if match is None:
            self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "wrong_format"))
        else:
            row, col = int(match.group(1)), int(match.group(2))
            if not (0 <= row < self.rows and 0 <= col < self.cols):
                self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "out_of_bounds"))
            else:
                if self.revealed[row][col]:
                    self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "already_revealed", row=row, col=col))
                else:
                    if self.first_move:                         
                        self.clear_all_flags()
                        self.setup_mines(row, col)
                        self.initial_move_pos = (row, col)                                   
                        self.first_move = False
                    
                    queue = deque([(row, col)])                                            
                    self.revealed[row][col] = True                                                 
                    while queue:
                        current_row, current_col = queue.popleft()
                                              
                        if self.grid[current_row][current_col] == -1:
                            pct_complete = self._get_percentage_completion()
                            self.revealed[row][col] = False                                                   
                            self.state.set_invalid_move(reward=pct_complete, reason=self.m("invalid_move", "hit_mine", row=current_row, col=current_col))

                                                                                           
                        if self.grid[current_row][current_col] == 0:
                            for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                                neighbor_row, neighbor_col = current_row + dr, current_col + dc
                                                                                         
                                if 0 <= neighbor_row < self.rows and 0 <= neighbor_col < self.cols:
                                    if not self.revealed[neighbor_row][neighbor_col]:
                                        self.revealed[neighbor_row][neighbor_col] = True                                         
                                        queue.append((neighbor_row, neighbor_col))

                    self.state.add_observation(
                        message=self.m("game_action", "revealed", row=row, col=col),
                        observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
                    )
                                                                                                                                                
       
        self.state.game_state["rendered_board"] = self._render_board()                              

                                          
        if self._is_solved():
            self.state.set_outcome(reward=1, reason=self.m("outcome", "win"))
        elif self.state.check_turn_limit():
            pct_complete = self._get_percentage_completion()
            self.state.set_outcome(reward=pct_complete, reason=self.m("outcome", "turn_limit", percent=round(pct_complete * 100)))
            
        self._observe_current_state()                                              
        
        return self.state.step()

    def _get_percentage_completion(self) -> float:
        pass                                                                                              
        if self.first_move:
                                                      
            return 0.0
        
                                                                            
        safe_total_after_initial = 0
        revealed_safe_after_initial = 0
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != -1:             
                                                                                 
                    was_initially_revealed = self._was_in_initial_safe_zone(r, c)
                    
                    if not was_initially_revealed:
                        safe_total_after_initial += 1
                        if self.revealed[r][c]:
                            revealed_safe_after_initial += 1
        
        return revealed_safe_after_initial / safe_total_after_initial if safe_total_after_initial > 0 else 1.0
    
    def _was_in_initial_safe_zone(self, row: int, col: int) -> bool:
        pass                                                                     
        if not hasattr(self, 'initial_move_pos'):
            return False
        
        initial_row, initial_col = self.initial_move_pos
        
                                                                               
        if (initial_row - 1 <= row <= initial_row + 1 and 
            initial_col - 1 <= col <= initial_col + 1):
            return True
        
                                                                                        
                                                                                     
                                                                                
        return self._would_be_revealed_initially(row, col, initial_row, initial_col)
    
    def _would_be_revealed_initially(self, target_row: int, target_col: int, start_row: int, start_col: int) -> bool:
        pass                                                               
                                                                         
        temp_revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        queue = deque([(start_row, start_col)])
        temp_revealed[start_row][start_col] = True
        
        while queue:
            current_row, current_col = queue.popleft()
            
                                                                               
            if self.grid[current_row][current_col] == 0:
                for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                    neighbor_row, neighbor_col = current_row + dr, current_col + dc
                    if 0 <= neighbor_row < self.rows and 0 <= neighbor_col < self.cols:
                        if not temp_revealed[neighbor_row][neighbor_col] and self.grid[neighbor_row][neighbor_col] != -1:
                            temp_revealed[neighbor_row][neighbor_col] = True
                            queue.append((neighbor_row, neighbor_col))
        
        return temp_revealed[target_row][target_col]

    
    def setup_mines(self, safe_row: int, safe_col: int):
        mines = set()
        while len(mines) < self.num_mines:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
                                                  
            if (r, c) not in mines and (r < safe_row - 1 or r > safe_row + 1 or c < safe_col - 1 or c > safe_col + 1):
                mines.add((r, c))
                self.grid[r][c] = -1                        
        self.calculate_adjacent_numbers()

    def calculate_adjacent_numbers(self):
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1:
                    continue
                mine_count = sum((0 <= r + dr < self.rows and 0 <= c + dc < self.cols and self.grid[r + dr][c + dc] == -1) for dr, dc in directions)
                self.grid[r][c] = mine_count

    def clear_all_flags(self):
        self.flags = [[False for _ in range(self.cols)] for _ in range(self.rows)]

    def _is_solved(self) -> bool:
                                                        
        return all(self.revealed[r][c] for r in range(self.rows) for c in range(self.cols) if self.grid[r][c] != -1)