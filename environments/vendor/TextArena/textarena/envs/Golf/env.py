import random
import re
from typing import Optional, Tuple, List, Dict, Any

import textarena as ta

class GolfEnv(ta.Env):
    def __init__(self, num_cards: int = 6, num_columns: int = 3):
        pass                                              
        super().__init__()
        self.num_cards = num_cards
        self.num_columns = num_columns
        self.num_rows = num_cards // num_columns
        self.deck = self._create_deck()
        
    def _create_deck(self) -> List[Dict[str, Any]]:
        pass                                   
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        deck = []

        if self.num_cards <= 6:
            num_decks = 1
        elif self.num_cards <= 9:
            num_decks = 2
        elif self.num_cards <= 12:
            num_decks = 3
        
        for _ in range(num_decks):
            for suit in suits:
                for rank in ranks:
                    card = {
                        'rank': rank,
                        'suit': suit,
                        'value': self._get_card_value(rank)
                    }
                    deck.append(card)
        return deck
    
    def _get_card_value(self, rank: str) -> int:
        pass                                             
        if rank == 'A':
            return 1
        elif rank in ['J', 'Q']:
            return 10
        elif rank == 'K':
            return 0                                                
        else:
            return int(rank)
    
    def _card_to_string(self, card: Dict[str, Any]) -> str:
        pass                                        
        return f"{card['rank']}{card['suit']}"
    
    def _find_action_token(self, message: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        pass                                                         
        patterns = [
            ("draw", re.compile(r"\[draw\]", re.I)),
            ("take", re.compile(r"\[take\]", re.I)),
            ("swap", re.compile(r"\[swap (\d+) (\d+)\]", re.I)),
            ("discard", re.compile(r"\[discard\]", re.I)),
            ("knock", re.compile(r"\[knock\]", re.I)),
            ("peek", re.compile(r"\[peek (\d+) (\d+)\]", re.I))
        ]
        
        found = [(name, m) for name, rx in patterns if (m := rx.search(message))]
        if len(found) != 1:
            return None, None                     
            
        action_name, match = found[0]
        params = {}
        
        if action_name in ("swap", "peek"):
            params['row'] = int(match.group(1))
            params['col'] = int(match.group(2))
        
        return action_name, params
    
    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        pass                        
        if num_players < 2 or num_players > 4:
            raise ValueError("Golf supports 2-4 players")
            
        if num_players == 2:
            self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        else:
            self.state = ta.FFAMultiPlayerState(num_players=num_players, seed=seed)
        
                                                            
        game_state = self._init_game_state(num_players)
        
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        
                                                
        self._announce_turn_options(self.state.current_player_id)
    
    def _init_game_state(self, num_players: int) -> Dict[str, Any]:
        pass                                                 
                                   
        deck_copy = self.deck.copy()
        random.shuffle(deck_copy)
        
                                                                 
        cards_to_reveal = self.num_cards // 3
        
                               
        players = {}
        for player_id in range(num_players):
            player_cards = []
            
                                                                 
            positions_to_reveal = random.sample(range(self.num_cards), cards_to_reveal)
            
            for i in range(self.num_cards):
                start_revealed = i in positions_to_reveal
                player_cards.append({
                    'card': deck_copy.pop(),
                    'revealed': start_revealed
                })
            
            players[player_id] = {
                'cards': player_cards,
                'score': 0
            }
        
                            
        discard_pile = [deck_copy.pop()]
        
                                    
        return {
            'players': players,
            'deck': deck_copy,
            'discard_pile': discard_pile,
            'current_phase': 'playing',                                  
            'knocker': None,
            'rounds_after_knock': 0,
            'turn_phase': 'draw'                          
        }
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        return self.m("player_prompt", "intro", player_id=player_id)
                                                                       
                                                                               

    def _render_player_hand(self, player_id: int) -> str:
        pass                                              
        if player_id not in self.state.game_state['players']: return self.m("hand", "no_cards").render(_pid=player_id)

        player = self.state.game_state['players'][player_id]
        cards = player['cards']

        output = [self.m("hand", "header").render(_pid=player_id)]

        for row in range(self.num_rows):
            row_cards = ""
            for col in range(self.num_columns):
                card_idx = row * self.num_columns + col
                if card_idx < len(cards):
                    card_info = cards[card_idx]

                    if card_info['revealed']:
                        card_str = f"{self._card_to_string(card_info['card']):>4}"
                    else:
                        card_str = "  ? "

                    row_cards += f"{card_str} "
                else:
                    row_cards += "     "                          
            output.append(self.m("hand", "row", n=row + 1, cards=row_cards).render(_pid=player_id))

        return "\n".join(output)
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        player_id = self.state.current_player_id
        
        self.state.add_observation(from_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        
                      
        action_name, params = self._find_action_token(action)
        
        if action_name is None:
            self.state.set_invalid_move(self.m("invalid", "wrong_action"))
            return self.state.step()
        
                                                              
        if self.state.game_state['turn_phase'] == 'draw':
            return self._handle_draw_phase(player_id, action_name, params)
        elif self.state.game_state['turn_phase'] == 'action_with_card':
            return self._handle_action_phase(player_id, action_name, params)
    
    def _handle_draw_phase(self, player_id: int, action_name: str, params: Dict) -> Tuple[bool, ta.Info]:
        pass                                                           
        if action_name == 'draw':
            if not self.state.game_state['deck']:
                                                            
                self.state.add_observation(message=self.m("message", "deck_empty"), observation_type=ta.ObservationType.GAME_MESSAGE)
                self._end_game()
                return self.state.step(rotate_player=False)
            
            drawn_card = self.state.game_state['deck'].pop()
            self.state.game_state['drawn_card'] = drawn_card
            self.state.game_state['turn_phase'] = 'action_with_card'
            
            self.state.add_observation(to_id=player_id, message=self.m("board", "drew", card=self._card_to_string(drawn_card)), observation_type=ta.ObservationType.GAME_MESSAGE)
            
                                                                                     
            self._announce_turn_options(player_id)
            
            return self.state.step(rotate_player=False)
            
        elif action_name == 'take':
            if not self.state.game_state['discard_pile']: 
                self.state.set_invalid_move(self.m("invalid", "discard_empty"))
                return self.state.step()
            
            drawn_card = self.state.game_state['discard_pile'].pop()
            self.state.game_state['drawn_card'] = drawn_card
            self.state.game_state['turn_phase'] = 'action_with_card'
            self.state.game_state['took_from_discard'] = True                 
            
            self.state.add_observation(to_id=player_id, message=self.m("board", "took", card=self._card_to_string(drawn_card)), observation_type=ta.ObservationType.GAME_MESSAGE)
            
                                                                                     
            self._announce_turn_options(player_id)
            
            return self.state.step(rotate_player=False)
            
        else:
            self.state.set_invalid_move(self.m("invalid", "must_draw_first"))
            return self.state.step()
    
    def _handle_action_phase(self, player_id: int, action_name: str, params: Dict) -> Tuple[bool, ta.Info]:
        pass                                                       
        if action_name == 'swap':
            return self._handle_swap(player_id, params)
        elif action_name == 'discard':
                                                                             
            if self.state.game_state.get('took_from_discard', False):
                self.state.set_invalid_move(self.m("invalid", "cannot_discard_taken"))
                return self.state.step()
            return self._handle_discard_drawn(player_id)
        else:
            self.state.set_invalid_move(self.m("invalid", "have_drawn_card"))
            return self.state.step()
    
    def _handle_swap(self, player_id: int, params: Dict) -> Tuple[bool, ta.Info]:
        pass                                                      
        if 'drawn_card' not in self.state.game_state:
            self.state.set_invalid_move(self.m("invalid", "need_drawn_swap"))
            return self.state.step()

        row, col = params['row'], params['col']

        if row < 1 or row > self.num_rows or col < 1 or col > self.num_columns:
            self.state.set_invalid_move(self.m("invalid", "out_of_bounds", max_row=self.num_rows, max_col=self.num_columns))
            return self.state.step()
        
                                     
        card_idx = (row - 1) * self.num_columns + (col - 1)
        player = self.state.game_state['players'][player_id]
        
                          
        old_card = player['cards'][card_idx]['card']
        player['cards'][card_idx]['card'] = self.state.game_state['drawn_card']
        player['cards'][card_idx]['revealed'] = True
        
                                      
        self.state.game_state['discard_pile'].append(old_card)
        self.state.add_observation(message=self.m("action_desc", "swapped", pid=player_id, new=self._card_to_string(self.state.game_state['drawn_card']), old=self._card_to_string(old_card), row=row, col=col), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        
                                          
        del self.state.game_state['drawn_card']
        self.state.game_state['took_from_discard'] = False
        
                                                                              
        if self._player_has_all_cards_revealed(player_id): return self._trigger_final_round(player_id, self.m("reason", "all_revealed"))
        
        return self._next_turn()
    
    def _handle_discard_drawn(self, player_id: int) -> Tuple[bool, ta.Info]:
        pass                                    
        if 'drawn_card' not in self.state.game_state:
            self.state.set_invalid_move(self.m("invalid", "need_drawn_discard"))
            return self.state.step()

        discarded_card = self.state.game_state['drawn_card']
        self.state.game_state['discard_pile'].append(discarded_card)

        self.state.add_observation(message=self.m("action_desc", "discarded", pid=player_id, card=self._card_to_string(discarded_card)), observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        
                                          
        del self.state.game_state['drawn_card']
        self.state.game_state['took_from_discard'] = False
        
                                                                              
        if self._player_has_all_cards_revealed(player_id): return self._trigger_final_round(player_id, self.m("reason", "all_revealed"))
        
        return self._next_turn()
    
    def _handle_knock(self, player_id: int) -> Tuple[bool, ta.Info]:
        pass                                             
        if 'drawn_card' in self.state.game_state: self.state.set_invalid_move(self.m("invalid", "knock_with_card")); return self.state.step()
        if self.state.game_state['knocker'] is not None: self.state.set_invalid_move(self.m("invalid", "already_knocked")); return self.state.step()
        self.state.game_state['knocker'] = player_id
        self.state.game_state['current_phase'] = 'final_round'
        self.state.add_observation(message=self.m("message", "knocked", pid=player_id), observation_type=ta.ObservationType.GAME_MESSAGE)
        return self._next_turn()
    
    def _handle_peek(self, player_id: int, params: Dict) -> Tuple[bool, ta.Info]:
        pass                                              
        row, col = params['row'], params['col']
        
        if row < 1 or row > self.num_rows or col < 1 or col > self.num_columns: self.state.set_invalid_move(self.m("invalid", "out_of_bounds", max_row=self.num_rows, max_col=self.num_columns)); return self.state.step()

        card_idx = (row - 1) * self.num_columns + (col - 1)
        player = self.state.game_state['players'][player_id]

        if player['cards'][card_idx]['revealed']: self.state.set_invalid_move(self.m("invalid", "already_revealed")); return self.state.step()

                                     
        peeked_card = player['cards'][card_idx]['card']
        self.state.add_observation(to_id=player_id, message=self.m("board", "peeked", row=row, col=col, card=self._card_to_string(peeked_card)), observation_type=ta.ObservationType.GAME_MESSAGE)
        return self._next_turn()
    
    def _player_has_all_cards_revealed(self, player_id: int) -> bool:
        pass                                                  
        if player_id not in self.state.game_state['players']: return False
        player = self.state.game_state['players'][player_id]
        return all(card_info['revealed'] for card_info in player['cards'])
    
    def _trigger_final_round(self, triggering_player: int, reason: str) -> Tuple[bool, ta.Info]:
        pass                                                           
        if self.state.game_state['current_phase'] == 'final_round':
                                                   
            return self._next_turn()
        
        self.state.game_state['current_phase'] = 'final_round'
        self.state.game_state['triggering_player'] = triggering_player
        self.state.game_state['rounds_after_trigger'] = 0
        self.state.add_observation(message=self.m("message", "final_round", pid=triggering_player, reason=reason), observation_type=ta.ObservationType.GAME_MESSAGE)
        return self._next_turn()

    def _next_turn(self) -> Tuple[bool, ta.Info]:
        pass                                                                
                                          
        self.state.game_state['turn_phase'] = 'draw'
        
                                          
        if self.state.game_state['current_phase'] == 'final_round':
            self.state.game_state['rounds_after_knock'] += 1
            
                                                                                                   
            final_round_complete = False
            if self.state.game_state.get('knocker') is not None:
                                                                     
                final_round_complete = self.state.game_state['rounds_after_knock'] >= self.state.num_players
            elif self.state.game_state.get('triggering_player') is not None:
                                                                                                 
                final_round_complete = self.state.game_state['rounds_after_knock'] >= (self.state.num_players - 1)
            
            if final_round_complete:
                self._end_game()
                return self.state.step(rotate_player=False)
        
                             
        next_player = (self.state.current_player_id + 1) % self.state.num_players
        self.state.manually_set_current_player_id(next_player)
        
        result = self.state.step(rotate_player=False)
        self._announce_turn_options(next_player)
        return result
    
    def _announce_turn_options(self, player_id: int):
        pass                                                            
        hand_str = self._render_player_hand(player_id)
        discard_top = self._card_to_string(self.state.game_state['discard_pile'][-1]) if self.state.game_state['discard_pile'] else self.m("board", "none").render(_pid=player_id)

        if self.state.game_state['turn_phase'] == 'draw':
            if self.state.game_state['knocker'] is not None:
                options = self.m("options", "final_turns")
            else:
                options = self.m("options", "draw")                       
        else:                          
            if self.state.game_state.get('took_from_discard', False):
                options = self.m("options", "must_swap")
            else:
                options = self.m("options", "swap_or_discard")

        self.state.add_observation(to_id=player_id, message=self.m("board", "turn_view", hand=hand_str, discard=discard_top, options=options), observation_type=ta.ObservationType.GAME_BOARD)
    
    def _end_game(self):
        pass                                             
                                                                          
        for player_id, player in self.state.game_state['players'].items():
                                    
            for card_info in player['cards']:
                card_info['revealed'] = True
            
                                                       
            total_score = 0
            
                                 
            for col in range(self.num_columns):
                column_values = []
                
                                                  
                for row in range(self.num_rows):
                    card_idx = row * self.num_columns + col
                    if card_idx < len(player['cards']):
                        card = player['cards'][card_idx]['card']
                        column_values.append(card['value'])
                
                                                                  
                if len(set(column_values)) == 1 and len(column_values) > 1:
                                                                     
                    column_score = 0
                else:
                                                      
                    column_score = sum(column_values)
                
                total_score += column_score
            
            player['score'] = total_score
        
                                    
        winner_id = min(self.state.game_state['players'].keys(), key=lambda pid: self.state.game_state['players'][pid]['score'])
        winner_score = self.state.game_state['players'][winner_id]['score']
        
                              
        sorted_players = sorted(self.state.game_state['players'].items(), key=lambda x: x[1]['score'])

        scores = "".join(
            self.m("summary", "line", pid=player_id, score=player['score']).render()
            for i, (player_id, player) in enumerate(sorted_players)
        )
        summary = self.m("summary", "full", winner=winner_id, score=winner_score, scores=scores)

                                         
        if self.state.num_players == 2: self.state.set_winner(winner_id, summary)
        else: self.state.set_outcome(reward=1 if self.state.current_player_id == winner_id else 0, reason=summary)
    
    def get_board_str(self) -> str:
        pass                                                         
        if not self.state.game_state:
            return "Game not started"
        output = []
        output.append(self.m("board_str", "title").render())
        if self.state.game_state['discard_pile']: output.append(self.m("board_str", "discard", card=self._card_to_string(self.state.game_state['discard_pile'][-1])).render())
        if self.state.game_state['knocker'] is not None: output.append(self.m("board_str", "knocked", pid=self.state.game_state['knocker']).render())
        output.append("")
        for player_id, player in self.state.game_state['players'].items():
            output.append(self.m("board_str", "player_header", pid=player_id, score=player['score']).render())
            output.append(self._render_player_hand(player_id))
            output.append("")
        return "\n".join(output)