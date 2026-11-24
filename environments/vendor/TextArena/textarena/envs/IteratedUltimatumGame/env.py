import re
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta
from textarena.envs.IteratedUltimatumGame.renderer import create_board_str


class IteratedUltimatumGameEnv(ta.Env):
    pass                                           
    
                            
                                                               
                                                                              
                                              
                                                                     
                                                          
                                                     
       

    def __init__(self, pool: int = 10, max_turns: Optional[int] = 4, alternate_roles: bool = False):
        pass                                                           
        
             
                                                            
                                                                                           
           
        self.pool = pool
        self.max_turns = max_turns
        self.alternate_roles = alternate_roles
        
                                                   
        self.offer_pattern = re.compile(
            r"\[Offer:\s*\$?(\d+)\]", re.IGNORECASE
        )
        self.accept_pattern = re.compile(r"\[Accept\]", re.IGNORECASE)
        self.reject_pattern = re.compile(r"\[Reject\]", re.IGNORECASE)

    def get_board_str(self):
        pass                                          
                                                                             
        if self.state.game_state["phase"] == "offering":
            current_proposer = self.state.current_player_id
        else:
                                                               
            current_proposer = 1 - self.state.current_player_id
            
        return create_board_str(
            pool=self.state.game_state["pool"],
            current_offer=self.state.game_state.get("current_offer"),
            game_phase=self.state.game_state["phase"],
            round_number=self.state.game_state["round_number"],
            total_rounds=self.max_turns // 2,
            player_totals=self.state.game_state["player_totals"],
            round_history=self.state.game_state["round_history"],
            current_proposer=current_proposer,
        )

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        pass                                                     
   
        return self.m(
            "player_prompt", "intro",
            player_id=player_id,
            num_rounds=self.max_turns // 2,
            pool=game_state['pool'],
            other_id=1 - player_id,
        )

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                                         
                               
        self.state = ta.TwoPlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)

        game_state = {
            "pool": self.pool,
            "phase": "offering",                               
            "round_number": 1,
            "current_offer": None,
            "player_totals": {0: 0, 1: 0},                                   
            "round_history": [],                                  
            "current_proposer_id": self.state.current_player_id,
            "current_responder_id": 1 - self.state.current_player_id
        }

        self.state.reset(
            game_state=game_state,
            player_prompt_function=self._generate_player_prompt,
        )

        self.state.add_observation(
            message=self.m(
                "round", "begins",
                round_number=self.state.game_state['round_number'],
                proposer_id=self.state.game_state['current_proposer_id'],
                responder_id=self.state.game_state['current_responder_id'],
            ),
            observation_type=ta.ObservationType.GAME_MESSAGE
        )

                                                        

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                              
                                                    
        self.state.add_observation(
            from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION
        )

        rotate_player = True                      
        game_phase = self.state.game_state["phase"]

        if game_phase == "offering":
                                               
            self._handle_proposer_action(action)
        elif game_phase == "responding":
                                                       
            self._handle_responder_action(action)
            rotate_player = False if self.alternate_roles else True

        return self.state.step(rotate_player=rotate_player)

    def _handle_proposer_action(self, action: str) -> None:
        pass                                     
        offer_match = self.offer_pattern.search(action)
        
        if not offer_match:
            self.state.set_invalid_move(reason=self.m("invalid_move", "no_offer_format"))
            return

        try:
            offer = int(offer_match.group(1))
        except ValueError:
            self.state.set_invalid_move(reason=self.m("invalid_move", "bad_integer"))
            return

                               
        if offer < 0 or offer > self.state.game_state["pool"]:
            self.state.set_invalid_move(reason=self.m("invalid_move", "out_of_range", pool=self.state.game_state['pool']))
            return

                                         
        self.state.game_state["current_offer"] = offer
        self.state.game_state["phase"] = "responding"
        
                             
        proposer_id = self.state.current_player_id
        responder_id = 1 - proposer_id
        self.state.add_observation(
            message=self.m(
                "round", "offer",
                round_number=self.state.game_state['round_number'],
                proposer_id=proposer_id,
                offer=offer,
                responder_id=responder_id,
                keep=self.state.game_state['pool'] - offer,
            ),
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
        
                                                                            

    def _handle_responder_action(self, action: str) -> None:
        pass                                              
        current_offer = self.state.game_state["current_offer"]
        
        if current_offer is None:
            self.state.set_invalid_move(reason=self.m("invalid_move", "no_current_offer"))
            return

        if self.accept_pattern.search(action):
                            
            self._execute_accepted_offer()
        elif self.reject_pattern.search(action):
                            
            self._execute_rejected_offer()
        else:
            self.state.set_invalid_move(reason=self.m("invalid_move", "accept_or_reject"))

    def _execute_accepted_offer(self) -> None:
        pass                                           
        offer = self.state.game_state["current_offer"]
        pool = self.state.game_state["pool"]
                                                                           
        responder_id = self.state.current_player_id
        proposer_id = 1 - responder_id
        
                                        
        proposer_gain = pool - offer
        responder_gain = offer
        
                            
        self.state.game_state["player_totals"][proposer_id] += proposer_gain
        self.state.game_state["player_totals"][responder_id] += responder_gain
        
                        
        self.state.game_state["round_history"].append({
            "round": self.state.game_state["round_number"],
            "proposer": proposer_id,
            "responder": responder_id,
            "offer": offer,
            "decision": "Accept",
            "proposer_gain": proposer_gain,
            "responder_gain": responder_gain,
        })
        
                          
        self.state.add_observation(
            message=self.m(
                "round", "accepted",
                responder_id=responder_id,
                round_number=self.state.game_state['round_number'],
                proposer_id=proposer_id,
                proposer_gain=proposer_gain,
                responder_gain=responder_gain,
                total_0=self.state.game_state['player_totals'][0],
                total_1=self.state.game_state['player_totals'][1],
            ),
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
        
        self._advance_to_next_round()

    def _execute_rejected_offer(self) -> None:
        pass                                           
                                                                           
        responder_id = self.state.current_player_id
        proposer_id = 1 - responder_id
        offer = self.state.game_state["current_offer"]
        
                                   
        self.state.game_state["round_history"].append({
            "round": self.state.game_state["round_number"],
            "proposer": proposer_id,
            "responder": responder_id,
            "offer": offer,
            "decision": "Reject",
            "proposer_gain": 0,
            "responder_gain": 0,
        })
        
                          
        self.state.add_observation(
            message=self.m(
                "round", "rejected",
                responder_id=responder_id,
                round_number=self.state.game_state['round_number'],
                total_0=self.state.game_state['player_totals'][0],
                total_1=self.state.game_state['player_totals'][1],
            ),
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
        
        self._advance_to_next_round()

    def _advance_to_next_round(self) -> None:
        pass                                            
        if self.state.game_state["round_number"] >= (self.max_turns // 2):
            self._determine_final_winner()
        else:
            self.state.game_state["round_number"] += 1
            self.state.game_state["phase"] = "offering"
            self.state.game_state["current_offer"] = None

            if self.alternate_roles:
                                          
                proposer_id = 1 - self.state.game_state["current_proposer_id"]
            else:
                                                           
                proposer_id = self.state.game_state.get("current_proposer_id", 0)

            responder_id = 1 - proposer_id

            self.state.game_state["current_proposer_id"] = proposer_id
            self.state.game_state["current_responder_id"] = responder_id

            self.state.add_observation(
                message=self.m(
                    "round", "begins",
                    round_number=self.state.game_state['round_number'],
                    proposer_id=proposer_id,
                    responder_id=responder_id,
                ),
                observation_type=ta.ObservationType.GAME_MESSAGE
            )

    def _determine_final_winner(self) -> None:
        pass                                                        
        total_0 = self.state.game_state["player_totals"][0]
        total_1 = self.state.game_state["player_totals"][1]
        
        if total_0 > total_1:
            self.state.set_winner(
                player_id=0,
                reason=self.m("outcome", "win", winner=0, winner_total=total_0, loser=1, loser_total=total_1)
            )
        elif total_1 > total_0:
            self.state.set_winner(
                player_id=1,
                reason=self.m("outcome", "win", winner=1, winner_total=total_1, loser=0, loser_total=total_0)
            )
        else:
            self.state.set_draw(
                reason=self.m("outcome", "draw", total=total_0)
            ) 