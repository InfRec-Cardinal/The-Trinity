                           
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                   

from hanabi_learning_environment.rl_env import Agent


class SimpleAgent(Agent):
  pass                                        

  def __init__(self, config, *args, **kwargs):
    pass                       
    self.config = config
                                                  
    self.max_information_tokens = config.get('information_tokens', 8)

  @staticmethod
  def playable_card(card, fireworks):
    pass                                                               
    return card['rank'] == fireworks[card['color']]

  def act(self, observation):
    pass                              
    if observation['current_player_offset'] != 0:
      return None

                                                                             
               
    for card_index, hint in enumerate(observation['card_knowledge'][0]):
      if hint['color'] is not None or hint['rank'] is not None:
        return {'action_type': 'PLAY', 'card_index': card_index}

                                                               
    fireworks = observation['fireworks']
    if observation['information_tokens'] > 0:
                                                                            
      for player_offset in range(1, observation['num_players']):
        player_hand = observation['observed_hands'][player_offset]
        player_hints = observation['card_knowledge'][player_offset]
                                                                    
        for card, hint in zip(player_hand, player_hints):
          if SimpleAgent.playable_card(card,
                                       fireworks) and hint['color'] is None:
            return {
                'action_type': 'REVEAL_COLOR',
                'color': card['color'],
                'target_offset': player_offset
            }

                                                  
    if observation['information_tokens'] < self.max_information_tokens:
      return {'action_type': 'DISCARD', 'card_index': 0}
    else:
      return {'action_type': 'PLAY', 'card_index': 0}
