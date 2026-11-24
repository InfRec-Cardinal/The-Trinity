import re, random
from typing import Any, Dict, List, Tuple, Optional, Union

import textarena as ta
from textarena.envs.FifteenPuzzle.renderer import create_board_str

class FifteenPuzzleEnv(ta.Env):
    pass                              
    def __init__(self, max_turns: int = 50):
        pass                                             
        super().__init__()
        self.max_turns = max_turns

    def get_board_str(self):
        return create_board_str(game_state=self.state.game_state)
    
    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                              
        self.state = ta.SinglePlayerState(num_players=num_players, seed=seed, max_turns=self.max_turns)                             
        self.board = self._generate_board()                             
        self.initial_board = [row[:] for row in self.board]                                  
        game_state = {"board": self.board, "rendered_board": self._render_board(self.board)}                        
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self._observe_current_state()                                         

    def _observe_current_state(self) -> None:
        pass                                                    
        r, c = self._get_empty_position()
        moves = {"[up]": r < 3, "[down]": r > 0, "[left]": c < 3, "[right]": c > 0}
        legal_moves = [m for m, valid in moves.items() if valid]
        msg = self.m("board", "current_board", board=self.state.game_state['rendered_board'], moves=', '.join(legal_moves))
        self.state.add_observation(message=msg, observation_type=ta.ObservationType.GAME_BOARD)

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        return self.m("player_prompt", "intro", player_id=player_id)
    
    def _generate_board(self):
        pass                                           
        tiles = list(range(1, 16)) + [None]
        random.shuffle(tiles)
        return [tiles[i:i + 4] for i in range(0, 16, 4)]                                                                         
    
    def _render_board(self, board):
        pass                                   
        rendered_board = ""
        for row in board:
            rendered_board += ' '.join(['__' if x is None else f"{x:2}" for x in row]) + "\n"
        return rendered_board
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                                
        player_id = self.state.current_player_id
        self.state.add_observation(from_id=player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)                                    
        action_search_pattern = re.compile(r"\[([a-zA-Z]+)\]")            
        match = action_search_pattern.search(action)

        if match is None:
            reason=self.m("invalid_move", "wrong_format", player_id=player_id)
            self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)

        else:
            direction = match.group(1)
            if not self._move(direction):
                reason=self.m("invalid_move", "illegal_move")
                self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)

            else:
                self.state.game_state["rendered_board"] = self._render_board(self.board)                             
                message=self.m("board", "game_board", board=self._render_board(self.board))
                self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_BOARD)
            
        if self._is_solved():                                 
            reason=self.m("outcome", "win", player_id=player_id)
            self.state.set_winners(player_ids=[player_id], reason=reason)
        elif self.state.check_turn_limit():
            pct_completion = self._get_percentage_completion()
            reason=self.m("outcome", "turn_limit", percent=pct_completion*100)
            self.state.set_outcome(reward=pct_completion, reason=reason)
        self._observe_current_state()                                        
        return self.state.step()
    
    def _is_solved(self) -> bool:
        pass                                           
        correct_tiles = list(range(1, 16)) + [None]
        current_tiles = [tile for row in self.board for tile in row]
        return current_tiles == correct_tiles

    def _move(self, direction: str) -> bool:
        pass                                                              
        empty_row, empty_col = self._get_empty_position()
        target_row, target_col = empty_row, empty_col

        if direction == 'up' and empty_row < 3:         target_row += 1
        elif direction == 'down' and empty_row > 0:     target_row -= 1
        elif direction == 'left' and empty_col < 3:     target_col += 1
        elif direction == 'right' and empty_col > 0:    target_col -= 1
        else:                                           return False                

                                                   
        self.board[empty_row][empty_col], self.board[target_row][target_col] = (self.board[target_row][target_col], self.board[empty_row][empty_col])
        return True
    
    def _get_empty_position(self):
        for r in range(4):
            for c in range(4):
                if self.board[r][c] is None:
                    return r, c

    def _get_percentage_completion(self) -> float:
        goal = list(range(1, 16)) + [None]
        correct = 0
        total = 0
                                                    
        flat_current = [tile for row in self.board for tile in row]
        flat_initial = [tile for row in self.initial_board for tile in row]
        for idx, goal_tile in enumerate(goal):
            if flat_initial[idx] == goal_tile: continue                                                             
            total += 1
            if flat_current[idx] == goal_tile:
                correct += 1
        return correct / total if total > 0 else 0.0