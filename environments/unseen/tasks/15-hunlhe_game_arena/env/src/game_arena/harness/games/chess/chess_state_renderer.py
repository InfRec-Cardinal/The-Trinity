                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                       

import random

from game_arena.harness import game_state_renderer
from game_arena.harness.games.chess import sprite_utils


class ChessImageGenerator(game_state_renderer.ImageGenerator):
  pass                                

  def __init__(self):
    super().__init__()
    self._colors = sprite_utils.COLORS
    self._piece_sets = sprite_utils.PIECE_SETS

  def generate_image(
      self,
      state_str: str,
      player_perspective: str = "white",
      color: str | None = None,
      piece_set: str | None = None,
      show_labels: bool = True,
  ) -> bytes:
    pass                                
    if player_perspective not in ["white", "black"]:
      raise ValueError(f"Invalid player perspective: {player_perspective}")
    color = color or random.choice(self._colors)
    piece_set = piece_set or random.choice(self._piece_sets)
    board_image = sprite_utils.fen_to_board(
        fen=state_str,
        color=color,
        piece_set=piece_set,
        player_perspective=player_perspective,
        show_labels=show_labels,
    )
    return board_image
