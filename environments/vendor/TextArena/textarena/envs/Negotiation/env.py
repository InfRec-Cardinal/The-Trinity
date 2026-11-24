import re, random
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta


class NegotiationEnv(ta.Env):
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
        r"\s*\[Whisper\s+(?:to\s+)?(?:Player\s+)?(\d+)\s*:\s*(.*?)\]",
        re.IGNORECASE | re.DOTALL
    )

                               
    offer_pattern = re.compile(
        r"\[Offer\s+(?:to\s+)?(?:Player\s+)?(\d+)\s*:?\s*(.*?)\]",
        re.IGNORECASE | re.DOTALL
    )
    accept_pattern = re.compile(r"\[Accept\s*#?\s*(\d+)\]", re.IGNORECASE)
    deny_pattern = re.compile(r"\[Deny\s*#?\s*(\d+)\]", re.IGNORECASE)

    def __init__(self, turn_multiple: int = 3):
        pass                                                             

             
                                                           
           
        
        self.resource_names = ["Wheat", "Wood", "Sheep", "Brick", "Ore"]
        self.base_values = {"Wheat": 5, "Wood": 10, "Sheep": 15, "Brick": 25, "Ore": 40}

        self.turn_multiple = turn_multiple

    @property
    def terminal_render_keys(self):
        return ["player_resources", "player_values", "pending_offers"]

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                              
                                          
        self.state = ta.State(num_players=num_players, min_players=2, max_players=15, max_turns=int(num_players*self.turn_multiple), seed=seed)

                                                              
                                                        
        player_resources = {}
        player_values = {}
        for pid in range(self.state.num_players):
                                    
            player_resources[pid] = {
                r: random.randint(5, 25) for r in self.resource_names
            }
                                                                            
            player_values[pid] = {}
            for r in self.resource_names:
                base = self.base_values[r]
                variation = int(0.2 * base)        
                low, high = max(5, base - variation), min(40, base + variation)
                player_values[pid][r] = random.randint(low, high)

                         
        game_state = {
            "player_resources": player_resources,
            "player_values": player_values,
            "pending_offers": {},
            "offer_id_counter": 0,
        }
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)


    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        pass                                                                    
                                                              
           
        resources = game_state["player_resources"][player_id]
        valuations = game_state["player_values"][player_id]
        resource_lines = []
        for r in self.resource_names:
            qty = resources[r]
            val = valuations[r]
            resource_lines.append(f"- {qty} x {r} (value: {val} each)")
        resource_str = "\n".join(resource_lines)

        prompt = (
            f"You are Player {player_id} in a multi-player game of Negotiation with {self.state.num_players} players.\n"
            f"You have:\n{resource_str}\n\n"
            "You can broadcast messages, privately message someone, or make trade offers.\n"
            "You can also accept or deny any offers you received previously.\n"
            f"Your personal valuations are shown above; your goal is to maximize your total resource value.\n"
            "Available actions:\n"
            "  '[Broadcast: Some message]' - Send a message to all players\n"
            "  '[Whisper to X: Some message]' - Send a private message to a specific player\n"
            "  '[Offer to X: 2 Wheat -> 3 Wood]' - Make a trade offer to a specific player\n"
            "  '[Accept <x>]' or '[Deny <x>]' - Accept or Deny a trade offer\n"
            "You may combine multiple tokens in a single turn if you like.\n"
        )
        if self.state.max_turns is not None:
            prompt += f"Game ends after {self.state.max_turns} turns.\n"
        return prompt

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                                      
                                                                              
           
        current_pid = self.state.current_player_id
                                          
                                                                 
        self.state.add_observation(from_id=current_pid, to_id=current_pid, message=action)

                                                        
                                                                                           
                                                                                      
        self._process_broadcasts(current_pid, action)
        self._process_private_messages(current_pid, action)
        self._process_offers(current_pid, action)
        self._process_accepts_and_denies(current_pid, action)

                                                                                      
        if self.state.turn == (self.state.max_turns or 0) - 1:
            self._determine_winner()

                                                
        return self.state.step()

                                                            
    def _parse_broadcast(self, text: str) -> List[str]:
        pass                                                   
                                                                     
                                                        
           
        results = []
        raw = self.broadcast_pattern.findall(text)
        for g1, g2, g3 in raw:
            msg = g1 or g2 or g3
            if msg and msg.strip():
                                                 
                if not msg.startswith(" "):
                    msg = " " + msg
                results.append(msg)
        return results

    def _parse_whisper(self, text: str) -> List[Tuple[str, str]]:
        pass                                               
                                                       
                                                 
           
        results = []
        matches = self.whisper_pattern.findall(text)
        for pid_str, msg in matches:
            if msg and not msg.startswith(" "):
                msg = " " + msg
            results.append((pid_str, msg))
        return results

                                
    def _process_broadcasts(self, from_pid: int, action: str):
        pass                                                               
        messages = self._parse_broadcast(action)
        for msg_content in messages:
                                                            
            if msg_content.strip():
                message = f"(Broadcast) Player {from_pid} says:{msg_content}"
                self.state.add_observation(from_id=from_pid, to_id=-1, message=message)

    def _process_private_messages(self, from_pid: int, action: str):
        pass                                                                     
                                                                                    
           
        matches = self._parse_whisper(action)
        for target_str, msg_content in matches:
            msg_content = msg_content.strip()
            try:
                target_pid = int(target_str)
            except ValueError:
                self.state.set_invalid_move(player_id=from_pid, reason=f"Invalid private-message target: {target_str}")
                continue

            if target_pid not in range(self.state.num_players):
                self.state.set_invalid_move(player_id=from_pid, reason=f"Attempted to message a non-existent player {target_pid}.")
                continue

            if msg_content:
                message = f"(Private) Player {from_pid} says:{msg_content}"
                self.state.add_observation(from_id=from_pid, to_id=target_pid, message=message)
            else:
                self.state.set_invalid_move(player_id=from_pid, reason="Empty private message?")

    def _process_offers(self, from_pid: int, action: str):
        pass                                                       
                                                                     
           
        game_state = self.state.game_state
        matches = self.offer_pattern.findall(action)
                                                                 
        for target_str, offer_str in matches:
            offer_str = offer_str.strip()
            try:
                target_pid = int(target_str)
            except ValueError:
                self.state.set_invalid_move(player_id=from_pid, reason=f"Invalid offer target: {target_str}")
                continue
            if target_pid not in range(self.state.num_players):
                self.state.set_invalid_move(player_id=from_pid, reason=f"Offer made to invalid player ID {target_pid}")
                continue

                                                                  
            parts = re.split(r"->", offer_str)
            if len(parts) != 2:
                reason = f"Cannot parse Offer: '{offer_str}'. Must be like '2 Wheat -> 3 Wood'."
                self.state.set_invalid_move(player_id=from_pid, reason=reason)
                continue

            offered_str = parts[0].strip()
            requested_str = parts[1].strip()

                             
            offered_dict = self._parse_resource_list(offered_str)
            requested_dict = self._parse_resource_list(requested_str)
            if offered_dict is None or requested_dict is None:
                self.state.set_invalid_move(player_id=from_pid, reason=f"Invalid resource format in offer: '{offer_str}'")
                continue

                                                                                               
            if not self._check_sufficient_resources(from_pid, offered_dict, game_state["player_resources"]):
                reason = f"You do not hold enough resources to offer {offered_dict} to Player {target_pid}."
                self.state.set_invalid_move(player_id=from_pid, reason=reason)
                continue

                                   
            game_state["offer_id_counter"] += 1
            new_id = game_state["offer_id_counter"]
            game_state["pending_offers"][new_id] = {
                "from": from_pid,
                "to": target_pid,
                "offered_resources": offered_dict,
                "requested_resources": requested_dict
            }

                                                                         
            message = f"Offer #{new_id} created: Player {from_pid} -> Player {target_pid}."
            self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
                                                          
            message = (
                f"You have a new offer [ID #{new_id}] from Player {from_pid}: "
                f"{self._offer_to_str(offered_dict, requested_dict)}\n"
                f"You can [accept #{new_id}] or [deny #{new_id}] it."
            )
            self.state.add_observation(from_id=ta.GAME_ID, to_id=target_pid, message=message)

    def _process_accepts_and_denies(self, current_pid: int, action: str):
        pass                                             
                                                                
                                                                                 
                                                                                
                                                               
           
        accepts = self.accept_pattern.findall(action)               
        denies  = self.deny_pattern.findall(action)                 

        for offer_id_str in accepts:
            try:
                offer_id = int(offer_id_str)
            except ValueError:
                self.state.set_invalid_move(player_id=current_pid, reason=f"Invalid offer ID in Accept: {offer_id_str}")
                continue
            self._attempt_accept_offer(current_pid, offer_id)

        for offer_id_str in denies:
            try:
                offer_id = int(offer_id_str)
            except ValueError:
                self.state.set_invalid_move(player_id=current_pid, reason=f"Invalid offer ID in Deny: {offer_id_str}")
                continue
            self._deny_offer(current_pid, offer_id)


    def _attempt_accept_offer(self, current_pid: int, offer_id: int):
        pass                                                                               
                                                                                      
           
        game_state = self.state.game_state
        if offer_id not in game_state["pending_offers"]:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Offer #{offer_id} does not exist.")
            return
        off = game_state["pending_offers"][offer_id]
        if off["to"] != current_pid:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Offer #{offer_id} is not addressed to you.")
            return

                                                          
        if not self._check_sufficient_resources(off["from"], off["offered_resources"], game_state["player_resources"]):
                                                                                      
            self.state.add_observation(message=f"Offer #{offer_id} canceled because Player {off['from']} no longer has enough resources to fulfill it.")
            del game_state["pending_offers"][offer_id]
            return

                                                  
        if not self._check_sufficient_resources(
            off["to"], off["requested_resources"], game_state["player_resources"]
        ):
            reason=f"You do not have enough resources to fulfill Offer #{offer_id}."
            self.state.set_invalid_move(player_id=current_pid, reason=reason)
            return

                           
        self._exchange_resources(off["from"], off["to"],
                                 off["offered_resources"], off["requested_resources"])
                          
        message=(
            f"Player {off['to']} ACCEPTED Offer #{offer_id} from Player {off['from']}: "
            f"{self._offer_to_str(off['offered_resources'], off['requested_resources'])}"
        )
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
                                
        del game_state["pending_offers"][offer_id]

    def _deny_offer(self, current_pid: int, offer_id: int):
        pass                                                                       
        game_state = self.state.game_state
        if offer_id not in game_state["pending_offers"]:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Offer #{offer_id} does not exist.")
            return

        off = game_state["pending_offers"][offer_id]
        if off["to"] != current_pid:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Offer #{offer_id} is not addressed to you.")
            return

        message=f"Player {current_pid} DENIED Offer #{offer_id} from Player {off['from']}."
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
        del game_state["pending_offers"][offer_id]

    def _check_sufficient_resources(self, pid: int, needed: Dict[str, int],
                                    all_resources: Dict[int, Dict[str, int]]) -> bool:
        pass                                                                                
        for resource, qty in needed.items():
            if all_resources[pid].get(resource, 0) < qty:
                return False
        return True

    def _exchange_resources(self, from_pid: int, to_pid: int,
                            offered: Dict[str, int], requested: Dict[str, int]):
        pass                                                                      
                                                                   
           
                                                                                   
        res = self.state.game_state["player_resources"]
                                
        for r, q in offered.items():
            res[from_pid][r] -= q
            res[to_pid][r]   += q
                                
        for r, q in requested.items():
            res[to_pid][r]   -= q
            res[from_pid][r] += q

    def _parse_resource_list(self, resource_str: str) -> Optional[Dict[str, int]]:
        pass                                                                        
                                    
           
                                  
        items = re.split(r",\s*|\s+and\s+", resource_str, flags=re.IGNORECASE)
        parsed = {}
        for item in items:
            item = item.strip()
            if not item:
                continue
                                                  
            match = re.match(r"(\d+)\s+(.+)", item)
            if not match:
                return None
            qty_str, rname = match.groups()
            qty = int(qty_str)
                                                  
            rname = rname.strip().title()
            if rname not in self.resource_names:
                return None
            if qty <= 0:
                return None
            parsed[rname] = parsed.get(rname, 0) + qty
        return parsed if parsed else None

    def _offer_to_str(self, offered: Dict[str, int], requested: Dict[str, int]) -> str:
        pass                                                                     
           
        off_str = ", ".join(f"{q} {r}" for r, q in offered.items())
        req_str = ", ".join(f"{q} {r}" for r, q in requested.items())
        return f"{off_str} -> {req_str}"

    def _determine_winner(self):
        pass                                                                     
                                                                  
           
                                                                  
                                  
        game_state = self.state.game_state
        final_values = {}
        for pid in range(self.state.num_players):
            val = self._calculate_inventory_value(pid, game_state)
            final_values[pid] = val

        best_pid = max(final_values, key=final_values.get)
        best_val = final_values[best_pid]
                      
        winners = [p for p, v in final_values.items() if v == best_val]
        if len(winners) == 1:
            reason=f"Player {best_pid} wins with a total value of {best_val}!"
            self.state.set_winners(player_ids=[best_pid], reason=reason)
        else:
            self.state.set_draw(reason=f"Tie among players {winners} with value {best_val}.")

    def _calculate_inventory_value(self, pid: int, game_state: Dict[str, Any]) -> int:
        pass                                                                            
           
        total = 0
        resources = game_state["player_resources"][pid]
        values = game_state["player_values"][pid]
        for r in self.resource_names:
            total += resources[r] * values[r]
        return total
