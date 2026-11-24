import re, random
from typing import Any, Dict, List, Optional, Tuple

import textarena as ta
from textarena.envs.BlindAuction.renderer import create_board_str


class BlindAuctionEnv(ta.Env):
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

    whisper_pattern = re.compile(r"\s*\[Whisper\s+(?:to\s+)?(?:Player\s+)?(\d+)\s*:\s*(.*?)\]", re.IGNORECASE | re.DOTALL)
    bid_pattern = re.compile(r"\[Bid\s+(?:on\s+)?(?:Item\s+)?(\d+)\s*:\s*(\d+)\]", re.IGNORECASE)

    def __init__(
        self,
        starting_capital: int = 1000,
        num_items: int = 5,
        conversation_rounds: int = 3,
        base_item_values: Optional[List[int]] = None
    ):
        pass                                                   

             
                                                                     
                                                        
                                                                               
                                                                                                      
           
        self.starting_capital = starting_capital
        self.num_items = num_items
        self.conversation_rounds = conversation_rounds
        
                                                                      
        self.base_item_values = base_item_values
        
                               
        self.item_names = [
            "Ancient Vase", "Diamond Necklace", "Antique Clock", "Signed Painting", 
            "Gold Statue", "Rare Manuscript", "Silver Chalice", "Vintage Watch",
            "Jade Figurine", "Bronze Sculpture", "Crystal Decanter", "Royal Tapestry",
            "Emerald Ring", "Ivory Chess Set", "Pearl Earrings", "Platinum Coin Collection",
            "Ruby Brooch", "Sapphire Tiara", "Telescope", "Amber Fossil"
        ]

    def get_board_str(self):
        return create_board_str(game_state=self.state.game_state)

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                             
                                                   
        self.state = ta.State(
            num_players=num_players, 
            min_players=3, 
            max_players=15,
            max_turns=self.conversation_rounds * num_players + num_players,
            check_truncated=False,
            seed=seed
        )
        
                                                  
        if not self.base_item_values:
            self.base_item_values = [random.randint(50, 500) for _ in range(self.num_items)]
        
                                          
        while len(self.item_names) < self.num_items:
            self.item_names.append(f"Mystery Item {len(self.item_names)}")
        
                                                            
        item_names = random.sample(self.item_names, self.num_items)
        
                                                                        
        player_item_values = {}
        for pid in range(num_players):
            player_item_values[pid] = {}
            for i, base_value in enumerate(self.base_item_values):
                variation = int(0.2 * base_value)        
                min_value = max(1, base_value - variation)
                max_value = base_value + variation
                player_item_values[pid][i] = random.randint(min_value, max_value)
        
                               
        game_state = {
            "phase": "conversation",                                      
            "round": 1,                              
            "item_names": item_names[:self.num_items],
            "base_item_values": self.base_item_values[:self.num_items],
            "player_item_values": player_item_values,
            "remaining_capital": {pid: self.starting_capital for pid in range(num_players)},
            "player_bids": {pid: {} for pid in range(num_players)},                                              
            "auction_results": None,                                         
            "conversations_completed": 0                                      
        }
        
                         
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        pass                                           
                                                      
        item_values = []
        for i in range(self.num_items):
            item_name = game_state["item_names"][i]
            value = game_state["player_item_values"][player_id][i]
            item_values.append(f"- Item {i}: {item_name} - Value to you: {value} coins")
        
        items_str = "\n".join(item_values)
        
        prompt = (
            f"Welcome to the Blind Auction, Player {player_id}!\n\n"
            f"You have {self.starting_capital} coins to bid on {self.num_items} valuable items.\n\n"
            f"The auction has two phases:\n"
            f"1. Conversation Phase ({self.conversation_rounds} rounds): Talk with other players to gather information or make deals.\n"
            f"2. Bidding Phase (1 round): Submit blind bids on items. Highest bidder wins each item.\n\n"
            f"Available Items (with their value TO YOU):\n{items_str}\n\n"
            f"Note: Each player may value items differently, up to ±20% difference!\n\n"
            f"Available Commands:\n"
            f"- Conversation Phase:\n"
            f"  '[Broadcast: message]' - Send a message to all players\n"
            f"  '[Whisper to X: message]' - Send a private message to Player X\n\n"
            f"- Bidding Phase:\n"
            f"  '[Bid on Item X: amount]' - Bid the specified amount on Item X\n"
            f"  You can submit multiple bids for different items in a single turn.\n\n"
            f"The winner is the player with the highest net worth (total subjectvie item value + remaining coins)."
        )
        return prompt

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                            
        current_pid = self.state.current_player_id
        game_state = self.state.game_state
        
                                 
        self.state.add_observation(from_id=current_pid, to_id=current_pid, message=action)
        
                                              
        if game_state["phase"] == "conversation":
            self._handle_conversation_action(current_pid, action)
            
                                                            
            game_state["conversations_completed"] += 1
            if game_state["conversations_completed"] >= self.conversation_rounds * self.state.num_players:
                self._transition_to_bidding_phase()
                
        elif game_state["phase"] == "bidding":
            self._handle_bidding_action(current_pid, action)
            
                                           
            if self.state.turn >= self.conversation_rounds * self.state.num_players + self.state.num_players - 1:
                self._determine_auction_results()
                
                                 
        return self.state.step()

    def _handle_conversation_action(self, player_id: int, action: str) -> None:
        pass                                                              
                                    
        broadcasts = self._parse_broadcasts(action)
        for msg in broadcasts:
            broadcast_msg = f"(Broadcast) Player {player_id} says:{msg}"
            self.state.add_observation(from_id=player_id, to_id=-1, message=broadcast_msg)
        
                          
        whispers = self._parse_whispers(action)
        for target_pid_str, msg in whispers:
            try:
                target_pid = int(target_pid_str)
                if target_pid not in range(self.state.num_players):
                    self.state.set_invalid_move(
                        player_id=player_id, 
                        reason=f"Attempted to whisper to non-existent Player {target_pid}."
                    )
                    continue
                
                whisper_msg = f"(Private) Player {player_id} says:{msg}"
                self.state.add_observation(from_id=player_id, to_id=target_pid, message=whisper_msg)
            except ValueError:
                self.state.set_invalid_move(player_id=player_id, reason=f"Invalid player target: {target_pid_str}")

    def _handle_bidding_action(self, player_id: int, action: str) -> None:
        pass                                                           
        game_state = self.state.game_state
        bids = self.bid_pattern.findall(action)
        
                                       
        if not bids:
            message=f"Player {player_id} submitted no bids this turn."
            self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
            return
            
                          
        total_bid_amount = 0
        valid_bids = []
        
        for item_id_str, bid_amount_str in bids:
            try:
                item_id = int(item_id_str)
                bid_amount = int(bid_amount_str)
                
                                  
                if item_id not in range(self.num_items):
                    reason=f"Bid on non-existent Item {item_id}."
                    self.state.set_invalid_move(player_id=player_id, reason=reason)
                    continue
                
                                                 
                if bid_amount <= 0:
                    reason=f"Bid amount must be positive, got {bid_amount}."
                    self.state.set_invalid_move(
                        player_id=player_id, reason=reason)
                    continue
                
                                                                              
                total_bid_amount += bid_amount
                valid_bids.append((item_id, bid_amount))
                
            except ValueError:
                reason=f"Invalid bid format: [{item_id_str}:{bid_amount_str}]"
                self.state.set_invalid_move(player_id=player_id, reason=reason)
        
                                                     
        if total_bid_amount > game_state["remaining_capital"][player_id]:
            reason=f"Total bid amount {total_bid_amount} exceeds your remaining capital {game_state['remaining_capital'][player_id]}."
            self.state.set_invalid_move(player_id=player_id, reason=reason)
            return
            
                           
        for item_id, bid_amount in valid_bids:
            game_state["player_bids"][player_id][item_id] = bid_amount
            
                                               
        game_state["remaining_capital"][player_id] -= total_bid_amount
        
                                                                    
        bid_items = [item_id for item_id, _ in valid_bids]
        if bid_items:
            message=f"Player {player_id} submitted bids for Items: {', '.join(map(str, bid_items))}."
            self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=message)

    def _transition_to_bidding_phase(self) -> None:
        pass                                                      
        game_state = self.state.game_state
        game_state["phase"] = "bidding"
        
                                 
        message=f"Conversation phase complete! Now entering the bidding phase. Each player will have one turn to submit bids."
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message)
        
                                    
        bidding_reminder = (
            "Bidding Format: '[Bid on Item X: amount]' - Bid the specified amount on Item X\n"
            "You have to submit all of your bids in a single turn. Highest bidder wins each item."
        )
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=bidding_reminder)

    def _determine_auction_results(self) -> None:
        pass                                                                
        game_state = self.state.game_state
        num_players = self.state.num_players
        
                            
        auction_results = {
            "item_winners": {},                                       
            "winning_bids": {},                                               
            "player_wins": {},                                                
            "player_spent": {},                                               
            "player_value": {},                                                            
            "player_profit": {},                                                           
            "player_net_worth": {},                                                                
        }
        
                                         
        for item_id in range(self.num_items):
            highest_bid = 0
            winner_pid = None
            
            for pid in range(num_players):
                bid = game_state["player_bids"][pid].get(item_id, 0)
                if bid > highest_bid:
                    highest_bid = bid
                    winner_pid = pid
                elif bid == highest_bid:
                    winner_pid = None
            
                                             
            if winner_pid is not None and highest_bid > 0:
                auction_results["item_winners"][item_id] = winner_pid
                auction_results["winning_bids"][item_id] = highest_bid
                if winner_pid not in auction_results["player_wins"]:
                    auction_results["player_wins"][winner_pid] = [] 
                auction_results["player_wins"][winner_pid].append(item_id)
                if winner_pid not in auction_results["player_spent"]:
                    auction_results["player_spent"][winner_pid] = 0 
                auction_results["player_spent"][winner_pid] += highest_bid
                
                                               
                item_value = game_state["player_item_values"][winner_pid][item_id]

                if not winner_pid in auction_results["player_value"]:
                    auction_results["player_value"][winner_pid] = 0 
                auction_results["player_value"][winner_pid] += item_value
        
                                                        
        for pid in range(num_players):
            value = auction_results["player_value"].get(pid, 0)
            spent = auction_results["player_spent"].get(pid, 0)
            remaining = game_state["remaining_capital"].get(pid)
            
                                                    
            auction_results["player_profit"][pid] = value - spent
            
                                                            
            auction_results["player_net_worth"][pid] = remaining + value
        
                                    
        game_state["auction_results"] = auction_results
        
                          
        self._announce_auction_results()
        
                              
        self._determine_winner()

    def _announce_auction_results(self) -> None:
        pass                                                     
        game_state = self.state.game_state
        results = game_state["auction_results"]
        
                                          
        message = "==================== AUCTION RESULTS ====================\n\n"
        
                               
        message += "🏆 ITEM RESULTS:\n"
        for item_id in range(self.num_items):
            item_name = game_state["item_names"][item_id]
            if item_id in results["item_winners"]:
                winner_pid = results["item_winners"][item_id]
                winning_bid = results["winning_bids"][item_id]
                item_value = game_state["player_item_values"][winner_pid][item_id]
                profit = item_value - winning_bid
                message += f"- Item {item_id} ({item_name}): Won by Player {winner_pid} for {winning_bid} coins\n"
                message += f"  Value to Player {winner_pid}: {item_value} coins (Profit: {profit} coins)\n"
            else:
                message += f"- Item {item_id} ({item_name}): No valid bids\n"
        
        message += "\n💰 PLAYER RESULTS:\n"
        for pid in range(self.state.num_players):
                                         
            remaining = game_state["remaining_capital"][pid]
            initial = self.starting_capital
            spent = results["player_spent"].get(pid, 0)      
            value = results["player_value"].get(pid, 0)       
            profit = results["player_profit"].get(pid, 0)       
            net_worth = remaining + value                                                  
            
                                             
                                                                
            results["player_net_worth"][pid] = net_worth
            
            message += f"- Player {pid}:\n"
            
                                         
            items_won = results["player_wins"].get(pid, [])
            if items_won:
                message += f"  Items Won:\n"
                for item_id in items_won:
                    item_name = game_state["item_names"][item_id]
                    bid = results["winning_bids"][item_id]
                    value_to_player = game_state["player_item_values"][pid][item_id]
                    message += f"  - Item {item_id} ({item_name}): Paid {bid} coins, Value {value_to_player} coins\n"
            else:
                message += f"  Items Won: None\n"
            
                                    
            message += f"  Financial Summary:\n"
            message += f"  - Initial Capital: {initial} coins\n"
            message += f"  - Total Spent: {spent} coins\n"
            message += f"  - Remaining Capital: {remaining} coins\n"
            message += f"  - Total Item Value: {value} coins\n"
            message += f"  - Profit: {profit} coins\n"
            message += f"  - Net Worth: {net_worth} coins\n\n"
        
                          
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message
        )

    def _determine_winner(self) -> None:
        pass                                                         
        game_state = self.state.game_state
        results = game_state["auction_results"]
        
                                                       
        max_worth = max(results["player_net_worth"].values(), default=0)
        winners = []
        for pid, worth in results["player_net_worth"].items():
            if worth == max_worth:
                winners.append(pid)

                           
        if len(winners) == 1:
            winner = winners[0]
            profit = results["player_profit"][winner]
            spent = results["player_spent"][winner]
            remaining = game_state["remaining_capital"][winner]
            item_value = results["player_value"][winner]
            
            reason = (
                f"Player {winner} won with a final net worth of {max_worth} coins! "
                f"(Remaining capital: {remaining} coins, Item value: {item_value} coins, "
                f"Profit: {profit} coins)"
            )
            self.state.set_winners(player_ids=[winner], reason=reason)
        else:
                                                             
            details = []
            for pid in winners:
                profit = results["player_profit"][pid]
                remaining = game_state["remaining_capital"][pid]
                details.append(
                    f"Player {pid} (Net worth: {max_worth} coins, "
                    f"Remaining capital: {remaining} coins, "
                    f"Profit: {profit} coins)"
                )
            
            reason = f"Multiple players tied with a net worth of {max_worth} coins:\n" + "\n".join(details)
            self.state.set_draw(reason=reason)

    def _parse_broadcasts(self, text: str) -> List[str]:
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

    def _parse_whispers(self, text: str) -> List[Tuple[str, str]]:
        pass                                         
        results = []
        matches = self.whisper_pattern.findall(text)
        for pid_str, msg in matches:
            if msg and not msg.startswith(" "):
                msg = " " + msg
            results.append((pid_str, msg))
        return results