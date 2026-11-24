                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                

from game_arena.harness import base_game


class TicTacToeGameAdapter(base_game.OpenSpielGameAdapter):
  pass                           

  game_short_name = "tic_tac_toe"
  game_notation = game_notation = base_game.BaseGameNotation(
      state="""x..
...
...
""",
      action="o(0,1); o(2,0); x(2,1). The game begins with player x.",
      player_map={0: "x", 1: "o"},
      move_notation="zero-based (row,col)",
      state_notation="ASCII notation",
  )
