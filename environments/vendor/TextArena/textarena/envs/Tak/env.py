import re, ast, random
from typing import Dict, Optional, List, Tuple

import textarena as ta

class TakEnv(ta.Env):
    pass                        

                                                                          
                                                         

                                                                             
                                                              
                                                                              
                                                                           
                                                                         

                                                                          
                                                                            

                                                                           
                                                                          
                                                                                   
                                                                               
                                                                                 
                                                                               
                                                                             
       
    def __init__(self, board_size: int = 4, stones: int = 15, capstones: int = 1, max_turns: int = 100):
        pass                                   

             
                                                        
                                                             
                                                         
                                                                                
                                                                              
                                            
           

        self.board_size = board_size
        self.stones = stones
        self.capstones = capstones
        self.max_turns = max_turns

        self.players = None
        self.board = None

    @property 
    def terminal_render_keys(self):
        return ["rendered_board"]

    def reset(self, num_players: int = 2, seed: Optional[int]=None):
        pass                                                
        
             
                                                       
           
                                    
        self.state = ta.TwoPlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)

                               
        self.board = self._generate_board()
        self.players = {
            0: {"stones": self.stones, "capstones": self.capstones},
            1: {"stones": self.stones, "capstones": self.capstones}
        }

                               
        game_state={"board": self.board, "rendered_board": self._render_board()}
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self._observe_current_state()
    
    def _generate_board(self):
        pass                                         
           
        board = [[[] for _ in range(self.board_size)] for _ in range(self.board_size)]
        return board

    def _render_board(self):
        pass                                                     
           
                                                           
        max_cell_width = max(
            len(self._format_stack(cell)) for row in self.board for cell in row
        )
        cell_width = max(max_cell_width, 5)                                             

                                   
        header = "      " + "   ".join(f"{i:^{cell_width}}" for i in range(self.board_size))

                                   
        separator = "     " + "-" * (self.board_size * (cell_width + 3) - 1)

                     
        rows = []
        for row_idx, row in enumerate(self.board):
                                           
            row_display = [self._pad_cell(self._format_stack(cell), cell_width) for cell in row]
            rows.append(f"{row_idx:>3} | " + " | ".join(row_display) + " |")
            rows.append(separator)

                                                                  
        board_string = "\n".join([header, separator] + rows)
        return board_string


    def _format_stack(self, stack):
        pass                                                      
           
        if not stack:
            return ""              
        return f"({len(stack)}) {'/'.join(stack)}"                             
    
                                                       
    def _pad_cell(self, content, cell_width):
        return content.center(cell_width)

                                                    
    def _generate_player_prompt(self, player_id, game_state):
        pass                                   
           
        return self.m("player_prompt", "intro", player_id=player_id)
    
    def _observe_current_state(self) -> None:
        pass                                                                                               
           
        board_str = self._render_board()
                                                                                  
        available_flat_stones = self.players[self.state.current_player_id]["stones"]
        available_capstones = self.players[self.state.current_player_id]["capstones"]
        self.state.add_observation(
            message=self.m("board", "current_state", board=board_str, flat_stones=available_flat_stones, capstones=available_capstones),
            observation_type=ta.ObservationType.GAME_BOARD
        )


    def step(self, action: str) -> Tuple[bool, Optional[ta.Info]]:
        pass                                          
        
             
                                               
            
                
                                           
                                         
           
                                 
        self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

                                
        action_search_pattern = re.compile(
            r"\[(place|move)\s"                                                 
            r"\((\d+,\d+|\s*)\)\s"                                               
            r"({.*?})\]"                                                   
        )                                                                  
        match = action_search_pattern.search(action)

        if not match:
                                 
            reason=self.m("invalid_move", "invalid_format", current_player_id=self.state.current_player_id)
            self.state.set_invalid_move(reason=reason)
        
        else:
                                        
            action, source, allocation = self.extract_values(match.groups())

            if action == "place":
                                                   
                if not self._is_valid_placement(allocation):
                                        
                    reason=self.m("invalid_move", "invalid_placement", current_player_id=self.state.current_player_id)
                    self.state.set_invalid_move(reason=reason)
                else:
                    self._apply_placement(allocation, self.state.current_player_id)
                    message=self.m("action", "placement", current_player_id=self.state.current_player_id, cells=list(allocation.keys()))
                    self.state.add_observation(from_id=-1, to_id=-1, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

            elif action == "move":
                                                                    
                if not self._is_valid_movement(source, allocation):
                                       
                    reason=self.m("invalid_move", "invalid_movement", current_player_id=self.state.current_player_id)
                    self.state.set_invalid_move(reason=reason)
                else:
                                     
                    self._apply_movement(source, allocation)
                    message=self.m("action", "movement", current_player_id=self.state.current_player_id, source=source, targets=list(allocation.keys()))
                    self.state.add_observation(from_id=-1, to_id=-1, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

            else:
                                 
                reason=self.m("invalid_move", "invalid_action", current_player_id=self.state.current_player_id)
                self.state.set_invalid_move(reason=reason)

            
            self.state.game_state["rendered_board"] = self._render_board()                             

                                                                                  
                                                                                  
        if not self.state.made_invalid_move and not self.state.done:
            cur = self.state.current_player_id                                                     
            opp = 1 - cur
            if self._check_win(cur):                                                    
                self.state.set_winner(player_id=cur, reason=self.m("outcome", "winner", current_player_id=cur))
            elif self._check_win(opp):                                                                                
                self.state.set_winner(player_id=opp, reason=self.m("outcome", "winner", current_player_id=opp))
            elif self._board_full() or self._out_of_pieces(0) or self._out_of_pieces(1):
                self._resolve_flat_count(capped=False)                                                
            elif self.state.turn + 1 >= self.state.max_turns:
                self._resolve_flat_count(capped=True)                                 

        result = self.state.step()
        self._observe_current_state()
        return result

    def _flat_counts(self) -> Dict[int, int]:
        pass                                                                                 
        counts = {0: 0, 1: 0}
        for row in self.board:
            for cell in row:
                if cell and cell[-1][0] == "F":
                    counts[int(cell[-1][-1])] += 1
        return counts

    def _board_full(self) -> bool:
        return all(cell for row in self.board for cell in row)

    def _out_of_pieces(self, player_id: int) -> bool:
        return self.players[player_id]["stones"] == 0 and self.players[player_id]["capstones"] == 0

    def _resolve_flat_count(self, capped: bool = False) -> None:
        pass                                                                     
        c = self._flat_counts()
        if c[0] == c[1]:
            key = "draw_capped" if capped else "draw"
            self.state.set_draw(reason=self.m("outcome", key, flats0=c[0], flats1=c[1]))
        else:
            winner = 0 if c[0] > c[1] else 1
            key = "flat_win_capped" if capped else "flat_win"
            self.state.set_winner(player_id=winner, reason=self.m("outcome", key, winner=winner, flats0=c[0], flats1=c[1]))

    def _check_win(self, player_id):
        pass                                                                          
                                                   

             
                                                     
                                                           
                                                                               

                
                                                              
           
        visited = set()
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]                         

        def is_valid_cell(row, col):
            pass                                            
            if 0 <= row < self.board_size and 0 <= col < self.board_size:
                stack = self.board[row][col]
                return stack and stack[-1].endswith(str(player_id)) and stack[-1][0] in ["F", "C"]
            return False

        def dfs(row, col, edges_reached):
            pass                                                                                   

                 
                                                
                                                                                

                    
                                                                                           
               
                                              
            if (row, col) in visited:
                return False

                                              
            visited.add((row, col))

                                                                       
            if row == 0:
                edges_reached.add("top")
            if row == self.board_size - 1:
                edges_reached.add("bottom")
            if col == 0:
                edges_reached.add("left")
            if col == self.board_size - 1:
                edges_reached.add("right")

                                                             
            if ("top" in edges_reached and "bottom" in edges_reached) or \
            ("left" in edges_reached and "right" in edges_reached):
                return True

                                       
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if is_valid_cell(new_row, new_col):
                                                                           
                    if dfs(new_row, new_col, edges_reached.copy()):
                        return True

            return False

                                                                           
        for col in range(self.board_size):
            if is_valid_cell(0, col):                                        
                if dfs(0, col, {"top"}):
                    return True

                                                                            
        for row in range(self.board_size):
            if is_valid_cell(row, 0):                                         
                if dfs(row, 0, {"left"}):
                    return True

        return False

    def _update_pieces(self, player_id, piece):
        pass                                                                 
           
        if piece[0][0] == "F" or piece[0][0] == "W":
            self.players[player_id]["stones"] -= 1
        else:
            self.players[player_id]["capstones"] -= 1
    
    def extract_values(self, matched_groups):
        pass                                                                      
        
             
                                                                           
            
                
                                                                   
           
        action, source, allocation = matched_groups
    
                                                                
        if source.strip():
            source = tuple(map(int, source.split(',')))                                   
        else:
            source = None                                    

        try:
            allocation_dict = self._convert_to_dict(allocation)
        except:
            return None, None, None

                                 
        return action, source, allocation_dict


    def _is_valid_placement(self, allocation):
        pass                                   
        if len(allocation.items()) != 1:
                                              
            return False
        row, col = list(allocation.keys())[0]
        piece = list(allocation.values())[0]

        if piece[0][0] == "C" and self.players[self.state.current_player_id]["capstones"] == 0:
                                
            return False
        elif piece[0][0] in ["F", "W"] and self.players[self.state.current_player_id]["stones"] == 0:
                             
            return False

        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
                                           
            return False
        
        if len(piece) != 1:
                                         
            return False
        
        if self.board[row][col]:
                                          
            return False
        
        if piece[0][0] not in ["F", "W", "C"]:
                                 
            return False
        
        if piece[0][-1] != str(self.state.current_player_id):
                                                          
            return False
        
        return True
    
    def _apply_placement(self, allocation, player_id):
                          
        row, col = list(allocation.keys())[0]
        piece = list(allocation.values())[0]
                                                             
        self.board[row][col].extend(piece)
        self._update_pieces(player_id, piece)

    
    def _is_valid_movement(self, source, allocation):
        pass                                  
        if source is None:                           
            return False
        
        source_row, source_col = source

        if source_col >= self.board_size or source_row >= self.board_size:                                   
            return False
        
        if not self.board[source_row][source_col]:                           
            return False
        
        source_type, source_player_id = self.board[source_row][source_col][-1][0], self.board[source_row][source_col][-1][-1]

        if source_player_id != str(self.state.current_player_id):                                                      
            return False
        
        source_stack = self.board[source_row][source_col]
        pieces_to_move = [value for values in allocation.values() for value in values]

        if len(pieces_to_move) > self.board_size:                                                                     
            return False

        if pieces_to_move != source_stack[-len(pieces_to_move):]:                                                           
            return False
        
        top_piece_type = source_stack[-1][0]

        if len(pieces_to_move) == 1:                                                                            
            target_row, target_col = list(allocation.keys())[0]

            if (abs(target_row - source_row) + abs(target_col - source_col)) != 1:                                         
                return False
            
            if target_row >= self.board_size or target_col >= self.board_size:                                   
                return False
            
            if top_piece_type == "C" and self.board[target_row][target_col] and self.board[target_row][target_col][-1][0] == "C":                                                  
                return False
            elif top_piece_type == "W" and self.board[target_row][target_col] and self.board[target_row][target_col][-1][0] in ["W", "C"]:                                            
                return False
            elif top_piece_type == "F" and self.board[target_row][target_col] and self.board[target_row][target_col][-1][0] in ["W", "C"]:                                                          
                return False

        else:
            for i, (target, pieces) in enumerate(allocation.items()):
                target_row, target_col = target
                if (abs(target_row - source_row) + abs(target_col - source_col)) != i + 1:                                         
                    return False
                
                if target_row >= self.board_size or target_col >= self.board_size:                                   
                    return False
                
                if self.board[target_row][target_col]:
                    if self.board[target_row][target_col][-1][0] == "C":                                              
                        return False
                    elif self.board[target_row][target_col][-1][0] == "W":                                          
                        return False
                
        return True
    
    def _apply_movement(self, source, allocation):
        pass                                   
        source_row, source_col = source
        source_stack = self.board[source_row][source_col]
        pieces_to_move = [value for values in allocation.values() for value in values]
        top_piece_type = source_stack[-1][0]

        if len(pieces_to_move) == 1:
            target_row, target_col = list(allocation.keys())[0]
            if self.board[target_row][target_col]:
                if top_piece_type == "C" and self.board[target_row][target_col][-1][0] == "W":                                   
                    self.board[target_row][target_col][-1] = "F" + self.board[target_row][target_col][-1][1]
            self.board[target_row][target_col].extend(pieces_to_move)
        else:
            for target, pieces in allocation.items():
                target_row, target_col = target
                self.board[target_row][target_col].extend(pieces)
        self.board[source_row][source_col] = source_stack[:-len(pieces_to_move)]            
    
    def _convert_to_dict(self, input_str):
        pass                                                                                             
                                                 
                                                
                                                 
           
                                                                  
        def add_quotes(match):
            return f"'{match.group(0)}'"
        
                                                                  
        input_str = re.sub(r'\b([A-Za-z0-9_]+)\b', add_quotes, input_str)
        
                                              
        try:
            parsed_dict = ast.literal_eval(input_str)
                                                                                             
            result_dict = {tuple(int(k) if k.isdigit() else k for k in key): [str(item) for item in value] for key, value in parsed_dict.items()}
            return result_dict
        except Exception as e:
            raise ValueError(f"Invalid input string: {input_str}") from e
