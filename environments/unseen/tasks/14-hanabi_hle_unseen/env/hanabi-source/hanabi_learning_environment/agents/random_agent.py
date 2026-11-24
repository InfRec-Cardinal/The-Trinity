                           
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                   

import random
from hanabi_learning_environment.rl_env import Agent


class RandomAgent(Agent):
  pass                                        

  def __init__(self, config, *args, **kwargs):
    pass                       
    self.config = config

  def act(self, observation):
    pass                              
    if observation['current_player_offset'] == 0:
      return random.choice(observation['legal_moves'])
    else:
      return None
