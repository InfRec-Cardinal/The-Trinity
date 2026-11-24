import re, random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import textarena as ta
from textarena.envs.SimpleBlindAuction.renderer import create_board_str


class SimpleBlindAuctionEnv(ta.Env):
    def __init__(self, starting_capital: int = 1000, num_items: int = 5, conversation_rounds: int = 3, base_item_values: Optional[List[int]] = None):
        pass             
                                                                     
                                                        
                                                                               
                                                                                                      
           
        self.starting_capital = starting_capital
        self.num_items = num_items
        self.conversation_rounds = conversation_rounds
        self.base_item_values = base_item_values                                                               
        self.item_names = [                        
            "Ancient Vase", "Diamond Necklace", "Antique Clock", "Signed Painting", "Gold Statue", "Rare Manuscript", "Silver Chalice", "Vintage Watch",
            "Jade Figurine", "Bronze Sculpture", "Crystal Decanter", "Royal Tapestry", "Emerald Ring", "Ivory Chess Set", "Pearl Earrings"
        ]

    def get_board_str(self): return create_board_str(game_state=self.state.game_state)
    def reset(self, num_players: int, seed: Optional[int] = None):
        self.state = ta.TwoPlayerState(num_players=num_players, max_turns=self.conversation_rounds * 2 + 2, seed=seed)
        while len(self.item_names) < self.num_items: self.item_names.append(f"Mystery Item {len(self.item_names)}")                                    
        item_names = random.sample(self.item_names, self.num_items)                                           
        
                                                   
        if not self.base_item_values: base_item_values = [random.randint(50, 500) for _ in range(self.num_items)]
        else: 
            base_item_values = self.base_item_values[:self.num_items]                                                 
            while len(base_item_values) < self.num_items: base_item_values.append(random.randint(50, 500))                              
        
                                                                        
        player_item_values = {}
        for pid in range(2):
            player_item_values[pid] = {}
            for i in range(self.num_items):
                base_value = base_item_values[i]
                variation = int(0.2 * base_value)        
                min_value = max(1, base_value - variation)
                max_value = base_value + variation
                player_item_values[pid][i] = random.randint(min_value, max_value)
        
                               
        game_state = {
            "phase": "conversation",                                     
            "round": 1,                              
            "item_names": item_names[:self.num_items],
            "base_item_values": base_item_values,
            "player_item_values": player_item_values,
            "remaining_capital": {0: self.starting_capital, 1: self.starting_capital},
            "player_bids": {0: {}, 1: {}},                                              
            "auction_results": None,                                         
            "conversations_completed": 0,                                      
            "bidding_done": {0: False, 1: False}
        }
        self.state.reset(game_state=game_state, player_prompt_function=self._prompt)                  


    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
                                                      
        item_values = []
        for i in range(self.num_items):
            item_name = game_state["item_names"][i]
            value = game_state["player_item_values"][player_id][i]
            item_values.append(f"- Item {i}: {item_name} - Value to you: {value} coins")
        items_str = "\n".join(item_values)
        return (
            f"You are Player {player_id} in a 2-player Simple Blind Auction game.\n\n"
            f"You have {self.starting_capital} coins to bid on {self.num_items} valuable items.\n\n"
            f"The auction has two phases:\n"
            f"1. Conversation Phase ({self.conversation_rounds} rounds): Talk with the other player. All messages are public.\n"
            f"2. Bidding Phase (1 round): Submit blind bids on items. Highest bidder wins each item.\n\n"
            f"Available Items (with their value TO YOU):\n{items_str}\n\n"
            f"Note: Each player may value items differently, up to ±20% difference!\n\n"
            f"How to play:\n"
            f"- Conversation Phase: Just type your messages normally\n"
            f"- Bidding Phase: Use '[Bid on Item X: amount]' format to bid\n"
            f"  Example: '[Bid on Item 0: 250] [Bid on Item 3: 175]'\n\n"
            f"Your goal is to win items that are worth more to you than what you paid.\n"
            f"The player with the highest net worth at the end wins.\n"
            f"Net worth = remaining capital + value of won items.\n"
        )

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        current_pid = self.state.current_player_id
        if self.state.game_state["phase"] == "conversation":
            self.state.add_observation(from_id=current_pid, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
            self.state.game_state["conversations_completed"] += 1
            if self.state.game_state["conversations_completed"] >= self.conversation_rounds * 2: self._transition_to_bidding_phase()
        elif self.state.game_state["phase"] == "bidding":
            self._handle_bidding_action(current_pid, action)
                                                                           
                                                        
            self.state.game_state["bidding_done"][current_pid] = True
                                                               
            if all(self.state.game_state["bidding_done"].values()): self._determine_auction_results()
        return self.state.step()

    def _transition_to_bidding_phase(self) -> None:
        pass                                                      
        self.state.game_state["phase"] = "bidding"
                                 
        message=(
                "Conversation phase complete! Now entering the bidding phase.\nPlease submit your bids using the format: [Bid on Item X: amount]\n"
                "You can submit multiple bids in one turn, for example:\n'[Bid on Item 0: 150] [Bid on Item 2: 200] [Bid on Item 4: 350]'"
            )
        self.state.add_observation(message=message, observation_type=ta.ObservationType.GAME_MESSAGE)

    def _handle_bidding_action(self, player_id: int, action: str) -> None:
        self.state.add_observation(from_id=player_id, to_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        bids = re.compile(r"\[Bid\s+(?:on\s+)?(?:Item\s+)?(\d+)\s*:\s*(\d+)\]", re.IGNORECASE).findall(action)

        if not bids: self.state.add_observation(to_id=player_id, message="You submitted no valid bids.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION); return                                                                                 
                          
        total_bid_amount = 0
        valid_bids = []
        
        for item_id_str, bid_amount_str in bids:
            try:
                item_id = int(item_id_str); bid_amount = int(bid_amount_str)
                if item_id not in range(self.num_items): self.state.set_invalid_move(reason=f"Item {item_id} does not exist. Valid items are 0-{self.num_items-1}."); continue                   
                if bid_amount <= 0: self.state.set_invalid_move(reason="Bid amount must be positive."); continue                                  
                
                                                                              
                total_bid_amount += bid_amount
                valid_bids.append((item_id, bid_amount))
            except ValueError: self.state.set_invalid_move(reason=f"Invalid bid format. Use '[Bid on Item X: amount]'.")
        
                                                     
        if total_bid_amount > self.state.game_state["remaining_capital"][player_id]: self.state.set_invalid_move(reason=f"Total bid amount {total_bid_amount} exceeds your remaining capital {self.state.game_state['remaining_capital'][player_id]}."); return
        for item_id, bid_amount in valid_bids: self.state.game_state["player_bids"][player_id][item_id] = bid_amount                    
        self.state.game_state["remaining_capital"][player_id] -= total_bid_amount                                        
        
                                                
        bid_items = [item_id for item_id, _ in valid_bids]
        if bid_items:
            self.state.add_observation(to_id=player_id, message=f"You submitted bids for Items: {', '.join(map(str, bid_items))}.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
            self.state.add_observation(to_id=1-player_id, message=f"Player {player_id} has submitted bids.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)                                                 

    def _determine_auction_results(self) -> None:
        pass                                                                
        game_state = self.state.game_state
        
                            
        auction_results = {
            "item_winners": {},                                  
            "winning_bids": {},                                          
            "player_wins": defaultdict(list),                           
            "player_spent": defaultdict(int),                            
            "player_value": defaultdict(int),                                         
            "player_profit": defaultdict(int),                                          
            "player_net_worth": defaultdict(int)                                               
        }
        
                                         
        for item_id in range(self.num_items):
            player0_bid = game_state["player_bids"][0].get(item_id, 0)
            player1_bid = game_state["player_bids"][1].get(item_id, 0)
            
                                                      
            if player0_bid > player1_bid:   winner_pid = 0; highest_bid = player0_bid
            elif player1_bid > player0_bid: winner_pid = 1; highest_bid = player1_bid
            else: continue                             
            
                                             
            auction_results["item_winners"][item_id] = winner_pid
            auction_results["winning_bids"][item_id] = highest_bid
            auction_results["player_wins"][winner_pid].append(item_id)
            auction_results["player_spent"][winner_pid] += highest_bid
                
                                           
            item_value = game_state["player_item_values"][winner_pid][item_id]
            auction_results["player_value"][winner_pid] += item_value
        
                                                        
        for pid in range(2):
            value = auction_results["player_value"][pid]
            spent = auction_results["player_spent"][pid]
            remaining = game_state["remaining_capital"][pid]
            auction_results["player_profit"][pid] = value - spent                                         
            auction_results["player_net_worth"][pid] = remaining + value                                                 
        game_state["auction_results"] = auction_results                             
        self._announce_auction_results()                   
        self._determine_winner()                       

    def _announce_auction_results(self) -> None:
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
                message += f"- Item {item_id} ({item_name}): No winner (tie or no bids)\n"
        message += "\n💰 PLAYER RESULTS:\n"
        for pid in range(2):
                                         
            remaining = game_state["remaining_capital"][pid]
            initial = self.starting_capital
            spent = results["player_spent"][pid]
            value = results["player_value"][pid]
            profit = results["player_profit"][pid]
            net_worth = remaining + value                                                  
            message += f"- Player {pid}:\n"
                                         
            items_won = results["player_wins"][pid]
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
        
                          
        self.state.add_observation(message=message, observation_type=ta.ObservationType.GAME_MESSAGE)

    def _determine_winner(self) -> None:
        game_state = self.state.game_state
        results = game_state["auction_results"]
        
                                                       
        max_worth = max(results["player_net_worth"].values(), default=0)
        winners = [pid for pid, worth in results["player_net_worth"].items() if worth == max_worth]
        
                           
        if len(winners) == 1:
            winner = winners[0]
            profit = results["player_profit"][winner]
            spent = results["player_spent"][winner]
            remaining = game_state["remaining_capital"][winner]
            item_value = results["player_value"][winner]
            reason = f"Player {winner} won with a final net worth of {max_worth} coins! (Remaining capital: {remaining} coins, Item value: {item_value} coins, Profit: {profit} coins)"
            self.state.set_winner(player_id=winner, reason=reason)
        else:
                                                             
            details = []
            for pid in winners:
                profit = results["player_profit"][pid]
                remaining = game_state["remaining_capital"][pid]
                details.append(f"Player {pid} (Net worth: {max_worth} coins, Remaining capital: {remaining} coins, Profit: {profit} coins)")
            self.state.set_draw(reason=f"Both players tied with a net worth of {max_worth} coins.\n" + "\n".join(details))