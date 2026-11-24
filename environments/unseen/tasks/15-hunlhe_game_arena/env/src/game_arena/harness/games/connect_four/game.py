                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                             

from game_arena.harness import base_game
from game_arena.harness.games.connect_four import prompt_generation
from game_arena.harness.games.connect_four import prompt_templates


game_notation = base_game.BaseGameNotation(
    state=""".......
.......
.......
.......
.......
......x
""",
    action="o2; o6; x0. The game begins with player x.",
    player_map={0: "x", 1: "o"},
    move_notation="zero-based column number",
    state_notation="ASCII notation",
)


class ConnectFourGameAdapter(base_game.OpenSpielGameAdapter):
  pass                            

  game_short_name = "connect_four"
  game_notation = game_notation
  prompt_generator = staticmethod(prompt_generation.generate_prompt)
  rethink_generator = prompt_templates.CONNECTX_RETHINK

  def get_string_and_board(self):
    pass                                                    
    board_str = self.native_state.to_string()
    board = [list(row) for row in board_str.strip().split("\n")]
    return board_str, board

  def get_prompt(self, player_perspective: int = 0):
    pass                                                
    board_str, _ = self.get_string_and_board()
    params = self.native_state.get_game().get_parameters()
    return self.prompt_generator(
        rows=int(params.get("rows", 6)),
        columns=int(params.get("columns", 7)),
        in_a_row=int(params.get("x_in_row", 4)),
        visual_board_state=board_str,
        player_name=game_notation.player_map[player_perspective],
    )
