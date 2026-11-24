import re
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta
from textarena.envs.Nim.renderer import create_board_str

class NimEnv(ta.Env):
    def __init__(self, piles: List[int] = None):
        pass             
                                                                                                         
           
        super().__init__()
        self.initial_piles = piles if piles is not None else [3, 4, 5]

    def get_board_str(self):
        return create_board_str(self.state.game_state["piles"])

    def reset(self, num_players: int, seed: Optional[int] = None):
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.state.reset(game_state={"piles": self.initial_piles.copy()}, player_prompt_function=self._prompt)
        self.state.add_observation(message=self.m("state", "current_pile", piles=self._render_piles()), observation_type=ta.ObservationType.GAME_BOARD)

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        return self.m("player_prompt", "intro", player_id=player_id)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        self._execute_move(action)                                                                        
        self.state.add_observation(message=self.m("state", "current_pile", piles=self._render_piles()), observation_type=ta.ObservationType.GAME_BOARD)                                                                          
        self._check_game_over()                            
        return self.state.step()                                                 

    def _execute_move(self, action: str) -> None:
        match = re.compile(r"\[\s*(\d+)\s+(\d+)\s*\]").search(action.strip())                                                                                    
        if not match: self.state.set_invalid_move(reason=self.m("invalid_move", "wrong_format")); return
        try: pile_index, quantity = map(int, match.groups())                                            
        except ValueError: self.state.set_invalid_move(reason=self.m("invalid_move", "correct_format_wrong_fields")); return
                           
        if not (0 <= pile_index < len(self.state.game_state["piles"])): self.state.set_invalid_move(reason=self.m("invalid_move", "out_of_range", pile_index=pile_index)); return
        if quantity <= 0: self.state.set_invalid_move(reason=self.m("invalid_move", "non_positive")); return
        if self.state.game_state["piles"][pile_index] < quantity: self.state.set_invalid_move(reason=self.m("invalid_move", "exceeds_pile", quantity=quantity, pile_index=pile_index, pile_count=self.state.game_state['piles'][pile_index])); return
        self.state.game_state["piles"][pile_index] -= quantity                      
        self.state.add_observation(message=self.m("observation", "removed_from_piles", player_id=self.state.current_player_id, quantity=quantity, pile_index=pile_index), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)                    

    def _check_game_over(self) -> None:
        if all(pile == 0 for pile in self.state.game_state["piles"]):
            self.state.set_winner(player_id=self.state.current_player_id, reason=self.m("outcome", "win", player_id=self.state.current_player_id))

    def _render_piles(self) -> str:
                                                                                  
                                                                                    
        return "\n".join(f"  pile {i}: {amt}" for i, amt in enumerate(self.state.game_state["piles"]))