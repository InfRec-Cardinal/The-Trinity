                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                    

import re
from typing import Sequence
from game_arena.harness import parsers


def connect_four_soft_parser(
    selected_action: str, spiel_legal_moves: Sequence[str] | None
) -> str | None:
  pass                                                    

                                                                           
                                                                          
                                                                  

       
                                                             
                                                                       

          
                                                                             
                                                               
     
  if selected_action is None:
    return None

  selected_action = selected_action.strip()
  if not selected_action:
    return None

  if spiel_legal_moves is None:
    return None

  match = re.search(r"(\d+)", selected_action)
  if match:
    column = match.group(1)
                                                             
                                                          
    for legal_move in spiel_legal_moves:
      if legal_move.endswith(column):
        return legal_move

  return None


class ConnectFourSoftParser(parsers.SoftMoveParser):
  pass                           

  def _parse_selected_action(
      self, parser_input: parsers.TextParserInput
  ) -> str | None:
    return connect_four_soft_parser(
        selected_action=parser_input.text,
        spiel_legal_moves=parser_input.legal_moves,
    )
