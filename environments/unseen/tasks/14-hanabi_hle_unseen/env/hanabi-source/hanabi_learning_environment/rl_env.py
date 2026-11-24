                           
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                                    

from __future__ import absolute_import
from __future__ import division

from hanabi_learning_environment import pyhanabi
from hanabi_learning_environment.pyhanabi import color_char_to_idx

MOVE_TYPES = [_.name for _ in pyhanabi.HanabiMoveType]

                                                                                
                 
                                                                                


class Environment(object):
  pass                              

                                                                        
                                           
     

  def reset(self, config):
    pass                                       

                                                                           
                  

         
                                                                      
                  

            
                                                                
       
    raise NotImplementedError("Not implemented in Abstract Base class")

  def step(self, action):
    pass                         

         
                                                           

            
                                                           
                                                            
                                           
                                                 

           
                                                         
       
    raise NotImplementedError("Not implemented in Abstract Base class")


class HanabiEnv(Environment):
  pass                                    

           

                             
                           
                                         
                 
                          
                   
                               
                                                                
     
     

  def __init__(self, config):
    pass                                                         

         
                                                                            
                        
                                                    
                                                  
                                                      
                                                
                                                                            
                                                              
                                  
                                   
                                                        
                                   
                                                           
       
    assert isinstance(config, dict), "Expected config to be of type dict."
    self.game = pyhanabi.HanabiGame(config)

    self.observation_encoder = pyhanabi.ObservationEncoder(
        self.game, pyhanabi.ObservationEncoderType.CANONICAL)
    self.players = self.game.num_players()

  def reset(self):
    pass                                      

            
                                                                              
                                                                              
                                                       
                               
                             
                                                      
                                                             
                                                  
                                                     
                                                       
                                                       
                                                       
                                                       
                                                        
                                                          
                                                                         
                                                                    
                                                                         
                                                                    
                                                                         
                                                                    
                                                                         
                                                                    
                                                                         
                                                                    
                                                                 
                                                                 
                                                                
                                                                       
                                                                 
                                                                 
                                                                
                                                                       
                                                                 
                                                                 
                                                                
                                                                       
                                                                                
                                                             
                                                                       
                                                                                
                                                             
                                                                       
                                                                                
                                                             
                                                                        
                                                   
                                                                             
                                      
                                                                             
                                                          
                                                                             
                                                          
                                                                             
                                                          
                                                                             
                                                           
                                                                                
                                                                                
                                                                                
                                                                                
                                                                            
                                                           
                                                   
                                                                  
                                                      
                                                             
                                                  
                                                     
                                                       
                                                       
                                                       
                                                       
                                                        
                                                          
                                                    
                                                   
                                                                             
                                      
                                                                             
                                                          
                                                                             
                                                          
                                                                             
                                                          
                                                                             
                                                           
                                                                                
                                                                                
                                                                                
                                                                                
                                                                            
                                                           
                                                   
                                                                   
       
    self.state = self.game.new_initial_state()

    while self.state.cur_player() == pyhanabi.CHANCE_PLAYER_ID:
      self.state.deal_random_card()

    obs = self._make_observation_all_players()
    obs["current_player"] = self.state.cur_player()
    return obs

  def vectorized_observation_shape(self):
    pass                                               

            
                                                                    
       
    return self.observation_encoder.shape()

  def num_moves(self):
    pass                                                             

            
                               
       
    return self.game.max_moves()

  def step(self, action):
    pass                         

         
                                                                              
                              
                                                        
                                                           
             
                                            
                           
                                      
             
             
                                           
                          
                                      
             
                                                                      

            
                                                                              
                                                                              
                                                       
                               
                             
                                                      
                                                       
                                            
                                               
                                                 
                                             
                                             
                                             
                                              
                                                    
                                                                   
                                                          
                                                               
                                                          
                                                               
                                                          
                                                               
                                                          
                                                               
                                                          
                                                                       
                                                      
                                                             
                                                                       
                                                      
                                                             
                                                                       
                                                      
                                                             
                                                                      
                                                   
                                                             
                                                                      
                                                   
                                                             
                                                                      
                                                   
                                                              
                                             
                                                                            
                                                                        
                                                                        
                                                                        
                                                                         
                                                                      
                                                                      
                                                                      
                                                                      
                                                                        
                                             
                                                            
                                                
                                                       
                                            
                                               
                                                 
                                             
                                             
                                             
                                              
                                                    
                                              
                                             
                                                                            
                                                                        
                                                                        
                                                                        
                                                                         
                                                                      
                                                                      
                                                                      
                                                                      
                                                                        
                                             
                                                             
                                                            
                                           
                                                 

           
                                                         
       
    if isinstance(action, dict):
                                      
      action = self._build_move(action)
    elif isinstance(action, int):
                                              
      action = self.game.get_move(action)
    else:
      raise ValueError("Expected action as dict or int, got: {}".format(
          action))

    last_score = self.state.score()
                                    
    self.state.apply_move(action)

    while self.state.cur_player() == pyhanabi.CHANCE_PLAYER_ID:
      self.state.deal_random_card()

    observation = self._make_observation_all_players()
    done = self.state.is_terminal()
                                                                          
    reward = self.state.score() - last_score
    info = {}

    return (observation, reward, done, info)

  def _make_observation_all_players(self):
    pass                                

            
                                                    
       
    obs = {}
    player_observations = [self._extract_dict_from_backend(
        player_id, self.state.observation(player_id))
        for player_id in range(self.players)]                                    
    obs["player_observations"] = player_observations
    obs["current_player"] = self.state.cur_player()
    return obs

  def _extract_dict_from_backend(self, player_id, observation):
    pass                                                               

         
                                                                                
                                                         

            
                                                               
       
    obs_dict = {}
    obs_dict["current_player"] = self.state.cur_player()
    obs_dict["current_player_offset"] = observation.cur_player_offset()
    obs_dict["life_tokens"] = observation.life_tokens()
    obs_dict["information_tokens"] = observation.information_tokens()
    obs_dict["num_players"] = observation.num_players()
    obs_dict["deck_size"] = observation.deck_size()

    obs_dict["fireworks"] = {}
    fireworks = self.state.fireworks()
    for color, firework in zip(pyhanabi.COLOR_CHAR, fireworks):
      obs_dict["fireworks"][color] = firework

    obs_dict["legal_moves"] = []
    obs_dict["legal_moves_as_int"] = []
    for move in observation.legal_moves():
      obs_dict["legal_moves"].append(move.to_dict())
      obs_dict["legal_moves_as_int"].append(self.game.get_move_uid(move))

    obs_dict["observed_hands"] = []
    for player_hand in observation.observed_hands():
      cards = [card.to_dict() for card in player_hand]
      obs_dict["observed_hands"].append(cards)

    obs_dict["discard_pile"] = [
        card.to_dict() for card in observation.discard_pile()
    ]

                            
    obs_dict["card_knowledge"] = []
    for player_hints in observation.card_knowledge():
      player_hints_as_dicts = []
      for hint in player_hints:
        hint_d = {}
        if hint.color() is not None:
          hint_d["color"] = pyhanabi.color_idx_to_char(hint.color())
        else:
          hint_d["color"] = None
        hint_d["rank"] = hint.rank()
        player_hints_as_dicts.append(hint_d)
      obs_dict["card_knowledge"].append(player_hints_as_dicts)

                      
    obs_dict["vectorized"] = self.observation_encoder.encode(observation)
    obs_dict["pyhanabi"] = observation

    return obs_dict

  def _build_move(self, action):
    pass                                

         
                                                                              
                              
                                                        
                                                           
             
                                            
                           
                                      
             
             
                                           
                          
                                      
             

            
                                                          

           
                                      
       
    assert isinstance(action, dict), "Expected dict, got: {}".format(action)
    assert "action_type" in action, ("Action should contain `action_type`. "
                                     "action: {}").format(action)
    action_type = action["action_type"]
    assert (action_type in MOVE_TYPES), (
        "action_type: {} should be one of: {}".format(action_type, MOVE_TYPES))

    if action_type == "PLAY":
      card_index = action["card_index"]
      move = pyhanabi.HanabiMove.get_play_move(card_index=card_index)
    elif action_type == "DISCARD":
      card_index = action["card_index"]
      move = pyhanabi.HanabiMove.get_discard_move(card_index=card_index)
    elif action_type == "REVEAL_RANK":
      target_offset = action["target_offset"]
      rank = action["rank"]
      move = pyhanabi.HanabiMove.get_reveal_rank_move(
          target_offset=target_offset, rank=rank)
    elif action_type == "REVEAL_COLOR":
      target_offset = action["target_offset"]
      assert isinstance(action["color"], str)
      color = color_char_to_idx(action["color"])
      move = pyhanabi.HanabiMove.get_reveal_color_move(
          target_offset=target_offset, color=color)
    else:
      raise ValueError("Unknown action_type: {}".format(action_type))

    legal_moves = self.state.legal_moves()
    assert (str(move) in map(
        str,
        legal_moves)), "Illegal action: {}. Move should be one of : {}".format(
            move, legal_moves)

    return move


