                         
                                                      

                        
                                                                   

                                
                                                               
             
               
                                                  
                                                      
             
                            
                                    
                                    

                              
                                                                         

                                                                    
                                                                                                                                       
                                                                                            
                                                                                                      
                                                                                                                                         
    
                                                                                           
                  
                                                                                                                                   
                                                                                                                                                                                                              
                                              
           

                              
                                  
                             
                                                                      
                                                     
                               
    
                                                          
                                                                                                                                 
                                                                                                 

                         
                                                                                                                                                 
               
                                   
                                        
                                                                  
                                                                                                                     
                                                                                                                                                             
                                                                   
                                                                                                                                                          
                                        
                                                                                                                                                        
                                                                                                                                                             
                                                                                                                                                         
                       
                                                                                                                   
                                                                                                                                                                                                                 
                                                                                                                                                     

                                                                                                                         
                                                                                                                      
                   
                                                 
                                                                  
                                                                                                                                                                                    
            
                                  
    
                                                    
                                                                                                    
                     
                                                                     
                                                                                  
                                    
                              
                   
                                                     
                                       

import re, random, copy
from typing import Any, Dict, Optional, Tuple, Union

import textarena as ta
from textarena.envs.TowerOfHanoi.renderer import create_board_str

class TowerOfHanoiEnv(ta.Env):
    def __init__(self, num_disks: int=3, max_turns: int=100):
        pass             
                                                
                                                    
           
        super().__init__()
        self.num_disks = num_disks
        self.max_turns = max_turns

    def get_board_str(self):
        return create_board_str(towers=self.state.game_state['towers'])

    def reset(self, num_players: int, seed: Optional[int] = None):
        self.state = ta.SinglePlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)                              
        game_state={"towers": {"A": list(range(self.num_disks, 0, -1)), "B": [], "C": []}}
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self.state.add_observation(message=self.m("board", "current_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        return self.m("player_prompt", "intro", num_disks=self.num_disks)

    def _render_board(self):
        pass                    
        rendered_board = ""
        for tower, disks in self.state.game_state["towers"].items():
            rendered_board += f"{tower}: {disks}\n"
        return rendered_board
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.state.add_observation(message=action, observation_type=ta.ObservationType.PLAYER_ACTION)                          
        matches = re.compile(r"\[\s*([ABC])\s*,?\s*([ABC])\s*\]",re.IGNORECASE).findall(action)

        if not matches:
            self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "wrong_format"))
        else:
            for match in matches:
                source, target = match
                source = source.upper(); target = target.upper()
                if source not in self.state.game_state['towers'] or target not in self.state.game_state['towers']: 
                    self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "invalid_tower")); break
                elif not self.state.game_state['towers'][source]:
                    self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "empty_tower")); break
                elif source == target:
                    self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "same_tower")); break
                elif self.state.game_state['towers'][target] and self.state.game_state['towers'][target][-1] < self.state.game_state['towers'][source][-1]:
                    self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=self.m("invalid_move", "larger_on_smaller"))
                else:
                    self.state.game_state['towers'][target].append(self.state.game_state["towers"][source].pop())
                    self.state.add_observation(message=self.m("game_action", "moved", disk=self.state.game_state['towers'][target][-1], source=source, target=target), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.add_observation(message=self.m("board", "current_board", board=self._render_board()), observation_type=ta.ObservationType.GAME_BOARD)

            if self.state.game_state['towers']["C"] == list(range(self.num_disks, 0, -1)):                             
                self.state.set_outcome(reward=1, reason=self.m("outcome", "win"))   
                   
            elif self.state.check_turn_limit():
                pct_complete = self._get_percentage_completion()
                self.state.set_outcome(reward=pct_complete, reason=self.m("outcome", "turn_limit", pct=round(pct_complete * 100)))
            
        return self.state.step()
    
    def _get_percentage_completion(self) -> float:
        pass                                                                                      
        correct = 0
        goal = list(range(self.num_disks, 0, -1))                  
        for placed, expected in zip(self.state.game_state['towers']["C"], goal):
            if placed == expected:
                correct += 1
            else:
                break                              
        return correct/self.num_disks