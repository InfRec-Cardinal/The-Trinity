import re
from collections import defaultdict, deque
from typing import Optional, Dict, Tuple, List, Any

import textarena as ta


class LinesOfActionEnv(ta.Env):
    BOARD_N = 8
    FILES = "abcdefgh"
    RANKS = "12345678"
    MOVE_RE = re.compile(r"\s*\[?([a-h][1-8])[\s>]*([a-h][1-8])\]?\s*$", re.I | re.VERBOSE)

    @classmethod
    def coord_to_rc(cls, coord: str) -> Tuple[int, int]:
        f, r = coord[0].lower(), coord[1]
        return len(cls.RANKS) - int(r), cls.FILES.index(f)

    @classmethod
    def rc_to_coord(cls, r: int, c: int) -> str:
        return f"{cls.FILES[c]}{cls.RANKS[len(cls.RANKS) - 1 - r]}"

    def __init__(self):
        super().__init__()

    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.state.reset(game_state={"board": self._initial_board(), "halfmove_clock": 0, "rep_counter": defaultdict(int)}, player_prompt_function=self._prompt)
        self._update_repetition_hash()                          
        self._observe()

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        side  = 'O' if player_id == 0 else 'X'
        other = 'X' if side == 'O' else 'O'
        return self.m("player_prompt", "intro", player_id=player_id, side=side, other=other)
    def _render_board(self) -> str:
        hline = "  +" + "+".join(["---"] * self.BOARD_N) + "+"                       
        rows: List[str] = []
        rows.append("    " + "   ".join(list(self.FILES)))                   
        for r in range(self.BOARD_N):
            rank_lbl = list(reversed(self.RANKS))[r]
            rows.append(hline)                  
            cells = []            
            for c in range(self.BOARD_N):
                token = self.state.game_state["board"][r][c] if self.state.game_state["board"][r][c] else " "                 
                cells.append(f" {token} ")
            rows.append(f"{rank_lbl} |" + "|".join(cells) + f"| {rank_lbl}")
                                             
        rows.append(hline)
        rows.append("    " + "   ".join(list(self.FILES)))
        return "\n".join(rows)

    def _observe(self):
        self.state.add_observation(message=self.m("board", "current_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        side, enemy  = ('O','X') if self.state.current_player_id==0 else ('X','O')

                                                
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        
        m = self.MOVE_RE.search(action)
        if not m:
            self.state.set_invalid_move(self.m("invalid_move", "wrong_format"))
            self._observe()
            return self.state.step()

        frm_coord, to_coord = m.groups()
        fr, fc = self.coord_to_rc(frm_coord)
        tr, tc = self.coord_to_rc(to_coord)

                               
        if self.state.game_state["board"][fr][fc] != side:
            self.state.set_invalid_move(self.m("invalid_move", "no_piece", side=side, coord=frm_coord))
            self._observe()
            return self.state.step()

                                     
        dr, dc = tr - fr, tc - fc
        if dr == dc == 0:
            self.state.set_invalid_move(self.m("invalid_move", "identical"))
            self._observe()
            return self.state.step()

                                      
        if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
            self.state.set_invalid_move(self.m("invalid_move", "not_straight_or_diagonal"))
            self._observe()
            return self.state.step()

                                                 
        step_r, step_c = (dr > 0) - (dr < 0), (dc > 0) - (dc < 0)
        distance = max(abs(dr), abs(dc))
        if distance != self._count_pieces_on_line(fr, fc, step_r, step_c):
            self.state.set_invalid_move(self.m("invalid_move", "wrong_distance"))
            self._observe()
            return self.state.step()

                                          
        r, c = fr + step_r, fc + step_c
        while (r, c) != (tr, tc):
            if self.state.game_state["board"][r][c] == enemy:
                self.state.set_invalid_move(self.m("invalid_move", "enemy_blocks"))
                self._observe()
                return self.state.step()
            r += step_r
            c += step_c

                                 
        if self.state.game_state["board"][tr][tc] == side:
            self.state.set_invalid_move(self.m("invalid_move", "destination_own"))
            self._observe()
            return self.state.step()

                      
        captured = self.state.game_state["board"][tr][tc] == enemy
        self.state.game_state["board"][fr][fc] = ''
        self.state.game_state["board"][tr][tc] = side

        self.state.game_state["halfmove_clock"] = 0 if captured else self.state.game_state["halfmove_clock"] + 1
        self._update_repetition_hash()
        msg_key = "captured_suffix" if captured else "moved"
        self.state.add_observation(self.m("game_action", msg_key, player_id=self.state.current_player_id, **{"from": frm_coord, "to": to_coord}), ta.ObservationType.GAME_ACTION_DESCRIPTION)

                         
        if self._connected(side):                                           self.state.set_winner(self.state.current_player_id, reason=self.m("outcome", "win"))
        elif self.state.game_state["halfmove_clock"] >= 60:                 self.state.set_draw(reason=self.m("outcome", "draw_no_capture"))
        elif self.state.game_state["rep_counter"][self._pos_hash()] >= 3:   self.state.set_draw(reason=self.m("outcome", "draw_repetition"))

        self._observe()
        return self.state.step()

    def _initial_board(self) -> List[List[str]]:
        bd = [['' for _ in range(self.BOARD_N)] for _ in range(self.BOARD_N)]
        for i in range(1, self.BOARD_N - 1):
            bd[0][i] = 'O'          
            bd[self.BOARD_N-1][i] = 'O'             
            bd[i][0] = 'X'              
            bd[i][self.BOARD_N-1] = 'X'               
        return bd

    def _count_pieces_on_line(self, r: int, c: int, dr: int, dc: int) -> int:
        bd, N = self.state.game_state["board"], self.BOARD_N
        cnt = 1
                 
        nr, nc = r + dr, c + dc
        while 0 <= nr < N and 0 <= nc < N:
            if bd[nr][nc]: cnt += 1
            nr += dr; nc += dc
                  
        nr, nc = r - dr, c - dc
        while 0 <= nr < N and 0 <= nc < N:
            if bd[nr][nc]: cnt += 1
            nr -= dr; nc -= dc
        return cnt

    def _connected(self, side: str) -> bool:
        bd, N = self.state.game_state["board"], self.BOARD_N
        pieces = [(r, c) for r in range(N) for c in range(N) if bd[r][c] == side]
        if not pieces: return False
        q, seen = deque([pieces[0]]), {pieces[0]}
        dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        while q:
            r, c = q.popleft()
            for dr, dc in dirs:
                nr, nc = r+dr, c+dc
                if 0 <= nr < N and 0 <= nc < N and bd[nr][nc] == side and (nr,nc) not in seen:
                    seen.add((nr,nc)); q.append((nr,nc))
        return len(seen) == len(pieces)

                         
    def _pos_hash(self) -> str:
        bd = self.state.game_state["board"]
        side_to_move = str(self.state.current_player_id)
        flat = ''.join(cell or '.' for row in bd for cell in row)
        return flat + side_to_move

    def _update_repetition_hash(self):
        self.state.game_state["rep_counter"][self._pos_hash()] += 1
