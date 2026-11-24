import re
from typing import Any, Dict, Optional, Tuple
import textarena as ta
from textarena.envs.Santorini.renderer import create_board_str

class SantoriniBaseFixedWorkerEnv(ta.Env):
    pass                                                                                 
    
                                                                            
    
              
                             
                              
    
              
                             
                              
                             
       

                                                          
    INITIAL_POSITIONS = {
        2: [
            [(2,1), (1,2)],                           
            [(3,2), (2,3)]                             
        ],
        3: [
            [(2,2), (1,2)],                           
            [(3,2), (1,3)],                            
            [(3,1), (3,3)]                            
        ]
    }

                   
    PLAYER_COLORS = ["Navy", "White", "Grey"]

    def __init__(self, is_open: bool=True, show_valid: bool=True, error_allowance: int=10):
        pass                                         
        
             
                                                                                 
                                                                              
                                                                                         
           
        self.is_open = is_open
        self.show_valid = show_valid
        self.error_allowance = error_allowance

                                                                                                           
                                                                                        
        self.move_pattern = re.compile(r"\[(N[12]|W[12]|G[12])([A-E][1-5])([A-E][1-5])([A-E][1-5])\]", re.IGNORECASE)

                          
        self.rows = 5
        self.cols = 5

    def reset(self, num_players: int, seed: Optional[int]=None):
        pass                                      
        if num_players not in [2, 3]:
            raise ValueError("Number of players must be 2 or 3")
            
        self.state = ta.FFAMultiPlayerState(
            seed=seed,
            num_players=num_players,
            max_turns=None,                              
            error_allowance=self.error_allowance                                         
        )

                              
                                             
                                            
                                                 
        self.board = [[(0, None) for _ in range(self.cols)] for _ in range(self.rows)]

                                                                 
        for player_id, positions in enumerate(self.INITIAL_POSITIONS[num_players]):
            for worker_num, (row, col) in enumerate(positions, 1):
                self.board[row][col] = (0, (player_id, worker_num))

        game_state = {
            "board": self.board,
            "valid_moves": self._get_valid_moves(0)                                        
        }

        self.state.reset(game_state=game_state, 
                         player_prompt_function=self._generate_player_prompt,
                         role_mapping={i: self.PLAYER_COLORS[i] for i in range(num_players)},
                         )

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        pass                                           
        color = self.PLAYER_COLORS[player_id]
        prompt = self.t("player_prompt", "intro", color=color, color_initial=color[0], _pid=player_id)

        if self.is_open:
            prompt += self.t("player_prompt", "board_state", board=create_board_str(self.board), _pid=player_id)

        if self.show_valid:
            prompt += self.t("player_prompt", "valid_moves", valid_moves=game_state['valid_moves'], _pid=player_id)

        return prompt

    def _get_valid_moves(self, player_id: int) -> str:
        pass                                             
        valid_moves = []
        
                               
        worker_positions = []
        for row in range(self.rows):
            for col in range(self.cols):
                if self.board[row][col][1] is not None:
                    if self.board[row][col][1][0] == player_id:
                        worker_positions.append((row, col, self.board[row][col][1][1]))

                         
        for worker_row, worker_col, worker_num in worker_positions:
                                                     
            for move_row in range(max(0, worker_row - 1), min(self.rows, worker_row + 2)):
                for move_col in range(max(0, worker_col - 1), min(self.cols, worker_col + 2)):
                    if self._is_valid_move(worker_row, worker_col, move_row, move_col):
                                                                              
                        temp_board = [row[:] for row in self.board]
                        worker_height = temp_board[worker_row][worker_col][0]
                        temp_board[worker_row][worker_col] = (worker_height, None)
                        temp_board[move_row][move_col] = (temp_board[move_row][move_col][0], (player_id, worker_num))
                        
                                                                               
                        for build_row in range(max(0, move_row - 1), min(self.rows, move_row + 2)):
                            for build_col in range(max(0, move_col - 1), min(self.cols, move_col + 2)):
                                                                                     
                                if self._is_valid_build(temp_board, 
                                                        move_row, move_col,
                                                        build_row, build_col):
                                                                                 
                                    color_prefix = self.PLAYER_COLORS[player_id][0]
                                    move = f"[{color_prefix}{worker_num}{chr(65+worker_row)}{worker_col+1}" \
                                          f"{chr(65+move_row)}{move_col+1}" \
                                          f"{chr(65+build_row)}{build_col+1}]"
                                    valid_moves.append(move)

        return ", ".join(valid_moves)

    def _is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        pass                        
        
                           
                                                              
                                                            
                                               
                                                                                         
        
             
                                                                     
                                                                        
                                            
                                               
            
                
                                                            
           
                                     
        if from_row == to_row and from_col == to_col:
            return False
            
                                          
        if abs(to_row - from_row) > 1 or abs(to_col - from_col) > 1:
            return False

                                          
        if self.board[to_row][to_col][1] is not None:
            return False

                                         
        if self.board[to_row][to_col][0] == 4:
            return False

                                 
        height_diff = self.board[to_row][to_col][0] - self.board[from_row][from_col][0]
        if height_diff > 1:
            return False

        return True

    def _is_valid_build(self, 
                        board, 
                        worker_row: int, 
                        worker_col: int, 
                        build_row: int, 
                        build_col: int) -> bool:
        pass                                                    
        
                            
                                                                  
                                                           
                                                            
        
             
                                      
                                                                        
                                                                           
                                                  
                                                     
            
                
                                                             
           
                                                       
        if abs(build_row - worker_row) > 1 or abs(build_col - worker_col) > 1:
            return False

                                     
        if build_row == worker_row and build_col == worker_col:
            return False
            
                                             
        if board[build_row][build_col][1] is not None:
            return False
            
                               
        if board[build_row][build_col][0] >= 4:
            return False
            
        return True

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                            
                        
        player_id = self.state.current_player_id
        self.state.add_observation(from_id=player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

                      
        if not self._execute_player_move(action=action):
            return self.state.step()                                    
        
                                            
        next_player = (player_id + 1) % self.state.num_players
        next_moves = self._get_valid_moves(next_player)
        self.state.game_state["valid_moves"] = next_moves
        
                               
        self._check_gameover()

                                                         
        if self.is_open:
            self.state.add_observation(
                from_id=ta.GAME_ID,
                to_id=-1,
                message=create_board_str(self.board),
                observation_type = ta.ObservationType.GAME_BOARD
            )

        return self.state.step()

    def _execute_player_move(self, action: str):
        pass                                                       
        player_id = self.state.current_player_id
        match = self.move_pattern.search(action.strip())

                                      
        if match is None:
            self.state.set_invalid_move(
                reason=self.m("invalid_move", "wrong_format")
            )
            return False
        

                                 
        worker_id = match.group(1)                                  
        worker_num = int(worker_id[1])                                 
        
                                        
        prefix_to_player = {'N': 0, 'W': 1, 'G': 2}
        expected_player = prefix_to_player[worker_id[0].upper()]
        
                                                    
        if player_id != expected_player:
            self.state.set_invalid_move(
                reason=self.m("invalid_move", "wrong_player", expected_color=self.PLAYER_COLORS[expected_player], player_color=self.PLAYER_COLORS[player_id])
            )
            return False
        source = match.group(2).upper()
        dest = match.group(3).upper()
        build = match.group(4).upper()

                             
        source_row = ord(source[0]) - 65
        source_col = int(source[1]) - 1
        dest_row = ord(dest[0]) - 65
        dest_col = int(dest[1]) - 1
        build_row = ord(build[0]) - 65
        build_col = int(build[1]) - 1

                                   
        if self.board[source_row][source_col][1] != (player_id, worker_num):
            self.state.set_invalid_move(
                reason=self.m("invalid_move", "no_worker", worker_num=worker_num, source=source)
            )
            return False

                       
                                                                                               
                                                                          
                                                                    
        if not self._is_valid_move(source_row, source_col, dest_row, dest_col):
                                             
            self.state.set_invalid_move(
                reason=self.m("invalid_move", "bad_move", source=source, dest=dest)
            )
            return False

                                                        
        temp_board = [row[:] for row in self.board]
        worker_height = temp_board[source_row][source_col][0]
        temp_board[source_row][source_col] = (worker_height, None)
        temp_board[dest_row][dest_col] = (temp_board[dest_row][dest_col][0], (player_id, worker_num))

                                                     
                                                                 
                                                                                
                                                                                
        if not self._is_valid_build(temp_board,
                                    dest_row, dest_col,
                                    build_row, build_col):
                                              
            self.state.set_invalid_move(
                reason=self.m("invalid_move", "bad_build", build=build)
            )
            return False

                     
        source_height = self.board[source_row][source_col][0]
        dest_height = self.board[dest_row][dest_col][0]
        
                                                                        
        self.board[source_row][source_col] = (source_height, None)                      
        self.board[dest_row][dest_col] = (dest_height, (player_id, worker_num))                    
        
                       
        build_height = self.board[build_row][build_col][0]
        if build_height == 3:
            self.board[build_row][build_col] = (4, None)              
        else:
            self.board[build_row][build_col] = (build_height + 1, None)

                      
        message = self.m("game_action", "moved", player_id=player_id, color=self.PLAYER_COLORS[player_id], worker_num=worker_num, source=source, dest=dest, build=build)
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message, observation_type = ta.ObservationType.GAME_ACTION_DESCRIPTION)
        
        return True

    def _check_gameover(self):
        pass                                                         
        
                         
                                                                          
                                             
           
        player_id = self.state.current_player_id

                                                     
        for row in range(self.rows):
            for col in range(self.cols):
                if (self.board[row][col][1] is not None and 
                    self.board[row][col][0] == 3):                             
                    winner_id = self.board[row][col][1][0]                               
                    self.state.set_winners(
                        player_ids=[winner_id],
                        reason=self.m("outcome", "win_level3", winner_id=winner_id, winner_color=self.PLAYER_COLORS[winner_id])
                    )
                    return

                                                     
        current_moves = self._get_valid_moves(player_id)
                                                                           
        if not current_moves:
                                                           
            next_player = (player_id + 1) % self.state.num_players
            self.state.set_winners(
                player_ids=[next_player],
                reason=self.m("outcome", "no_moves", loser_id=player_id, loser_color=self.PLAYER_COLORS[player_id], winner_id=next_player, winner_color=self.PLAYER_COLORS[next_player])
            )
            return

                                                  
        next_player = (player_id + 1) % self.state.num_players
        next_moves = self._get_valid_moves(next_player)
                                                                       
        if not next_moves:
                                                           
            self.state.set_winners(
                player_ids=[player_id],
                reason=self.m("outcome", "no_moves", loser_id=next_player, loser_color=self.PLAYER_COLORS[next_player], winner_id=player_id, winner_color=self.PLAYER_COLORS[player_id])
            )
            return
