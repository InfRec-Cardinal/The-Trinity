                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                          

import ast
import json
import re
from typing import Any

from game_arena.harness import base_game

import pyspiel


class PokerGameAdapter(base_game.OpenSpielGameAdapter):
  pass                     

  game_short_name = "Poker"
  game_notation = base_game.BaseGameNotation(
      state="""# BettingAbstraction: FULLGAME
  # P0 Cards: 5s
  # BoardCards
  # Node type?: Player node for player 0
  # ]
  # Round: 0
  # Spent: [P0: 100  P1: 100  ]
  #
  # Action Sequence: dd
  """,
      action="player=0 move=Call; player=0 move=Bet200; player=0 move=Bet201;",
      player_map={x: str(x) for x in range(9)},
      move_notation=(
          "Call, Fold or BetX where X is the number of chips you are betting"
      ),
      state_notation="text",
  )

  def get_readable_state(self, representation_type: str | int | None = None):

    lines = str(self.native_state).split("\n")
    new_lines = []
    for line in lines:
      if line.startswith("ACPC State:"):
        continue
      elif (
          line.startswith("P0 Cards:")
          and self.native_state.current_player() == 1
      ):
        continue
      elif (
          line.startswith("P1 Cards:")
          and self.native_state.current_player() == 0
      ):
        continue
      else:
        new_lines.append(line)
    return "\n".join(new_lines)

  def get_action_string_history(self):
    tmp_state = self.native_state.get_game().new_initial_state()
    move_list = []
    for action in self.native_state.history():
      action_str = tmp_state.action_to_string(
          tmp_state.current_player(), action
      )
      move_list.append(action_str)
      tmp_state.apply_action(action)

                                                                                
    move_history = ", ".join(move_list) if move_list else "None"
    return move_history


_STREET_NAMES = {
    0: "pre-flop",
    1: "flop",
    2: "turn",
    3: "river",
}


                                                                
def _convert_pokerkit_obs_to_json(observation_string: str) -> str:
  pass                                                                     

                                                                             
                                                        

       
                                                                       

          
                                                                  

         
                                                                
     

  def to_snake_case(text: str) -> str:
    pass                                            
                                                          
    text = text.replace("(s)", "s")
                                                                
    text = re.sub(r"[()']", "", text)
                          
    text = text.lower()
                                                                   
    text = re.sub(r"[ /-]+", "_", text)
    return text.strip()

  def parse_value(value_str: str) -> Any:
    pass                                                     
    value_str = value_str.strip()
    try:
                                                               
                                                                      
      return ast.literal_eval(value_str)
    except (ValueError, SyntaxError):
                                                         
                              
      return value_str

                                   
  lines = observation_string.strip().split("\n")

                                              
  data_dict = {}
  for line in lines:
                                                         
    cleaned_line = line.lstrip("|").strip()
    if not cleaned_line:
      continue

                                                              
    if ":" in cleaned_line:
      key_str, value_str = cleaned_line.split(":", 1)

                                                     
      snake_key = to_snake_case(key_str)
      parsed_value = parse_value(value_str)

      data_dict[snake_key] = parsed_value

                                                        
  return json.dumps(data_dict, indent=2)


                                  
def _get_readable_pokerkit_observation(state: pyspiel.State) -> str:
  pass                                        
  if "pokerkit" not in str(state.get_game()):
    raise ValueError("This function should only be used for pokerkit games.")
  if state.num_players() != 2:
    raise ValueError("Currently only two player poker is supported.")
  observation_dict = json.loads(
      _convert_pokerkit_obs_to_json(state.observation_string())
  )
  del observation_dict["current_street_discard_draw_performed"]
  del observation_dict["bets"]
  observation_dict["your_seat_id(0-indexed)"] = state._player_to_seat[
      observation_dict.pop("player")
  ]
  observation_dict["current_street"] = _STREET_NAMES[
      observation_dict["current_street"]
  ]
  observation_dict["next_player_to_act"] = (
      f"seat{state._player_to_seat[observation_dict['next_player_to_act']]}"
  )
  game_params = state.get_game().get_parameters()
  observation_dict["blinds"] = game_params["pokerkit_game_params"]["blinds"]

  replay_state = state.get_game().new_initial_state()
  betting_history = {street: [] for street in _STREET_NAMES.values()}
  first_non_chance_node_found = False
  for action in state.history():
    if replay_state._hand_number != state._hand_number:
      replay_state.apply_action(action)
      continue
    if not replay_state.is_chance_node():
      if not first_non_chance_node_found:
        first_non_chance_node_found = True
        dealer_seat = replay_state._player_to_seat[
            replay_state.current_player()
        ]
        observation_dict["dealer(0-indexed)"] = f"seat{dealer_seat}"
        betting_history[_STREET_NAMES[0]].extend([
            (
                f"seat{dealer_seat}:post small blind"
                f" {min(observation_dict['blinds'])}"
            ),
            (
                f"seat{(dealer_seat+1)%state.num_players()}:post big blind"
                f" {max(observation_dict['blinds'])}"
            ),
        ])
      action_str = replay_state.action_to_string(action)
                                                                               
                                                                         
                           
      action_str = action_str.split(":")[-1]
      bet_string = f"seat{replay_state._player_to_seat[replay_state.current_player()]}:{action_str}"
      replay_obs_dict = json.loads(
          _convert_pokerkit_obs_to_json(replay_state.observation_string())
      )
      street_name = _STREET_NAMES[replay_obs_dict["current_street"]]
      betting_history[street_name].append(bet_string)
    replay_state.apply_action(action)
  if not first_non_chance_node_found:
    observation_dict["dealer(0-indexed)"] = (
        f"seat{replay_state._player_to_seat[replay_state.current_player()]}"
    )
  observation_dict["betting_history"] = betting_history
  observation_dict["hand_number"] = state._hand_number
  return json.dumps(observation_dict, indent=2)


                                 


class PokerkitGameAdapter(PokerGameAdapter):
  pass                        

  game_short_name = "pokerkit"

  def get_readable_state(self, representation_type: str | int | None = None):
    return _get_readable_pokerkit_observation(self.native_state)

  def convert_pokerkit_obs_to_json(self, observation_string: str) -> str:
    return _convert_pokerkit_obs_to_json(observation_string)
