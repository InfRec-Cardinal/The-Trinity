                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                             

import random
import re
from typing import Sequence
import chess
from game_arena.harness import parsers


def chess_soft_parser_v1(
    state_str: str, selected_action: str, spiel_legal_moves: Sequence[str]
) -> str | None:
  pass                                                
  if selected_action is None:
    return None

  selected_action = selected_action.strip()

  if not selected_action:
    return None

  if not selected_action.startswith("0-0") and selected_action[0].isdigit():
                                                       
                                                                    
                                                                          
                                                               
                                       
    match = re.search(r"(\d+)(\.{1,3})(.*)", selected_action)
    if match is not None:
      _, _, selected_action = match.groups()
    else:
      return None
                                                              
  selected_action = selected_action.lstrip()
                                                                               
                                                                              
                                                                                
                                                                             
             
  for char_to_remove in [
      ":",                                                       
      ".",                                 
      "*",
      ",",
      "&",
      "^",
      "\\",
      "<",
      ">",
      "{",
      "}",
      "[",
      "]",
      "?",                         
      "!",                         
  ]:
    selected_action = selected_action.replace(char_to_remove, "")

                                                                          
  selected_action = selected_action.removesuffix("ep")
                                                                             
                                                        

  board = chess.Board(state_str)
  maybe_legal_move_san = selected_action
                                                                          
                                                                               
                                                                           
  selected_uci = None
  try:
    selected_uci = board.parse_san(maybe_legal_move_san).uci()
  except ValueError as e:
    error_str = str(e)
                                                          
    if "ambiguous" in error_str:
      possible_moves_uci = []
      for legal_move in board.legal_moves:
        legal_move_san = board.san(legal_move)
        legal_move_san_short = legal_move_san.rstrip("+#")
        maybe_legal_move_san_short = maybe_legal_move_san.rstrip("+#")
                                                               
        if legal_move_san_short.startswith(
            maybe_legal_move_san_short[0]
        ) and legal_move_san_short.endswith(maybe_legal_move_san_short[-2:]):
          possible_moves_uci.append(legal_move.uci())
      if not possible_moves_uci:
        return None
      rng = random.Random(42)
      selected_uci = rng.choice(possible_moves_uci)
  if selected_uci is None:
    return None
  else:
    legal_move = board.parse_uci(selected_uci)
                                         
    selected_action = board.san(legal_move)
                                                   
  if selected_action not in spiel_legal_moves:
    return None
  return selected_action


class ChessSoftParser(parsers.SoftMoveParser):
  pass                    

  def _parse_selected_action(
      self, parser_input: parsers.TextParserInput
  ) -> str | None:
    return chess_soft_parser_v1(
        state_str=parser_input.state_str,
        selected_action=parser_input.text,
        spiel_legal_moves=parser_input.legal_moves,
    )
