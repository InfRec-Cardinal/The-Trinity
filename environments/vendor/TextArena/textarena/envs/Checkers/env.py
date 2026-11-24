import re
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta
from textarena.envs.Checkers.renderer import create_board_str

class CheckersEnv(ta.Env):
    def __init__(self, max_turns: int = 50):
        pass             
                                                                                    
           
        self.max_turns = max_turns

    def get_board_str(self): return create_board_str(game_state=self.state.game_state)
    def reset(self, num_players: int, seed: Optional[int] = None):
        self.state = ta.TwoPlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)
        self.state.reset(game_state={"board": self._initialize_board()}, player_prompt_function=self._prompt, role_mapping={0:"Red", 1:"Black"})
        self.state.add_observation(message=self.m("board", "current_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)

    def _initialize_board(self) -> List[List[str]]: return [['b' if row < 3 and (row + col) % 2 == 1 else 'r' if row > 4 and (row + col) % 2 == 1 else '.' for col in range(8)] for row in range(8)]
    def _render_board(self) -> str:
        header = "\n     " + "  ".join(chr(ord('a') + col) for col in range(8)) + "\n"
        divider = "   +" + "-" * 25 + "\n"
        rows = "\n".join(f" {row} |" + "".join(f" {self.state.game_state['board'][row][col]} " for col in range(8)) for row in range(8))
        return header + divider + rows + "\n"

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        color = 'Red' if player_id==0 else 'Black'
        return self.m("player_prompt", "intro", player_id=player_id, color=color)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        self._execute_player_move(action)
        self._check_gameover()
        self.state.add_observation(message=self.m("board", "current_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)
        return self.state.step()

    def _execute_player_move(self, action: str):
        pass                                                                                               
        match = re.compile(r"\[\s*([a-h])\s*([0-7])\s*([a-h])\s*([0-7])\s*\]", re.IGNORECASE).search(action.strip())
        if not match:
            self.state.set_invalid_move(reason=self.m("invalid_move", "wrong_format")); return
        col_from = ord(match.group(1).lower()) - ord('a')
        row_from = int(match.group(2))
        col_to   = ord(match.group(3).lower()) - ord('a')
        row_to   = int(match.group(4))
        if self._is_valid_move(self.state.current_player_id, row_from, col_from, row_to, col_to):
            self._move_piece(self.state.current_player_id, row_from, col_from, row_to, col_to)
        else:
            self.state.set_invalid_move(reason=self.m("invalid_move", "illegal",
                                        move=self._to_notation(row_from, col_from, row_to, col_to)))

    def _to_notation(self, r1: int, c1: int, r2: int, c2: int) -> str:
        return f"{chr(ord('a')+c1)}{r1}{chr(ord('a')+c2)}{r2}"

    def _is_valid_move(self, player_id: int, r1: int, c1: int, r2: int, c2: int) -> bool:
        pass                                                                                                                      
        if not (0 <= r1 < 8 and 0 <= c1 < 8 and 0 <= r2 < 8 and 0 <= c2 < 8):
            return False                       
        piece = self.state.game_state['board'][r1][c1]; target = self.state.game_state['board'][r2][c2]
        if player_id == 0:                        
            if piece not in ['r', 'R']: return False                                   
        else:
            if piece not in ['b', 'B']: return False                                   

        if target != '.': return False                              
                                                             
        dr = r2 - r1; dc = abs(c2 - c1)
        if piece in ['R', 'B']:                                                           
            if abs(dr) == 1 and dc == 1: return True
            if abs(dr) == 2 and dc == 2: return self._is_valid_capture(r1, c1, r2, c2)                                                        
            return False
        else:                                                         
            direction = -1 if piece == 'r' else 1                                      
            if dr == direction and dc == 1: return True                     
            if dr == 2 * direction and dc == 2: return self._is_valid_capture(r1, c1, r2, c2)                 
            return False

    def _is_valid_capture(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        mid_r = (r1 + r2) // 2
        mid_c = (c1 + c2) // 2
        moving_piece = self.state.game_state["board"][r1][c1]
        jumped_piece = self.state.game_state["board"][mid_r][mid_c]
        if moving_piece.lower() == 'r' and jumped_piece.lower() == 'b': return True
        if moving_piece.lower() == 'b' and jumped_piece.lower() == 'r': return True
        return False

    def _move_piece(self, player_id: int, r1: int, c1: int, r2: int, c2: int):
        piece = self.state.game_state["board"][r1][c1]
        self.state.game_state["board"][r1][c1] = '.'
        self.state.game_state["board"][r2][c2] = piece

                                               
        if abs(r2 - r1) == 2:
            mid_r = (r1 + r2) // 2
            mid_c = (c1 + c2) // 2
            self.state.game_state["board"][mid_r][mid_c] = '.'

                           
        if piece == 'r' and r2 == 0:    self.state.game_state["board"][r2][c2] = 'R'                    
        elif piece == 'b' and r2 == 7:  self.state.game_state["board"][r2][c2] = 'B'                      
        self.state.add_observation(message=self.m("game_action", "moved", player_id=player_id, move=self._to_notation(r1, c1, r2, c2)), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)                         

    def _check_gameover(self):
        red_pieces = sum(cell.lower() == 'r' for row in self.state.game_state["board"] for cell in row)
        black_pieces = sum(cell.lower() == 'b' for row in self.state.game_state["board"] for cell in row)
        if red_pieces == 0: self.state.set_winner(player_id=1, reason=self.m("outcome", "red_no_pieces")); return
        if black_pieces == 0: self.state.set_winner(player_id=0, reason=self.m("outcome", "black_no_pieces")); return
                                                                 
        if not self._has_legal_move(1 - self.state.current_player_id):                        
            self.state.set_winner(player_id=self.state.current_player_id, reason=self.m("outcome", "no_moves", player_id=1 - self.state.current_player_id)); return
        if not self._has_legal_move(self.state.current_player_id):                        
            self.state.set_winner(player_id=1-self.state.current_player_id, reason=self.m("outcome", "no_moves", player_id=self.state.current_player_id)); return
        if self.state.check_turn_limit(): self.state.set_draw(reason=self.m("outcome", "draw"))

    def _has_legal_move(self, player_id: int) -> bool:
        for r in range(8):
            for c in range(8):
                piece = self.state.game_state['board'][r][c]
                if player_id == 0 and piece in ['r', 'R']:
                    if self._can_piece_move(r, c): return True
                elif player_id == 1 and piece in ['b', 'B']:
                    if self._can_piece_move(r, c): return True
        return False

    def _can_piece_move(self, r: int, c: int) -> bool:
        piece = self.state.game_state['board'][r][c]
        if piece == '.': return False
        if piece in ['R', 'B']: directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]                                          
        else:                   directions = [(-1, -1), (-1, 1)] if piece=="r" else [(1, -1), (1, 1)]                                                        
                                                  
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8 and self.state.game_state['board'][nr][nc] == '.': return True
            nr2, nc2 = r + 2*dr, c + 2*dc                            
            if 0 <= nr2 < 8 and 0 <= nc2 < 8 and self.state.game_state['board'][nr2][nc2] == '.':
                jumped = self.state.game_state['board'][r + dr][c + dc]
                if piece.lower() == 'r' and jumped.lower() == 'b': return True
                if piece.lower() == 'b' and jumped.lower() == 'r': return True
        return False