def make(environment_name="Hanabi-Full", num_players=2, pyhanabi_path=None):
  pass                   

       
                                                                  
                                                     
                                                                         

          
                                 

         
                                         
     

  if pyhanabi_path is not None:
    prefixes=(pyhanabi_path,)
    assert pyhanabi.try_cdef(prefixes=prefixes), "cdef failed to load"
    assert pyhanabi.try_load(prefixes=prefixes), "library failed to load"

  if (environment_name == "Hanabi-Full" or
      environment_name == "Hanabi-Full-CardKnowledge"):
    return HanabiEnv(
        config={
            "colors":
                5,
            "ranks":
                5,
            "players":
                num_players,
            "max_information_tokens":
                8,
            "max_life_tokens":
                3,
            "observation_type":
                pyhanabi.AgentObservationType.CARD_KNOWLEDGE.value
        })
  elif environment_name == "Hanabi-Full-Minimal":
    return HanabiEnv(
        config={
            "colors": 5,
            "ranks": 5,
            "players": num_players,
            "max_information_tokens": 8,
            "max_life_tokens": 3,
            "observation_type": pyhanabi.AgentObservationType.MINIMAL.value
        })
  elif environment_name == "Hanabi-Small":
    return HanabiEnv(
        config={
            "colors":
                2,
            "ranks":
                5,
            "players":
                num_players,
            "hand_size":
                2,
            "max_information_tokens":
                3,
            "max_life_tokens":
                1,
            "observation_type":
                pyhanabi.AgentObservationType.CARD_KNOWLEDGE.value
        })
  elif environment_name == "Hanabi-Very-Small":
    return HanabiEnv(
        config={
            "colors":
                1,
            "ranks":
                5,
            "players":
                num_players,
            "hand_size":
                2,
            "max_information_tokens":
                3,
            "max_life_tokens":
                1,
            "observation_type":
                pyhanabi.AgentObservationType.CARD_KNOWLEDGE.value
        })
  else:
    raise ValueError("Unknown environment {}".format(environment_name))


                                                                                
                  
                                                                                


class Agent(object):
  pass               

                                                                            
                                 


           

                       
       

                                                    
                 
       
                                             
                                     
                                        
                                 
          
                             
       
     
     

  def __init__(self, config, *args, **kwargs):
    pass                     

         
                                                                            
                        
                                                    
                                                  
                                                      
                                                
                                                                           
                                                             
                                   
                                                           
                               
                                           

           
                                    
       
    raise NotImplementedError("Not implemeneted in abstract base class.")

  def reset(self, config):
    pass                                  

                                                           

         
                                                                            
                        
                                                    
                                                  
                                                      
                                                
                                                                           
                                                             
                                   
                                                           
       
    raise NotImplementedError("Not implemeneted in abstract base class.")

  def act(self, observation):
    pass                           

         
                                                                            
                   
                             
                                    
                         
                            
                              
                          
                          
                          
                           
                                 
                           
                          
                                                         
                                                     
                                                     
                                                     
                                                      
                                                   
                                                   
                                                   
                                                   
                                                     
                            

            
                                                                                
                              
                                                        
                                                           
             
                                            
                           
                                      
             
             
                                           
                          
                                      
             
       
    raise NotImplementedError("Not implemented in Abstract Base class")
