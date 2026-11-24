from typing import Dict, Optional, List, Tuple, Any
import random
import textarena as ta
import re

class SpiteAndMaliceEnv(ta.Env):
    pass                                     
       
    def __init__(self):
        pass                                               
                                         
        self.deck = [f"{rank}{suit}" for rank in "A23456789JQK" for suit in "♠♥♦♣"] * 2
        
    @property
    def terminal_render_keys(self):
        return ["rendered_board","player_turn"]

    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        pass                                             
                                   
        self.state = ta.TwoPlayerState(num_players=2, seed=seed, max_turns=None)
        
                                                                                      
        random.shuffle(self.deck)
        self.players = self._initialize_players()
        self.center_piles = [[] for _ in range(4)]
        
                                     
        self._draw_cards(0)
        self._draw_cards(1)

                                          
        game_state={
            "players": self.players, "center_piles": self.center_piles,
            "player_turn": self.state.current_player_id, "rendered_board": self._render_board()
        }
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self._observe_current_state(player_id=self.state.current_player_id)
    
    def _initialize_players(self):
        pass                                                                  
        players = {0: {"payoff": [], "hand": [], "discard": [[] for _ in range(4)]},
                   1: {"payoff": [], "hand": [], "discard": [[] for _ in range(4)]}}
        
                                                                   
        for player in players:
            players[player]["payoff"] = [self.deck.pop() for _ in range(20)]
        
        return players
    
    def _draw_cards(self, player_id: int):
        pass                                           
        while len(self.players[player_id]["hand"]) < 5 and self.deck:
            self.players[player_id]["hand"].append(self.deck.pop())
        
        if not self.deck and len(self.players[player_id]["hand"]) < 5:
            message=self.m("game_message", "no_cards_left")
            self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        pass                                   

             
                                              

                
                               
           
        prompt = self.m("player_prompt", "intro", player_id=player_id)

        return prompt

    def _observe_current_state(self, player_id: int):
        pass                                                               
        available_moves = ["[draw]"]

                                
        for i, pile in enumerate(self.center_piles):
                              
            if self.players[player_id]["payoff"]:
                top_payoff_card = self.players[player_id]["payoff"][-1]
                if self._can_play_on_center(top_payoff_card, pile):
                    available_moves.append(f"[play {top_payoff_card} {i}]")
                       
            for card in self.players[player_id]["hand"]:
                if self._can_play_on_center(card, pile):
                    available_moves.append(f"[play {card} {i}]")
                          
            for discard_pile in self.players[player_id]["discard"]:
                if discard_pile:
                    top_discard_card = discard_pile[-1]
                    if self._can_play_on_center(top_discard_card, pile):
                        available_moves.append(f"[play {top_discard_card} {i}]")

                                                                                      
        for i, discard_pile in enumerate(self.players[player_id]["discard"]):
            for card in self.players[player_id]["hand"]:
                available_moves.append(f"[discard {card} {i}]")

                            
        self.state.add_observation(to_id=player_id, message=self.m("board", "current_board", board=self._render_board(player_id=player_id), moves=", ".join(available_moves)), observation_type=ta.ObservationType.GAME_BOARD)

    
    def _play_card(self, player_id: int, card: str, center_index: int):
        pass                                                                        
                                                                      
        if self._can_play_on_center(card, self.center_piles[center_index]):
                                                                        
            if self.players[player_id]["payoff"] and card == self.players[player_id]["payoff"][-1]:
                self.players[player_id]["payoff"].pop()
                                                       
            elif card in self.players[player_id]["hand"]:
                self.players[player_id]["hand"].remove(card)
                                                                   
            else:
                found_in_discard = False
                for discard_pile in self.players[player_id]["discard"]:
                    if discard_pile and discard_pile[-1] == card:
                        discard_pile.pop()
                        found_in_discard = True
                        break
                if not found_in_discard:
                    return False                                              

                                             
            self.center_piles[center_index].append(card)
                                                                           
            if len(self.center_piles[center_index]) == 11:
                self.center_piles[center_index] = []
            return True
                                                       
        return False

    def _can_play_on_center(self, card: str, pile: List[str]):
        pass                                                           
                                                                                      
           
                                                                
        if card[0] == "K":
            return True
                                                                
        if not pile:
            return card[0] == "A" or card[0] == "K"
                                                                                      
        if pile[-1][0] == "K":
                                                                                              
            top_card_rank = len(pile) -1 if len(pile) >= 1 else 0                                      
        else:
                                                            
            top_card_rank = self._card_rank(pile[-1][0])
                                                                                             
        return self._card_rank(card[0]) == top_card_rank + 1
    
    def _card_rank(self, card: str):
        pass                                                          
        ranks = "A23456789JQK"
        return ranks.index(card[0])
    
    def _discard_card(self, player_id: int, card: str, discard_index: int):
        pass                                                       
        self.players[player_id]["hand"].remove(card)
        self.players[player_id]["discard"][discard_index].append(card)

    def _check_win(self, player_id: int):
        pass
                                                                         
                                                                               
           
                                                    
        if len(self.players[player_id]["payoff"]) == 0:
            return True
        
                                      
        if self._is_deadlock():
                                                                   
            player_0_payoff = len(self.players[0]["payoff"])
            player_1_payoff = len(self.players[1]["payoff"])
            
            if player_0_payoff < player_1_payoff:
                return player_id == 0
            elif player_1_payoff < player_0_payoff:
                return player_id == 1
            else:
                                                                                
                                                                                    
                return True
        
        return False

    def _is_deadlock(self):
        pass                                                                                      
                          
                                                   
                                                                                          
                                                                                    
           
                                                              
        if self.deck:
            return False
        
                                                                        
        for player_id in [0, 1]:
            player = self.players[player_id]
            
                                                                                  
            if player["hand"]:
                return False
            
                                                                                   
            if self._player_has_valid_moves(player_id):
                return False
        
        return True

    def _player_has_valid_moves(self, player_id: int):
        pass                                                                              
           
        player = self.players[player_id]
        
                                                        
        if player["payoff"]:
            top_payoff_card = player["payoff"][-1]
            for pile in self.center_piles:
                if self._can_play_on_center(top_payoff_card, pile):
                    return True
        
                                                                 
        for discard_pile in player["discard"]:
            if discard_pile:
                top_discard_card = discard_pile[-1]
                for pile in self.center_piles:
                    if self._can_play_on_center(top_discard_card, pile):
                        return True
        
        return False

    def _handle_game_end_check(self):
        pass                                                                    
                                                               
           
        current_player = self.state.current_player_id
        
                                     
        if self._check_win(current_player):
            if len(self.players[current_player]["payoff"]) == 0:
                reason = self.m("outcome", "payoff_cleared", current_player=current_player)
                self.state.set_winner(player_id=current_player, reason=reason)
            else:
                                    
                player_0_payoff = len(self.players[0]["payoff"])
                player_1_payoff = len(self.players[1]["payoff"])
                
                if player_0_payoff < player_1_payoff:
                    winner = 0
                    reason = self.m("outcome", "deadlock_player_0", player_0_payoff=player_0_payoff, player_1_payoff=player_1_payoff)
                elif player_1_payoff < player_0_payoff:
                    winner = 1
                    reason = self.m("outcome", "deadlock_player_1", player_1_payoff=player_1_payoff, player_0_payoff=player_0_payoff)
                else:
                    winner = current_player
                    reason = self.m("outcome", "deadlock_tie", player_0_payoff=player_0_payoff, current_player=current_player)
                
                self.state.set_winner(player_id=winner, reason=reason)
            return True
        
        return False
        
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                    
        
             
                                                         
            
                
                       
                                                             
           

        player_id = self.state.current_player_id

                                 
        self.state.add_observation(from_id=player_id, to_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

                                
        action_search_pattern = re.compile(r"\[(play|discard|draw)(?: ([A23456789JQK][♠♥♦♣]) ([0-3]))?\]")                                           
        matches = action_search_pattern.findall(action)
                                                                

        rotate_player  = False

        if not matches:
            reason=self.m("invalid_move", "wrong_format", player_id=player_id)
            self.state.set_invalid_move(reason=reason)
            rotate_player  = True
        else:
                                                                  
            for match in matches:
                action_type, card, index = match
                if action_type == "draw":
                    self._draw_cards(player_id)
                    message=self.m("game_action", "you_drew")
                    self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    message=self.m("game_action", "opponent_drew", player_id=player_id)
                    self.state.add_observation(from_id=ta.GAME_ID, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                elif action_type == "play":
                                                                                              
                    if self._play_card(player_id, card, int(index)):
                        message=self.m("game_action", "you_played", card=card, index=index)
                        self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                        message=self.m("game_action", "opponent_played", player_id=player_id, card=card, index=index)
                        self.state.add_observation(from_id=ta.GAME_ID, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    else:
                        reason=self.m("invalid_move", "invalid_play", player_id=player_id, card=card, index=index)
                        self.state.set_invalid_move(reason=reason)
                        break
                elif action_type == "discard":
                                                                                    
                    if card == self.players[player_id]["payoff"][-1] and card not in self.players[player_id]["hand"]:
                        reason=self.m("invalid_move", "discard_from_payoff", player_id=player_id)
                        self.state.set_invalid_move(reason=reason)
                        break
                    elif card not in self.players[player_id]["hand"]:
                        reason=self.m("invalid_move", "discard_not_in_hand", player_id=player_id)
                        self.state.set_invalid_move(reason=reason)
                        break
                    else:
                        self._discard_card(player_id, card, int(index))
                        message=self.m("game_action", "you_discarded", card=card, index=index, next_player_id=1 - player_id)
                        self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                        message=self.m("game_action", "opponent_discarded", player_id=player_id, card=card, index=index, next_player_id=1 - player_id)                                            
                        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                        rotate_player  = True
                        self.state.game_state["player_turn"] = 1 - player_id
                        break
                else:
                    reason=self.m("invalid_move", "wrong_move_type", player_id=player_id)
                    self.state.set_invalid_move(reason=reason)
                    break
        
                                               
        self.state.game_state["rendered_board"] = self._render_board()

                                                                 
        if self._handle_game_end_check():
            pass                                                

        self._observe_current_state(player_id=1 - player_id if rotate_player else player_id)                                                         
        return self.state.step(rotate_player)        
    
    def _render_board(self, player_id: Optional[int] = None) -> str:
        pass                         
        board = self.m("render", "center_piles_header")
        for i, pile in enumerate(self.center_piles):
            board = self.m("render", "pile", observation=board, i=i, pile=pile)
        
        if player_id is not None:
            board = self.m("render", "player_view_header", observation=board, player_id=player_id)
            board = self.m("render", "payoff", observation=board, top_card=self.players[player_id]['payoff'][-1] if self.players[player_id]['payoff'] else self.m("render", "empty"), payoff_length=len(self.players[player_id]['payoff']))
            board = self.m("render", "hand", observation=board, hand=self.players[player_id]['hand'])
            board = self.m("render", "discard", observation=board, discard=self.players[player_id]['discard'])

        else: 
            for player in self.players:
                board = self.m("render", "player_view_header", observation=board, player_id=player)
                board = self.m("render", "payoff", observation=board, top_card=self.players[player]['payoff'][-1] if self.players[player]['payoff'] else self.m("render", "empty"), payoff_length=len(self.players[player]['payoff']))
                board = self.m("render", "hand", observation=board, hand=self.players[player]['hand'])
                board = self.m("render", "discard", observation=board, discard=self.players[player]['discard'])
        return board