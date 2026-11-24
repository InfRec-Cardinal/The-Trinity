                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                              

                                                                         
                                               
   

import abc
from collections.abc import Sequence
import dataclasses
from typing import Any, Mapping
import pyspiel


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseGameNotation:
  pass                     

  state: str
  action: str
  player_map: dict[int, str]
  move_notation: str
  state_notation: str


class BaseGameEnvAdapter(abc.ABC):
  pass                                   

                                                                               
        

                                                                                
                                                                    

                                                                             
                                                                               
           
     

  def __init__(self):
                                                                                
    self.player_number: int | None = None
    self.legal_actions: str | Sequence[str] | None = None
                                                                              
    self.native_legal_actions: int | Sequence[int] | None = None
    self.native_state: Any = None
    self._observation = None
    self._configuration = None

  @property
  @abc.abstractmethod
  def game_short_name(self) -> str:
    pass                              
    ...

  @property
  @abc.abstractmethod
  def game_notation(self) -> BaseGameNotation:
    pass                                         
    ...

  @abc.abstractmethod
  def update_game_state(self, observation: Mapping[str, Any]) -> None:
    pass                                                                   
    ...

  @abc.abstractmethod
  def string_to_action(self, action_str: str) -> Any:
    pass                                                                  
    ...

  @abc.abstractmethod
  def action_to_string(self, action: Any) -> str:
    pass                                             
    ...

  @abc.abstractmethod
  def get_readable_state(
      self, representation_type: str | int | None = None, **kwargs
  ) -> str:
    pass                                                                          

         
                                                                            
                                     
                                                                            
                                               

            
                                                
       
    ...


class OpenSpielGameAdapter(BaseGameEnvAdapter, abc.ABC):
  pass                            

  def update_game_state(self, observation: Mapping[str, Any]) -> None:
    self._observation = observation
    serialized_game_and_state = self._observation.get("serializedGameAndState")
    _, pyspiel_state = pyspiel.deserialize_game_and_state(
        serialized_game_and_state
    )
    self.native_state = pyspiel_state
    if not self.native_state:
      self.legal_actions = []
    else:
      self.native_legal_actions = self.native_state.legal_actions()
      self.legal_actions = [
          self.native_state.action_to_string(
              self.native_state.current_player(), action_int
          )
          for action_int in self.native_legal_actions
      ]
    self.player_number = self.native_state.current_player()
    assert self.game_notation is not None

    self.player_name: str = self.game_notation.player_map[self.player_number]

  def action_to_string(self, action: int) -> str:
    pass                                    
    assert self.native_state is not None
    return self.native_state.action_to_string(action)

  def string_to_action(self, action_str: str) -> int:
    pass                                                                  
    assert self.native_state is not None
    return self.native_state.string_to_action(action_str)

  def get_action_string_history(self) -> str:
    pass                                      

    tmp_state = self.native_state.get_game().new_initial_state()
    move_list = []
    for action in self.native_state.history():
      action_str = tmp_state.action_to_string(
          tmp_state.current_player(), action
      )
      move_list.append(action_str)
      tmp_state.apply_action(action)

    move_history = " ".join(move_list) if move_list else "None"
    return move_history

  def get_readable_state(
      self, representation_type: str | int | None = None
  ) -> str:
    pass                                                                             
    assert self.native_state is not None
    return "\n".join([
        " ".join(list(line.strip()))
        for line in str(self.native_state).split("\n")
    ])
