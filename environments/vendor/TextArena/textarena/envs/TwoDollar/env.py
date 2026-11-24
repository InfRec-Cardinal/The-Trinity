   
                                       

                                                                                  
                                                                             
                                                

                                                                                 
   

import os
import json
import random
import re
from typing import Any, Dict, List, Optional, Tuple

import textarena as ta
from textarena.state import TwoPlayerState
from textarena.envs.TwoDollar.renderer import render_game_state, render_negotiation_summary, render_final_results

class TwoDollarEnv(ta.Env):
    pass                                                                                   
                                                                                           
       
    
    def __init__(self, 
                 player_roles: Optional[List[str]] = None,
                 total_amount: float = 2.00,
                 max_rounds: int = 20,
                 error_allowance: int = 3):
        pass                                              
        
             
                                                                             
                                                                  
                                                            
                                                                                           
           
        self.player_roles_config = player_roles
        self.total_amount = total_amount
        self.max_rounds = max_rounds
        self.error_allowance = error_allowance
        
                                  
        self.available_roles = self._load_available_roles()
        
                    
        self.player_roles = {}                                   
        self.player_proposal_history = {0: [], 1: []}                            
        self.negotiation_history = []                           
        self.current_proposal = {"amount": None, "proposer": None}
        self.final_amounts = {0: 0.0, 1: 0.0}
        self.player_deadline = {}                     
        
    def _load_available_roles(self) -> Dict[str, Dict]:
        pass                                                                        
        roles_dir = os.path.join(os.path.dirname(__file__), "roles")
        available_roles = {}
        
                                
        for folder in ["enforceable", "non_enforceable"]:
            folder_path = os.path.join(roles_dir, folder)
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    if filename.endswith('.json'):
                        role_name = filename[:-5]                
                        with open(os.path.join(folder_path, filename), 'r') as f:
                            available_roles[role_name] = json.load(f)
        
        return available_roles
    
    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                         
        if num_players != 2:
            raise ValueError("TwoDollar game requires exactly 2 players")
        
                                     
        if seed is not None:
            random.seed(seed)
        
                      
        if self.player_roles_config is None:
                               
            self.player_roles = self._assign_random_roles()
        else:
                                 
            if len(self.player_roles_config) != 2:
                raise ValueError("player_roles must contain exactly 2 role names")
            self.player_roles = self._assign_specific_roles(self.player_roles_config)
        
                                    
        self.state = TwoPlayerState(
            num_players=num_players,
            max_turns=self.max_rounds,
            seed=seed,
            error_allowance=self.error_allowance
        )
        
                               
        game_state = {
            "current_proposal": {"amount": None, "proposer": None},
            "negotiation_history": [],
            "player_proposal_history": {0: [], 1: []},
            "final_amounts": {0: 0.0, 1: 0.0}
        }
        
                          
        self.player_proposal_history = {0: [], 1: []}
        self.negotiation_history = []
        self.current_proposal = {"amount": None, "proposer": None}
        self.final_amounts = {0: 0.0, 1: 0.0}
        
                                         
        self.player_deadline = {}
        for player_id, role in self.player_roles.items():
            if role.get("name") == "x_rounds":
                self.player_deadline[player_id] = self.max_rounds // 2
        
                                       
        self.state.reset(
            game_state=game_state,
            player_prompt_function=self._generate_player_prompt
        )
    
    def _assign_random_roles(self) -> Dict[int, Dict]:
        pass                                   
                                         
        selected_roles = random.sample(list(self.available_roles.keys()), 2)
        
        return {
            0: self.available_roles[selected_roles[0]],
            1: self.available_roles[selected_roles[1]]
        }
    
    def _assign_specific_roles(self, role_names: List[str]) -> Dict[int, Dict]:
        pass                               
        player_roles = {}
        
        for i, role_name in enumerate(role_names):
            if role_name not in self.available_roles:
                raise ValueError(f"Unknown role: {role_name}. Available roles: {list(self.available_roles.keys())}")
            player_roles[i] = self.available_roles[role_name]
        
        return player_roles
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        pass                                       
        role = self.player_roles[player_id]
        
                          
        prompt = f"""TWO DOLLAR NEGOTIATION GAME

You are Player {player_id} negotiating with another player over how to split ${self.total_amount:.2f} total.
There are {self.max_rounds} maximum rounds.

GAME RULES:
- You must reach an agreement on how to split the ${self.total_amount:.2f}
- If no agreement is reached, both players get $0.00
- You have secret instructions that only you can see (below)

REQUIRED ACTION FORMAT:
Always provide your reasoning/persuasion BEFORE the bracketed action.
Any text after the bracketed action will be ignored.

Available actions:
- Make a proposal: "I think this is fair because... [Propose] $X.XX"
- Accept current proposal: "This works for me because... [Accept]"  
- Reject current proposal: "I can't accept this because... [Reject]"

"""
        
                                        
        prompt += f"\n=== YOUR SECRET INSTRUCTIONS ===\n"
        prompt += f"{role['instructions']}\n"
        
                                        
        prompt += f"\nVICTORY CONDITION: {role['victory_condition']}\n"
        prompt += f"FAILURE CONDITION: {role['failure_condition']}\n"
        
                                             
        if role.get("name") == "x_rounds":
            deadline = self.player_deadline.get(player_id, self.max_rounds // 2)
            prompt = prompt.replace("{deadline}", str(deadline))
            prompt = prompt.replace("{total_rounds}", str(self.max_rounds))
        
        return prompt
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                            
        current_pid = self.state.current_player_id
        
                        
        self.state.add_observation(
            from_id=current_pid,
            to_id=current_pid,
            message=f"Your action: {action}",
            observation_type=ta.ObservationType.PLAYER_ACTION
        )
        
                            
        if self._is_valid_action(action):
            self._process_valid_action(current_pid, action)
        
                                       
        deal_accepted = self._check_deal_accepted()
        max_turns_reached = self.state.turn >= self.max_rounds - 1
        
        if deal_accepted or max_turns_reached:
            self._end_game()
        
                                                          
        return self.state.step()
    
    def _is_valid_action(self, action: str) -> bool:
        pass                              
        action = action.strip()
        
                                                                    
        has_propose = "[Propose $" in action or ("[Propose]" in action and "$" in action)
        has_accept = "[Accept]" in action
        has_reject = "[Reject]" in action
        
                                                 
        action_count = sum([has_propose, has_accept, has_reject])
        
        if action_count == 0:
            self.state.set_invalid_move("Invalid action. Use: [Propose] $X.XX, [Accept], or [Reject]")
            return False
        elif action_count > 1:
            self.state.set_invalid_move("Multiple actions detected. Use only one action per turn: [Propose] $X.XX, [Accept], or [Reject]")
            return False
        
                                  
        if has_propose:
            if not self._is_valid_proposal(action):
                                                                    
                amount = self._extract_proposal_amount(action)
                if amount is None:
                    self.state.set_invalid_move("Invalid proposal format. Use: [Propose] $X.XX where X.XX is a valid dollar amount")
                elif amount < 0 or amount > self.total_amount:
                    self.state.set_invalid_move(f"Invalid amount ${amount:.2f}. Must be between $0.00 and ${self.total_amount:.2f}")
                else:
                    self.state.set_invalid_move("Invalid proposal format")
                return False
        
                                                                   
        if has_accept or has_reject:
            if self.current_proposal["amount"] is None:
                action_type = "accept" if has_accept else "reject"
                self.state.set_invalid_move(f"No current proposal to {action_type}")
                return False
            
                                                              
            if self.current_proposal["proposer"] == self.state.current_player_id:
                action_type = "accept" if has_accept else "reject"
                self.state.set_invalid_move(f"You cannot {action_type} your own proposal")
                return False
        
                                  
        valid, error_msg = self._validate_role_specific_action(self.state.current_player_id, action)
        if not valid:
            self.state.set_invalid_move(error_msg)
            return False
        
        return True
    
    def _is_valid_proposal(self, action: str) -> bool:
        pass                                                  
        try:
                                                 
            amount = self._extract_proposal_amount(action)
            if amount is None:
                return False
            
                                                          
            if amount < 0 or amount > self.total_amount:
                return False
            
            return True
        except Exception:
            return False
    
    def _extract_proposal_amount(self, action: str) -> Optional[float]:
        pass                                             
        try:
                                              
            match = re.search(r'\[Propose\]\s*\$(\d+(?:\.\d+)?)', action)
            if match:
                return float(match.group(1))
            return None
        except Exception:
            return None
    
    def _validate_role_specific_action(self, player_id: int, action: str) -> Tuple[bool, Optional[str]]:
        pass                                                    
        role = self.player_roles[player_id]
        
        if role.get("enforcement") == "action_validation":
            if role["name"] == "say_little":
                                                     
                message_part = action.split('[')[0].strip()
                word_count = len(message_part.split())
                if word_count > role["behavioral_rules"]["max_words_per_message"]:
                    return False, role["behavioral_rules"]["violation_message"].format(word_count=word_count)
            
            elif role["name"] == "high_tension" and ("[Propose $" in action or ("[Propose]" in action and "$" in action)):
                                                                      
                amount = self._extract_proposal_amount(action)
                proposals = self.player_proposal_history[player_id]
                
                if proposals and amount is not None and amount < proposals[-1]:                     
                    concession = proposals[-1] - amount
                    max_concession = role["behavioral_rules"]["max_concession"]
                    if concession > max_concession:
                        return False, role["behavioral_rules"]["violation_message"].format(concession=concession)
        
        return True, None
    
    def _process_valid_action(self, player_id: int, action: str):
        pass                         
        action = action.strip()
        
        if "[Propose]" in action and "$" in action:
            self._process_proposal(player_id, action)
        elif "[Accept]" in action:
            self._process_accept(player_id, action)
        elif "[Reject]" in action:
            self._process_reject(player_id, action)
    
    def _process_proposal(self, player_id: int, action: str):
        pass                          
                                      
        rationale = action.split("[Propose]")[0].strip()
        amount = self._extract_proposal_amount(action)
        
        if amount is None:
            return                                       
        
                                 
        self.current_proposal = {"amount": amount, "proposer": player_id}
        self.state.game_state["current_proposal"] = self.current_proposal
        
                           
        self._record_action(player_id, "propose", amount, rationale)
        
                               
        other_amount = self.total_amount - amount
        message = f"Player {player_id} proposes: ${amount:.2f} for themselves, ${other_amount:.2f} for their opponent"
        if rationale:
            message = f"Player {player_id} says: {rationale}\n{message}"
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _process_accept(self, player_id: int, action: str):
        pass                           
        rationale = action.split("[Accept]")[0].strip()
        
                           
        self._record_action(player_id, "accept", self.current_proposal["amount"], rationale)
        
                             
        message = f"Player {player_id} accepts the proposal"
        if rationale:
            message = f"Player {player_id} says: {rationale}\n{message}"
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _process_reject(self, player_id: int, action: str):
        pass                          
        rationale = action.split("[Reject]")[0].strip()
        
                           
        self._record_action(player_id, "reject", None, rationale)
        
                            
        message = f"Player {player_id} rejects the proposal"
        if rationale:
            message = f"Player {player_id} says: {rationale}\n{message}"

                                           
        self.current_proposal["amount"] = None
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _record_action(self, player_id: int, action_type: str, amount: Optional[float] = None, message: str = ""):
        pass                                 
        self.negotiation_history.append({
            "player_id": player_id,
            "action_type": action_type,
            "amount": amount,
            "message": message,
            "round": self.state.turn
        })
        
                                                    
        if action_type == "propose" and amount is not None:
            self.player_proposal_history[player_id].append(amount)
        
                           
        self.state.game_state["negotiation_history"] = self.negotiation_history
        self.state.game_state["player_proposal_history"] = self.player_proposal_history
    
    
    def _check_deal_accepted(self) -> bool:
        pass                                              
        if self.current_proposal["amount"] is None:
            return False
        
                                                             
        if self.negotiation_history:
            last_action = self.negotiation_history[-1]
                                                                                
            if (last_action["action_type"] == "accept" and 
                last_action["player_id"] != self.current_proposal["proposer"]):
                return True
        
        return False
    
    
    def _end_game(self):
        pass                                           
        if self._check_deal_accepted():
                               
            self._finalize_accepted_deal()
        else:
                             
            self._handle_no_deal()
        
        self.state.done = True
    
    def _finalize_accepted_deal(self):
        pass                                                      
        proposer_id = self.current_proposal["proposer"]
        accepter_id = 1 - proposer_id
        proposer_amount = self.current_proposal["amount"]
        accepter_amount = self.total_amount - proposer_amount
        
                             
        self.final_amounts[proposer_id] = proposer_amount
        self.final_amounts[accepter_id] = accepter_amount
        
                                               
        for player_id in [0, 1]:
            role = self.player_roles[player_id]
            player_amount = self.final_amounts[player_id]
            
                                     
            if role.get("enforcement") == "end_game_check":
                if role.get("threshold") is not None:
                    threshold = role.get("threshold", 0)
                    if player_amount < threshold:
                        self.final_amounts[player_id] = 0.0                    
                        
                elif role.get("name") == "x_rounds":
                                                      
                    deadline = self.player_deadline.get(player_id, self.max_rounds // 2)
                    met_deadline = False
                    for action in self.negotiation_history:
                        if (action["player_id"] == player_id and 
                            action["action_type"] == "accept" and 
                            action["round"] < deadline):
                            met_deadline = True
                            break
                    
                    if not met_deadline:
                        self.final_amounts[player_id] = 0.0                   
            
            elif role.get("enforcement") == "action_validation":
                                                                                 
                                                                        
                pass
        
                                
        deal_str = f"${self.final_amounts[0]:.2f} for Player 0, ${self.final_amounts[1]:.2f} for Player 1"
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=f"DEAL FINALIZED: {deal_str}",
            observation_type=ta.ObservationType.GAME_ADMIN
        )
        
                                 
        self._set_final_rewards()
    
    def _handle_no_deal(self):
        pass                                        
        self.final_amounts = {0: 0.0, 1: 0.0}
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message="NO DEAL REACHED - Both players receive $0.00",
            observation_type=ta.ObservationType.GAME_ADMIN
        )
        
                                 
        self._set_final_rewards()

    def _set_final_rewards(self):
        pass                                                   
                                                          
        winners = [pid for pid in [0, 1] if self.final_amounts[pid] > 0]
        
        if len(winners) == 2:
                                               
            if self.final_amounts[0] > self.final_amounts[1]:
                                   
                self.state.set_winner(player_id=0, reason=f"Player 0 received more money (${self.final_amounts[0]:.2f} vs ${self.final_amounts[1]:.2f})")
            elif self.final_amounts[1] > self.final_amounts[0]:
                                   
                self.state.set_winner(player_id=1, reason=f"Player 1 received more money (${self.final_amounts[1]:.2f} vs ${self.final_amounts[0]:.2f})")
            else:
                                      
                self.state.set_draw(reason=f"Both players received equal amounts (${self.final_amounts[0]:.2f} each)")
        elif len(winners) == 1:
                                 
            self.state.set_winner(player_id=winners[0], reason=f"Player {winners[0]} met their role requirements, Player {1 - winners[0]} failed")
        else:
                                      
            self.state.set_draw(reason="Both players failed to meet their role requirements")
    
    def get_observation(self):
        pass                                     
        player_id = self.state.current_player_id
        observation = self.state.get_current_player_observation()
        
                                       
        round_info = f"=== ROUND {self.state.turn + 1} of {self.max_rounds} ===\n"
        observation.append((ta.GAME_ID, round_info, ta.ObservationType.GAME_BOARD))
        
                                            
        if self.current_proposal["amount"] is not None:
            proposer_id = self.current_proposal["proposer"]
            amount = self.current_proposal["amount"]
            other_amount = self.total_amount - amount
            
            proposal_info = f"\nCURRENT PROPOSAL:\n"
            proposal_info += f"Player {proposer_id} wants ${amount:.2f}, Player {1 - proposer_id} gets ${other_amount:.2f}\n"
            
            observation.append((ta.GAME_ID, proposal_info, ta.ObservationType.GAME_BOARD))
        
        return player_id, observation

    def get_board_str(self) -> str:
        pass                                     
                                                      
                                                 
           
        if getattr(self.state, "done", False):
                                               
            summary = render_negotiation_summary(
                negotiation_history=self.negotiation_history,
                player_proposal_history=self.player_proposal_history,
                total_amount=self.total_amount,
            )
            results = render_final_results(
                final_amounts=self.final_amounts,
                player_roles=self.player_roles,
                total_amount=self.total_amount,
            )
            return f"{summary}\n\n{results}"
        
                               
        return render_game_state(
            current_proposal=self.current_proposal,
            total_amount=self.total_amount,
            negotiation_history=self.negotiation_history,
            max_history_items=5,
        )