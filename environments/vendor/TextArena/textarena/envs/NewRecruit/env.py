import re, random
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta
from textarena.envs.NewRecruit.renderer import create_board_str


class NewRecruitEnv(ta.Env):
    pass                                                                                                                          
                                                                                                                        
                                                                                                           
                                                                                 
       

    def __init__(self, max_turns: int = 10, error_allowance: int=3):
        pass                                               
        
             
                                                                                    
                                                                                         
           
        super().__init__()
        self.max_turns = max_turns
        self.error_allowance = error_allowance
        
                                                          
        self.accept_pattern = re.compile(r"\[Accept\]", re.IGNORECASE)
        self.reject_pattern = re.compile(r"\[Reject\]", re.IGNORECASE)
        self.letter_sequence_pattern = re.compile(r"\[Propose\]\s*([A-E]( ?[A-E]){7})", re.IGNORECASE)
        
                                                                   
        self.point_value_dict = {
                          
            "Salary": {
                "$60000": [-6000, 0],
                "$58000": [-4500, -1500],
                "$56000": [-3000, -3000],
                "$54000": [-1500, -4500],
                "$52000": [0, -6000]
            },
            "Signing Bonus": {
                "10%": [0, 4000],
                "8%": [1000, 3000],
                "6%": [2000, 2000],
                "4%": [3000, 1000],
                "2%": [4000, 0]
            },
                        
            "Job Assignment": {
                "Division A": [0, 0],
                "Division B": [-600, -600],
                "Division C": [-1200, -1200],
                "Division D": [-1800, -1800],
                "Division E": [-2400, -2400]
            },
            "Company Car": {
                "LUX EX2": [1200, 1200],
                "MOD 250": [900, 900],
                "RAND XTR": [600, 600],
                "DE PAS 450": [300, 300],
                "PALO LSR": [0, 0]
            },
                         
            "Starting Date": {
                "Jun 1": [1600, 0],
                "Jun 15": [1200, 1000],
                "Jul 1": [800, 2000],
                "Jul 15": [400, 3000],
                "Aug 1": [0, 4000]
            },
            "Vacation Days": {
                "30 days": [0, 1600],
                "25 days": [1000, 1200],
                "20 days": [2000, 800],
                "15 days": [3000, 400],
                "10 days": [4000, 0]
            },
            "Moving Expense Reimbursement": {
                "100%": [0, 3200],
                "90%": [200, 2400],
                "80%": [400, 1600],
                "70%": [600, 800],
                "60%": [800, 0]
            },
            "Insurance Coverage": {
                "Allen Insurance": [0, 800],
                "ABC Insurance": [800, 600],
                "Good Health Insurance": [1600, 400],
                "Best Insurance Co.": [2400, 200],
                "Insure Alba": [3200, 0]
            },
        }
        
                                               
        self.issue_categories = {
            "distributive": ["Salary", "Signing Bonus"],
            "compatible": ["Job Assignment", "Company Car"],
            "integrative": ["Starting Date", "Vacation Days", "Moving Expense Reimbursement", "Insurance Coverage"]
        }
        
                            
        self.issues = list(self.point_value_dict.keys())
        
                                                                     
        self.choice_letters = {}
        letters = ['A', 'B', 'C', 'D', 'E']
        for issue in self.issues:
            self.choice_letters[issue] = {}
            choices = list(self.point_value_dict[issue].keys())
            for i, choice in enumerate(choices):
                if i < len(letters):
                    self.choice_letters[issue][letters[i]] = choice
                    
                                                                        
        self.letter_choices = {}
        for issue in self.issues:
            self.letter_choices[issue] = {}
            for letter, choice in self.choice_letters[issue].items():
                self.letter_choices[issue][choice] = letter

    def get_board_str(self):
        pass                                                        
        
                
                                                             
           
        return create_board_str(
            game_state=self.state.game_state,
            player_id=self.state.current_player_id
        )

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                                   
        
             
                                                                         
                                                                       
           
                              
        self.state = ta.TwoPlayerState(num_players=num_players,
                                       max_turns=self.max_turns,
                                       error_allowance=self.error_allowance,
                                       seed=seed)
        
                               
        game_state = {
            "roles": {0: "Recruiter", 1: "Candidate"},
            "current_proposal": None,
            "accepted_proposal": None,
            "current_rationale": None,
            "proposal_history": [],
            "player_preferences": {
                0: {issue: {choice: self.point_value_dict[issue][choice][0] for choice in self.point_value_dict[issue]} for issue in self.issues},
                1: {issue: {choice: self.point_value_dict[issue][choice][1] for choice in self.point_value_dict[issue]} for issue in self.issues}
            }
        }
        
                                                                        
        self.state.reset(game_state=game_state, player_prompt_function=self._prompt)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                 
        
             
                                                                 
            
                
                                                                                                                  
           
                                                     
        self.state.add_observation(
            from_id=self.state.current_player_id,
            message=action,
            observation_type=ta.ObservationType.PLAYER_ACTION
        )
        
                            
        self._process_action(action)
        
                                                        
        if self.state.check_turn_limit():
            self._end_game_with_zero_points("Maximum number of turns reached without an accepted proposal.")
        
                        
        return self.state.step()

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        pass                                         
        
             
                                                  
                                                                
            
                
                                           
           
        role = game_state["roles"][player_id]
        opponent_role = game_state["roles"][1 - player_id]
        
                                                                                        
        preferences_str = ""
        for issue in self.issues:
            preferences_str += f"\n{issue}:\n"
            choices = list(self.point_value_dict[issue].keys())
            for i, choice in enumerate(choices):
                if i < len(self.choice_letters[issue]):
                    letter = list(self.choice_letters[issue].keys())[i]
                    points = self.point_value_dict[issue][choice][player_id]
                    preferences_str += f"  {letter}. {choice}: {points} points\n"
        
                                                           
        issue_order_str = "\n".join([f"{i+1}. {issue}" for i, issue in enumerate(self.issues)])
        
                           
        prompt = (
            f"You are the {role} in the New Recruit negotiation game.\n\n"
            f"Your preferences for each issue are as follows (higher points are better):{preferences_str}\n"
            f"You are negotiating with the {opponent_role}. You can only see your own preferences, not theirs.\n\n"
            "The issues are in this order:\n"
            f"{issue_order_str}\n\n"
            "Available actions:\n"
            f"  - Write your rationale to convince the {opponent_role}, followed by a proposal using letter choices:\n"
            f"    You may say anything (truths, lies, all in between) to persuade the {opponent_role} to accept the proposal.\n"
            "    Example format:\n"
            "    ```\n"
            "    I believe this proposal is fair because it balances our interests.\n"
            "    [Propose] CCAACCCC\n"
            "    ```\n"
            "    Where each letter corresponds to a choice for each issue in the order listed above.\n"
            "    You must always propose one letter A-E for each issue, 8 letters in total.\n"
            "  - [Accept]: Accept the current proposal.\n"
            "  - [Reject]: Reject the current proposal.\n\n"
            f"The game will end after {self.max_turns} turns if no proposal is accepted, resulting in 0 points for both players.\n"
            "Your goal is to maximize your points by negotiating effectively."
        )
        
                                                                    
        if game_state["current_proposal"]:
            proposer_id = game_state["current_proposal"]["proposer_id"]
            proposer_role = game_state["roles"][proposer_id]
            proposal_str = self._proposal_to_str(game_state["current_proposal"]["choices"])
            prompt += f"\n\nCurrent proposal from {proposer_role}:\n{proposal_str}\n"
            prompt += "You can [Accept] or [Reject] this proposal."
        
        return prompt

    def _process_action(self, action: str):
        pass                                  
        
             
                                                                 
           
        current_player_id = self.state.current_player_id
        game_state = self.state.game_state
        
                                                     
        if game_state["current_proposal"] and self.accept_pattern.search(action):
            self._accept_proposal()
            return
        
                                                     
        if game_state["current_proposal"] and self.reject_pattern.search(action):
            self._reject_proposal()
            return
        
                                                      
        letter_sequence_match = self.letter_sequence_pattern.search(action)
        
                                                             
        if letter_sequence_match:
                                             
            rationale_text = action.split("[Propose]")[0].strip()
            if rationale_text:
                self.state.game_state["current_rationale"] = rationale_text
            else:
                self.state.game_state["current_rationale"] = None

                                              
            raw_sequence = letter_sequence_match.group(1)
            letter_sequence = re.sub(r'[^A-Ea-e]', '', raw_sequence).upper()
            parsed_proposal = self._parse_letter_sequence(letter_sequence)
            
            if parsed_proposal:
                                     
                game_state["current_proposal"] = {
                    "proposer_id": current_player_id,
                    "choices": parsed_proposal
                }
                
                                         
                proposal_entry = {
                    "proposer_id": current_player_id,
                    "choices": parsed_proposal,
                    "accepted": False
                }
                
                                            
                if "current_rationale" in game_state and game_state["current_rationale"]:
                    proposal_entry["rationale"] = game_state["current_rationale"]
                
                game_state["proposal_history"].append(proposal_entry)
                
                                                        
                self.state.add_observation(
                    message=f"Player {current_player_id} ({game_state['roles'][current_player_id]}) made a new proposal.",
                    observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
                )
            else:
                                         
                self.state.set_invalid_move(reason="Invalid proposal format. Please use the format [Propose] ABCDEFGH where each letter (A-E) corresponds to a choice for each issue.")
        else:
                                   
            self.state.set_invalid_move(reason=f"Invalid action. Please use [Propose] followed by 8 letters (A-E), or [Accept]/[Reject] when there's a current proposal.")


    def _proposal_to_str(self, proposal: Dict[str, str]) -> str:
        pass                                                                 
        
             
                                                               
            
                
                                                           
           
        result = []
        
                                    
        if "current_rationale" in self.state.game_state and self.state.game_state["current_rationale"]:
            result.append(f"Rationale: {self.state.game_state['current_rationale']}")
            result.append("")                                            
        
                                
        letter_sequence = ""
        for issue in self.issues:
            if issue in proposal:
                choice = proposal[issue]
                letter = self.letter_choices[issue].get(choice, "")
                letter_sequence += letter if letter else "?"
        
                             
        result.append(f"Letter sequence: [Propose] {letter_sequence}")
        result.append("")                                            
        
                                                              
        for issue, choice in proposal.items():
            letter = self.letter_choices[issue].get(choice, "")
            if letter:
                result.append(f"- {issue}: {letter}. {choice}")
            else:
                result.append(f"- {issue}: {choice}")
        
        return "\n".join(result)

    def _accept_proposal(self):
        pass                                                     
           
        game_state = self.state.game_state
        current_proposal = game_state["current_proposal"]
        
        if current_proposal:
                                           
            for i, proposal in enumerate(game_state["proposal_history"]):
                if (proposal["proposer_id"] == current_proposal["proposer_id"] and 
                    proposal["choices"] == current_proposal["choices"]):
                    game_state["proposal_history"][i]["accepted"] = True
                    break
            
            game_state["accepted_proposal"] = current_proposal
            
                              
            recruiter_score = self._calculate_score(0, current_proposal["choices"])
            candidate_score = self._calculate_score(1, current_proposal["choices"])
            
                                                         
            self.state.add_observation(
                message=f"Player {self.state.current_player_id} ({game_state['roles'][self.state.current_player_id]}) accepted the proposal.",
                observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
            )
            
                                            
            if recruiter_score > candidate_score:
                self.state.set_winner(player_id=0, reason=f"Recruiter wins with {recruiter_score} points vs Candidate's {candidate_score} points.")
            elif candidate_score > recruiter_score:
                self.state.set_winner(player_id=1, reason=f"Candidate wins with {candidate_score} points vs Recruiter's {recruiter_score} points.")
            else:
                self.state.set_draw(reason=f"Draw with both players scoring {recruiter_score} points.")

    def _reject_proposal(self):
        pass                                                          
           
        game_state = self.state.game_state
        
                                                     
        self.state.add_observation(
            message=f"Player {self.state.current_player_id} ({game_state['roles'][self.state.current_player_id]}) rejected the proposal.",
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
        
                                    
        game_state["current_proposal"] = None

    def _calculate_score(self, player_id: int, proposal: Dict[str, str]) -> int:
        pass                                                             
        
             
                                                  
                                                               
            
                
                                          
           
        score = 0
        for issue, choice in proposal.items():
            score += self.point_value_dict[issue][choice][player_id]
        return score

    def _parse_letter_sequence(self, letter_sequence: str) -> Optional[Dict[str, str]]:
        pass                                                                            
        
             
                                                                                   
            
                
                                                                                                       
           
        try:
                                                                 
            if len(letter_sequence) != len(self.issues):
                return None

                                            
            proposal = {}
            for i, issue in enumerate(self.issues):
                letter = letter_sequence[i].upper()
                if letter not in self.choice_letters[issue]:
                    return None

                choice = self.choice_letters[issue][letter]
                proposal[issue] = choice

            return proposal
        except Exception:
                                                                             
                                                          
            return None

    def _end_game_with_zero_points(self, reason: str):
        pass                                                       
        
             
                                                         
           
        self.state.set_draw(reason=reason)
        self.state.rewards = {0: 0, 1: 0}
