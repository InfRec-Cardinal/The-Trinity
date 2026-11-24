import re
import random
from typing import Any, Dict, Optional, Tuple, List, Set
from functools import partial
import textarena as ta
from textarena.envs.Diplomacy.game_engine import DiplomacyGameEngine
from textarena.envs.Diplomacy.prompts.prompt import get_state_specific_prompt
import os

class DiplomacyEnv(ta.Env):
    pass                                                    
    broadcast_pattern = re.compile(
        r"(?:"
        r"\s*\[Broadcast\s*:\s*(.*?)\]"                                  
        r"|"
        r"\s*\[Broadcast((?:\s+).*?)\]"                                 
        r"|"
        r"\s*\[Broadcast\](\s+.*?)(?=\s*\[|$)"                          
        r")",
        re.IGNORECASE | re.DOTALL
    )
    
                               
    whisper_pattern = re.compile(
        r"\s*\[Whisper\s+(?:to\s+)?(?:Player\s+)?(\d+)(?:\s+\(([A-Z]+)\))?\s*:\s*(.*?)\]",
        re.IGNORECASE | re.DOTALL
    )
    
                                         
    submit_orders_pattern = re.compile(
        r"\[Submit\s+Orders\]([\s\S]*?)(?=\[|$)",
        re.IGNORECASE
    )

    def __init__(self, max_turns: int = 30, 
                negotiations_per_phase: int = 3):
        pass                                                 

             
                                                                                 
                                                                                    
           
        self.max_turns = max_turns
        self.negotiations_per_phase = negotiations_per_phase
        
                    
        self.engine = None
        self.player_power_map = {}
        self.power_player_map = {}
        self.current_negotiation_round = 0
        self.orders_submitted = set()                                        
        self.pending_orders = {}                                      
        self.current_season = None
        self.current_year = None
        self.current_phase = None
        self.chat_history: List[Dict[str, Any]] = []

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                              
        self.state = ta.State(num_players=num_players, min_players=3, max_players=7, seed=seed)
        
                                
        self.engine = DiplomacyGameEngine(max_turns=self.max_turns)
        self.player_power_map = self.engine.setup_game(num_players)
        self.state.role_mapping = self.player_power_map
        self.power_player_map = {power: player for player, power in self.player_power_map.items()}
        
                                   
        self.current_negotiation_round = 0
        self.orders_submitted = set()
        self.pending_orders = {}
        self.current_season = self.engine.season
        self.current_year = self.engine.year
        self.current_phase = self.engine.phase
        self.offers = {}
        self.next_offer_id = 1
        self.agreements = {}
        self.chat_history: List[Dict[str, Any]] = []

                                           
        game_state = self.engine.get_state()
        game_state['player_power_map'] = self.player_power_map
        game_state['powers_info'] = {power: {
            'home_centers': self.engine.powers[power].home_centers,
            'controlled_centers': self.engine.powers[power].controlled_centers,
            'units': [str(unit) for unit in self.engine.powers[power].units],
        } for power in self.player_power_map.values()}
        game_state['current_negotiation_round'] = 0
        game_state['total_negotiation_rounds'] = self.negotiations_per_phase

        player_prompt_function = partial(self._generate_player_prompt, player_power_map=self.player_power_map, start_of_game=True)
                              
        self.state.reset(
            game_state=game_state,
            player_prompt_function=player_prompt_function,
        )
        
                                                             
        self._announce_game_state()
        
        return self.state

    def _generate_player_prompt(self, player_power_map: Dict[str, str], player_id: int, game_state: Dict[str, Any], start_of_game: bool = False) -> str:
        pass                                                                                   
        
             
                                             
                                                 
                
                
                                      
           
        power_name = player_power_map.get(player_id)
        if not power_name:
            return "You are not an active player in this game."
            
        power_state = game_state['powers_info'].get(power_name, {})
        
                                        
        prompt = [
            f"# DIPLOMACY GAME - YOU ARE {power_name} (PLAYER {player_id})",
            "",
            "## GAME OVERVIEW",
            "Diplomacy is a strategic board game of negotiation, alliance-building, and tactical warfare set in pre-WWI Europe.",
            "The game revolves around diplomatic relations, military maneuvers, and territorial control.",
            "",
            "### GAME STRUCTURE",
            "- Each game year consists of Spring and Fall seasons, plus a Winter adjustment phase",
            "- Each season has a Movement phase and possibly a Retreat phase",
            "- After Fall, there's an Adjustment phase where you build new units or disband excess units",
            "- The game lasts until one power controls 18+ supply centers or until the maximum number of turns",
            f"- This game will last at most {self.max_turns} years",
            "",
            "### YOUR OBJECTIVE",
            "To win, you must control the majority of supply centers (currently 18 out of 34). This requires:",
            "1. Forming strategic alliances with other powers",
            "2. Coordinating attacks against common enemies",
            "3. Eventually outmaneuvering your allies to claim victory",
        ]
        
        prompt.extend([
            "",
            "## GAME MECHANICS",
            "",
            "### UNITS",
            "- Armies (A): Move on land, can be convoyed across water by fleets",
            "- Fleets (F): Move on water and coastal provinces, can convoy armies",
            "",
            "### ORDERS",
            "During Movement phases, you can issue these orders:",
            "- Hold: A unit from your power stays in place (e.g., 'A PAR H')",
            "- Move: A unit from your power moves to an adjacent territory (e.g., 'A PAR - BUR')",
            "- Support: A unit from your power supports another unit's position or move (e.g., 'A PAR S A MAR' or 'A PAR S A MAR - BUR')",
            "- Convoy: A fleet transports an army across water (e.g., 'F NTH C A LON - BEL')",
            "",
            "During Retreat phases, you can:",
            "- Retreat: Move a dislodged unit to an empty adjacent territory (e.g., 'A PAR R BUR')",
            "- Disband: Remove a dislodged unit from play (e.g., 'A PAR D')",
            "",
            "During Adjustment phases, depending on your center count vs. unit count (Build count = center count - unit count):",
            "- Build: Create new units in your unoccupied home centers (e.g., 'A PAR B')",
            "- Disband: Remove existing units if you have too many (e.g., 'A PAR D')",
            "- Waive: Choose not to build an allowed unit (e.g., 'WAIVE')",
            "",
            "### COMBAT RESOLUTION",
            "- All units have equal strength (1)",
            "- Support adds +1 strength per supporting unit",
            "- The unit with highest strength wins; equal strength units bounce (no movement)",
            "- A unit supporting a move is cut if attacked (unless the attack comes from the unit being supported)",
            "- A dislodged unit must retreat or be disbanded",
            "",
            f"## NEGOTIATION PROCESS ({self.negotiations_per_phase} ROUNDS PER PHASE)",
            f"Each game phase has {self.negotiations_per_phase} negotiation rounds before orders are submitted.",
            "Use these rounds to coordinate with other players through messages and form agreements.",
            "In the final negotiation round, you must submit your orders.",
            "",
            "## COMMUNICATION OPTIONS",
            "You can interact in the following ways:",
            "",
            "1. **Broadcast messages** - Send a message to all players",
            "   Example: [Broadcast: I propose we all focus on containing Russia this turn]",
            "   Alternative: [Broadcast] Let's coordinate our attacks against Turkey",
            "",
            "2. **Whisper messages** - Send a private message to another player",
            "   Example: [Whisper to 2: Would you be interested in coordinating against Germany?]",
            "   Alternative: [Whisper to 3 (ITALY): I can support your move to Trieste]",
            "",
            "3. **Submit orders** (final negotiation round only) - Send your orders for the current phase",
            "   Example:",
            "   ```",
            "   [Submit Orders]",
            "   A PAR - BUR",
            "   A MAR S A PAR - BUR",
            "   F BRE - MAO",
            "   ```",
            "",
            "You can combine multiple communication types in a single response:",
            "",
            "```",
            "[Broadcast: I'm looking to form alliances this turn]",
            "",
            "[Whisper to 1: I noticed England is threatening your northern border. I could help you against them if you agree not to attack me.]",
            "",
            "[Whisper to 3: Let's coordinate our fleets in the Mediterranean]",
            "```",
            "",
            "## STRATEGY TIPS",
            "1. Diplomacy is primarily a game of negotiation - communicate actively",
            "2. Form mutually beneficial alliances, but be prepared to break them when necessary",
            "3. Try to coordinate attacks with allies to ensure successful movements",
            "4. Defend your supply centers while looking for opportunities to capture others",
            "5. Balance short-term tactical gains with long-term strategic positioning",
            "",
            "### STATE SPECIFIC INSTRUCTIONS",
            f"{get_state_specific_prompt(power_name)}",
            "",
        ])
        
        if start_of_game:
            prompt.extend([
                "## CURRENT GAME STATE",
                f"It is {game_state['season']} {game_state['year']}, {game_state['phase']} phase.",
                f"This is negotiation round 1 of {game_state['total_negotiation_rounds']}.",
                "",
                "The game has just begun. Use this first negotiation round to establish initial diplomacy.",
                "",
                "Good luck, and may your diplomacy be successful!"
            ])
        
        return "\n".join(prompt)

    def format_power_units_and_centers(self, player_id: int):
        pass                                                                         
                                                          
        
             
                                                                                     
            
                
                                                                    
           
        if player_id == -1:
                           
            all_controlled_centers = set()
            for power in self.engine.powers.values():
                all_controlled_centers.update(power.controlled_centers)
            neutral_centers = []
            for center in self.engine.map.get_supply_centers():
                if center not in all_controlled_centers:
                    neutral_centers.append(center)
            return f"{len(neutral_centers)} SUPPLY CENTERS: " + ", ".join(neutral_centers)
        else:
            power_name = self.player_power_map[player_id]
            power = self.engine.powers[power_name]
            
                                       
            output = []
            power_str = f"{power_name} FORCES"
                                           
            if power.units:
                units_str = f"{len(power.units)} UNITS: "
                unit_details = []
                for unit in power.units:
                                                                         
                    unit_str = str(unit)
                    unit_type = unit_str[0]              
                    location = unit_str[2:]                 
                                                                                 
                    unit_details.append(f"{unit_type} {location}")
                units_str += "(" + ", ".join(unit_details) + ")"
            else:
                units_str = "0 units"
            
                                                    
            if power.controlled_centers:
                centers_str = f"{len(power.controlled_centers)} SUPPLY CENTERS: "
                                                                             
                centers_str += "(" + ", ".join(power.controlled_centers) + ")"
            else:
                centers_str = "0 supply centers"
            
                                  
            strength_summary = f"Current strength: {len(power.controlled_centers)} centers, {len(power.units)} units"
            
                               
            return f"{power_str}\n{units_str}\n{centers_str}\n{strength_summary}\n\n"
    
    def format_possible_orders(self, possible_orders):
        pass                                                                         
                                  
        
             
                                                                             
            
                
                                                    
           
                                                
        strategic_orders = {
            "OFFENSIVE": [],                                                           
            "DEFENSIVE": [],                                             
            "TACTICAL": [],                                                            
            "SUPPORT": []                     
        }
        
                                        
        supply_centers = set(self.engine.map.scs)
        
                                             
        power_centers = {}
        for power_name, power in self.engine.powers.items():
            for center in power.controlled_centers:
                power_centers[center] = power_name
        
                            
        for loc, orders in possible_orders.items():
            for order in orders:
                order_type = None
                
                                                            
                if " H" in order:
                    order_type = "DEFENSIVE"
                elif " S " in order:
                    order_type = "SUPPORT"
                elif " - " in order:
                                     
                    dest = order.split(" - ")[1].split(" VIA")[0] if " VIA" in order else order.split(" - ")[1]
                    
                                                             
                    if dest in supply_centers:
                                                                             
                        if dest not in power_centers or power_centers[dest] != self.player_power_map[self.state.current_player_id]:
                            order_type = "OFFENSIVE"
                        else:
                            order_type = "DEFENSIVE"                               
                    else:
                        order_type = "TACTICAL"                          
                elif " C " in order:
                    order_type = "SUPPORT"                              
                else:
                    order_type = "TACTICAL"                            
                
                                             
                if order_type:
                    strategic_orders[order_type].append(order)
        
                                   
        output = "POSSIBLE ORDERS:\n\n"
        
                                                                
        if strategic_orders["OFFENSIVE"]:
            output += "Offensive Moves (capture territory):\n"
            for order in strategic_orders["OFFENSIVE"]:
                output += f"  {order}\n"
            output += "\n"
        
                             
        if strategic_orders["DEFENSIVE"]:
            output += "Defensive Moves (protect territory):\n"
            for order in strategic_orders["DEFENSIVE"]:
                output += f"  {order}\n"
            output += "\n"
        
                                        
        if strategic_orders["TACTICAL"]:
            output += "Tactical Moves (improve position):\n"
            for order in strategic_orders["TACTICAL"]:
                output += f"  {order}\n"
            output += "\n"
        
                           
        if strategic_orders["SUPPORT"]:
            output += "Support Options (strengthen attacks/defense):\n"
            for order in strategic_orders["SUPPORT"]:
                output += f"  {order}\n"
        
        return output

    def get_prompt(self, player_id: int, history_text: str):
                              
        template = open("textarena/envs/Diplomacy/prompts/context_prompt.txt", "r").read()

                                  
        phase_info = self.expand_phase_info()

                               
        game_state = self.engine.get_state()
        game_state['player_power_map'] = self.player_power_map
        game_state['powers_info'] = {power: {
            'home_centers': self.engine.powers[power].home_centers,
            'controlled_centers': self.engine.powers[power].controlled_centers,
            'units': [str(unit) for unit in self.engine.powers[power].units],
        } for power in self.player_power_map.values()}
        game_state['current_negotiation_round'] = self.current_negotiation_round
        game_state['total_negotiation_rounds'] = self.negotiations_per_phase

                                    
        game_state['our_state_summary_text'] = self.format_power_units_and_centers(player_id)
        
                                  
        enemies_forces_summary = ""
        for pwr_id, pwr in self.player_power_map.items():
            if pwr_id != player_id:
                enemies_forces_summary += self.format_power_units_and_centers(pwr_id)
        game_state['other_state_summary_text'] = enemies_forces_summary

                                  
        neutral_supply_centers_summary = self.format_power_units_and_centers(-1)
        game_state['neutral_state_summary_text'] = neutral_supply_centers_summary

                            
        possible_orders = self.engine.get_possible_orders(self.player_power_map[player_id])
        possible_orders_text = self.format_possible_orders(possible_orders)
        game_state['possible_orders_text'] = possible_orders_text

                   
        prompt = template.format(
            phase_info=phase_info,
            history_text=history_text,
            our_state_summary_text=game_state['our_state_summary_text'],
            other_state_summary_text=game_state['other_state_summary_text'],
            neutral_state_summary_text=game_state['neutral_state_summary_text'],
            possible_orders_text=game_state['possible_orders_text'],
        )

        print(prompt)
        game_settings_prompt = self._generate_player_prompt(player_power_map=self.player_power_map, player_id=player_id, game_state=game_state, start_of_game=False)

        return game_settings_prompt + "\n\n" + prompt

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                              
        
             
                                                                
            
                
                                                                            
           
        current_pid = self.state.current_player_id
        power_name = self.player_power_map.get(current_pid)
        
        if not power_name:
            done, info = self.state.step(rotate_player=False)
            info['reason'] = "Skipped"
            info['detailed_reason'] = "You are not an active player in this game."
            return done, info
        
                                                                             
        self.add_observation(from_id=current_pid, to_id=current_pid, message=action)
        
                                           
        actions, game_state_changed = self._process_player_action(current_pid, power_name, action)
        
        if game_state_changed:                                            
                                   
            game_completed = self.engine.game_over
            if game_completed:
                self._announce_game_result()
                done, info = self.state.step(rotate_player=False)
                info.update({
                    'reason': "Game Over",
                    'detailed_reason': f"Game ended after {self.engine.turn_number} turns. The winners are {self.engine.winners}.",
                    'winners': self.engine.winners,
                    'winning_players': [self.power_player_map[power] for power in self.engine.winners] if self.engine.winners else [],
                    'final_sc_count': {power: len(self.engine.powers[power].controlled_centers) for power in self.engine.powers},
                    'turn_number': self.engine.turn_number
                })
                return done, info
                
                                                      
                                
        
        done, info = self.state.step(rotate_player=True)
                                                         
        if self.state.current_player_id == 0 and not game_state_changed:
            self._advance_negotiation_round()
        
                                      
        info.update({
            'current_player': current_pid,
            'current_power': power_name,
            'actions': actions
        })
        
        return done, info

    def _process_player_action(self, player_id: int, power_name: str, action: str) -> Tuple[Dict, bool]:
        pass                                                                              
        
             
                                          
                                            
                                           
            
                
                                                                                      
           
        game_state_changed = False
        action_summary = {
            "broadcasts": [],
            "whispers": [],
            "orders_submitted": False,
            "orders": []
        }
        
                            
        for match in self.broadcast_pattern.finditer(action):
            message = match.group(1) or match.group(2) or match.group(3)
            if message:
                                   
                self.add_observation(from_id=player_id, to_id=-1, message=message)
                action_summary["broadcasts"].append(message)
        
                          
        for match in self.whisper_pattern.finditer(action):
            target_id = int(match.group(1))
            target_power = match.group(2)
            message = match.group(3)
            
                                               
            if target_power and self.player_power_map.get(target_id) != target_power:
                continue
            
                                              
            self.add_observation(from_id=player_id, to_id=target_id, message=message)
            action_summary["whispers"].append({
                "to_player": target_id,
                "to_power": self.player_power_map.get(target_id),
                "message": message
            })
        
                                  
        if self.current_negotiation_round == self.negotiations_per_phase - 1:
            for match in self.submit_orders_pattern.finditer(action):
                orders_text = match.group(1).strip()
                if orders_text:
                    self._handle_orders_submission(player_id, power_name, orders_text)
                    action_summary["orders_submitted"] = True
                    action_summary["orders"].append(orders_text)
            
                                                                                      
            if len(self.orders_submitted) == len(self.player_power_map):
                game_state_changed = self._process_orders()

        return action_summary, game_state_changed


    def _rotate_players(self):
        pass                           
        current_player_id = self.state.current_player_id
        next_player_id = (current_player_id + 1) % self.state.num_players
        while next_player_id != current_player_id:
            self.state.manually_update_current_player(new_player_id=next_player_id)
            break
                                                                             
                                                                                         
                       
                                                
                                                                            
               
                                                                                                                                                   

    def _handle_orders_submission(self, player_id: int, power_name: str, orders_text: str):
        pass                                       
                                   
        orders = [line.strip() for line in orders_text.split('\n') 
                 if line.strip() and not line.strip().startswith('#')]
    
                                                           
        self.pending_orders[power_name] = orders
        self.orders_submitted.add(player_id)
        
                                                  
        msg = f"[Orders received for {power_name} ({len(orders)} orders)]"
        self.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=msg)

    def _process_orders(self) -> bool:
        pass                              
                                     
        phase_changed, new_state = self.engine.resolve_orders(self.pending_orders)
        
                           
        new_state['player_power_map'] = self.player_power_map
        self.state.game_state = new_state
        
                               
        self.current_season = self.engine.season
        self.current_year = self.engine.year
        self.current_phase = self.engine.phase
        
                                         
        self._announce_order_results()
        
                              
        self.orders_submitted = set()
        self.pending_orders = {}
        self.current_negotiation_round = 0
        
                           
        self.state.game_state['current_negotiation_round'] = 0
        
        return True

    def _advance_negotiation_round(self):
        pass                                       
        self.current_negotiation_round += 1
        self.state.game_state['current_negotiation_round'] = self.current_negotiation_round
        
                                                            
        if self.current_negotiation_round < self.negotiations_per_phase:
            message=(f"[Negotiation Round {self.current_negotiation_round + 1} of "
                       f"{self.negotiations_per_phase} begins]")
            self.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
                
                                                                         
            if self.current_negotiation_round == self.negotiations_per_phase - 1:
                message="[Final negotiation round: Please submit your orders]"
                self.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
        else:
                                                                         
            if self.pending_orders:
                self._process_orders()


    def _announce_game_state(self):
        pass                                                
        phase_type = self.engine.phase.value
        season = self.engine.season.value
        year = self.engine.year
        
                                     
        announcement = (
            f"===== {season} {year} {phase_type} Phase Begins =====\n"
            f"Current supply center counts:\n"
        )
        
                                                 
        for power_name, player_id in self.power_player_map.items():
            centers = len(self.engine.powers[power_name].controlled_centers)
            units = len(self.engine.powers[power_name].units)
            announcement += f"- Player {player_id} ({power_name}): {centers} centers, {units} units\n"
        
                             
        for player_id in self.player_power_map.keys():
            self.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=announcement)

    def _announce_order_results(self):
        pass                                       
                                   
        base_announcement = (
            f"===== Order Results: {self.current_season.value} {self.current_year} =====\n"
        )
        
                                                                   
        for player_id, power_name in self.player_power_map.items():
            power_announcement = base_announcement
            
                                        
            if power_name in self.pending_orders:
                power_announcement += f"\nYour orders ({power_name}):\n"
                for order in self.pending_orders[power_name]:
                    power_announcement += f"- {order}\n"
            
                                                               
            power_announcement += "\nOther powers' orders:\n"
            for other_power, orders in self.pending_orders.items():
                if other_power != power_name:
                    power_announcement += f"\n{other_power}:\n"
                    for order in orders:
                        power_announcement += f"- {order}\n"
            
                            
            self.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=power_announcement)
        
                            
        self._announce_game_state()

    def _announce_game_result(self):
        pass                                         
        if self.engine.winners:
                                  
            winners_text = ", ".join(self.engine.winners)
            winning_players = [self.power_player_map[power] for power in self.engine.winners]
            winning_players_text = ", ".join(f"Player {pid}" for pid in winning_players)
            
            reason = (
                f"Victory achieved by: {winners_text} ({winning_players_text})\n\n"
                f"Final supply center counts:\n"
            )
            self.state.set_winners(player_ids=winning_players, reason=reason)
        else:
                               
            reason = (
                f"Game ended in a DRAW after {self.engine.turn_number} turns.\n\n"
                f"Final supply center counts:\n"
            )
            self.state.set_draw(reason=reason)

        announcement = "Game Results:\n" + reason
                                        
        for power_name, player_id in self.power_player_map.items():
            if power_name in self.engine.powers:
                centers = len(self.engine.powers[power_name].controlled_centers)
                announcement += f"- Player {player_id} ({power_name}): {centers} centers\n"
        
                                  
        announcement += "\nGame Summary:\n"
        for entry in self.engine.history:
            announcement += f"- {entry['phase']}\n"

                             
        for player_id in self.player_power_map.keys():
            self.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=announcement)

    def add_observation(self, from_id: int, to_id: int, message: str):
        pass                                        
        self.chat_history.append({
            "turn": self.state.turn,
            "from": from_id,
            "from_power": self.player_power_map.get(from_id),
            "to": to_id,
            "to_power": self.player_power_map.get(to_id),
            "message": message
        })
        self.state.add_observation(from_id=from_id, to_id=to_id, message=message)

    def get_game_state(self):
        game_state = {
                                    
            "current_season": self.current_season.value,
            "current_year": self.current_year,
            "current_phase": self.current_phase.value,
            "current_negotiation_round": self.current_negotiation_round,
            "total_negotiation_rounds": self.negotiations_per_phase,
                                 
            "Players": [
                {
                    "id": player_id,
                    "power": self.player_power_map[player_id],
                    "controlled_centers": len(self.engine.powers[self.player_power_map[player_id]].controlled_centers),
                    "units": len(self.engine.powers[self.player_power_map[player_id]].units)
                }
                for player_id in self.player_power_map.keys()
            ],
                                
            "orders_submitted": list(self.orders_submitted),
            "pending_orders_count": {power: len(orders) for power, orders in self.pending_orders.items()},
            "sc_counts": {power: len(self.engine.powers[power].controlled_centers) for power in self.engine.powers},
            "unit_counts": {power: len(self.engine.powers[power].units) for power in self.engine.powers},
            "is_final_round": self.current_negotiation_round == self.negotiations_per_phase - 1,
        }
        
        return game_state

    def get_conversation_history(self) -> List[List[Dict[str, Any]]]:
        pass                                                                
                                                                    
        max_turn = 0
        turn_messages = {}
        
                                                  
        for entry in self.chat_history:
            turn = entry["turn"]
            
                                                      
            message = entry["message"]
            if "[Whisper to" in message:
                                                               
                message = re.sub(r"\[Whisper to \d+(?:\s+\([A-Z]+\))?: ", "", message)
                entry["message"] = message
            
                              
            if turn not in turn_messages:
                turn_messages[turn] = []
            
                                                        
            clean_entry = {
                "from": entry["from_power"] if entry["from_power"] else ("GAME" if entry["from"] == ta.GAME_ID else f"Player {entry['from']}"),
                "to": entry["to_power"] if entry["to"] != -1 and entry["to_power"] else ("ALL" if entry["to"] == -1 else f"Player {entry['to']}"),
                "message": message,
                "turn": turn
            }
            turn_messages[turn].append(clean_entry)
            
            max_turn = max(max_turn, turn)
        
                                                   
        conversation_history = [[] for _ in range(max_turn + 1)]
        for turn, messages in turn_messages.items():
            conversation_history[turn] = messages
        
        return conversation_history
    
    def get_order_history(self) -> Dict[str, Any]:
        pass                               
        return self.engine.order_history
    
    def get_game_state_history(self) -> List[Dict[str, Any]]:
        pass                            
        return self.engine.game_state_history
    
    def expand_phase_info(self):
        pass                                                                     
                                                                                  
                                                                                       
           
        season = self.engine.season.value
        year = self.engine.year
        phase = self.engine.phase.value
                                        
        
                                
        if year <= 1902:
            stage = "early game"
        elif year <= 1906:
            stage = "mid game"
        else:
            stage = "late game"
        
                                    
        if phase == 'Movement':
            actions = "Players issue move, support, or convoy orders."
        elif phase == 'Retreats':
            actions = "Dislodged units must retreat or disband."
        elif phase == 'Adjustments':
            actions = "Powers may build new units if they have more centers than units, otherwise disband if fewer."
        else:
            actions = "Unknown phase actions."
        
        return f"{season} {year} {phase} ({stage}): {actions}"

    def generate_phase_summary(self, phase_history):
                                                                         
        game_state_history = self.get_game_state_history()
        game_state_changes = ""
        if len(game_state_history) >= 2:
            current_state = game_state_history[-1]
            previous_state = game_state_history[-2]
            
                                          
            sc_changes = []
            for power in current_state["sc_counts"]:
                current_sc = current_state["sc_counts"][power]
                previous_sc = previous_state["sc_counts"].get(power, 0)
                if current_sc != previous_sc:
                    change = current_sc - previous_sc
                    sc_changes.append(f"{power}: {'+' if change > 0 else ''}{change} supply centers")
            
            if sc_changes:
                game_state_changes += "Supply Center Changes:\n" + "\n".join(sc_changes) + "\n\n"
            
                                 
            unit_changes = []
            for power in current_state["unit_counts"]:
                current_units = current_state["unit_counts"][power]
                previous_units = previous_state["unit_counts"].get(power, 0)
                if current_units != previous_units:
                    change = current_units - previous_units
                    unit_changes.append(f"{power}: {'+' if change > 0 else ''}{change} units")
            
            if unit_changes:
                game_state_changes += "Unit Count Changes:\n" + "\n".join(unit_changes) + "\n\n"
        
                                      
        with open(os.path.join(os.path.dirname(__file__), "prompts", "phase_summary_prompt.txt"), "r") as f:
            prompt = f.read()
        
                                                                         
        prompt = prompt.format(phase_history=phase_history, game_state_changes=game_state_changes)
        
                                                       