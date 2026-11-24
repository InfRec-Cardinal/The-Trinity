import random
import re
from typing import Optional, Tuple, List, Dict, Any

import textarena as ta

class BriscolaEnv(ta.Env):
    def __init__(self):
        pass                                                  
        super().__init__()
        self.deck = self._create_deck()
        
    def _create_deck(self) -> List[Dict[str, Any]]:
        pass                                               
        suits = ['♠', '♥', '♦', '♣']                                   
        ranks = ['A', '2', '3', '4', '5', '6', '7', 'J', 'Q', 'K']                               
        deck = []
        
        for suit in suits:
            for rank in ranks:
                card = {
                    'rank': rank,
                    'suit': suit,
                    'points': self._get_card_points(rank),
                    'power': self._get_card_power(rank)
                }
                deck.append(card)
        return deck
    
    def _get_card_points(self, rank: str) -> int:
        pass                                                 
        point_values = {
            'A': 11,         
            '3': 10,           
            'K': 4,           
            'Q': 3,                            
            'J': 2,                   
            '7': 0, '6': 0, '5': 0, '4': 0, '2': 0             
        }
        return point_values[rank]
    
    def _get_card_power(self, rank: str) -> int:
        pass                                                                             
        power_values = {
            'A': 8,                      
            '3': 7,            
            'K': 6,           
            'Q': 5,            
            'J': 4,           
            '7': 3, '6': 2, '5': 1, '4': 0, '2': -1           
        }
        return power_values[rank]
    
    def _card_to_string(self, card: Dict[str, Any]) -> str:
        pass                                        
        return f"{card['rank']}{card['suit']}"
    
    def _find_action_token(self, message: str) -> Optional[int]:
        pass                                              
        pattern = re.compile(r"\[play (\d+)\]", re.I)
        match = pattern.search(message)
        
        if match:
            return int(match.group(1)) - 1                            
        return None
    
    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        pass                        
        if num_players not in [2, 3, 4]:
            raise ValueError("Briscola supports 2, 3, or 4 players")
            
        if num_players == 2:
            self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        else:
            self.state = ta.FFAMultiPlayerState(num_players=num_players, seed=seed)
        
                               
        game_state = {
            'players': {},
            'deck': [],
            'trump_suit': None,
            'trump_card': None,
            'current_trick': [],
            'tricks_won': {},
            'points_won': {},
            'phase': 'playing',                     
            'trick_leader': 0,
            'cards_in_hand': 3 if num_players <= 3 else 2
        }
        
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self._init_game()
    
    def _init_game(self):
        pass                       
        gs = self.state.game_state
        
                      
        deck_copy = self.deck.copy()
        random.shuffle(deck_copy)
        
                               
        cards_per_hand = gs['cards_in_hand']
        for player_id in range(self.state.num_players):
            player_hand = []
            for _ in range(cards_per_hand):
                if deck_copy:
                    player_hand.append(deck_copy.pop())
            
            gs['players'][player_id] = {
                'hand': player_hand,
                'points': 0
            }
            gs['tricks_won'][player_id] = []
            gs['points_won'][player_id] = 0
        
                                                                  
        if deck_copy:
            gs['trump_card'] = deck_copy.pop()
            gs['trump_suit'] = gs['trump_card']['suit']
            deck_copy.insert(0, gs['trump_card'])                                    
        
        gs['deck'] = deck_copy
        gs['current_trick'] = []
        gs['trick_leader'] = 0
        gs['phase'] = 'playing'
        
                             
        self._announce_game_start()
        self._announce_turn(self.state.current_player_id)
    
    def _announce_game_start(self):
        pass                                                  
        gs = self.state.game_state
        trump_str = self._card_to_string(gs['trump_card']) if gs['trump_card'] else "None"

        self.state.add_observation(
            message=self.m("game", "start", trump_suit=gs['trump_suit'], trump_card=trump_str),
            observation_type=ta.ObservationType.GAME_MESSAGE
        )
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        max_pos = len(game_state['players'][player_id]['hand']) if player_id in game_state['players'] else 3
        return self.m("prompt", "intro", player_id=player_id, max_pos=max_pos)
    
    def _render_player_hand(self, player_id: int) -> str:
        pass                             
        gs = self.state.game_state
        if player_id not in gs['players']:
            return self.m("hand", "none").render(_pid=player_id)

        player = gs['players'][player_id]
        hand = player['hand']

        if not hand:
            return self.m("hand", "empty").render(_pid=player_id)

        trump_mark = self.m("hand", "trump_mark").render(_pid=player_id)
        output = []
        output.append(self.m("hand", "header").render(_pid=player_id))
        for i, card in enumerate(hand):
            trump_indicator = trump_mark if card['suit'] == gs['trump_suit'] else ""
            output.append(self.m("hand", "card_line", pos=i + 1, card=self._card_to_string(card), points=card['points'], trump_mark=trump_indicator).render(_pid=player_id))

        return "\n".join(output)
    
    def _render_current_trick(self, recipient_id: int) -> str:
        pass                                          
        gs = self.state.game_state
        if not gs['current_trick']:
            return self.m("trick", "empty").render(_pid=recipient_id)

        trump_mark = self.m("hand", "trump_mark").render(_pid=recipient_id)
        output = []
        output.append(self.m("trick", "header").render(_pid=recipient_id))
        for player_id, card in gs['current_trick']:
            trump_indicator = trump_mark if card['suit'] == gs['trump_suit'] else ""
            output.append(self.m("trick", "line", player_id=player_id, card=self._card_to_string(card), trump_mark=trump_indicator).render(_pid=recipient_id))

        return "\n".join(output)
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        player_id = self.state.current_player_id
        gs = self.state.game_state
        
        self.state.add_observation(
            from_id=player_id, 
            message=action, 
            observation_type=ta.ObservationType.PLAYER_ACTION
        )
        
                      
        card_index = self._find_action_token(action)
        
        if card_index is None:
            self.state.set_invalid_move(self.m("invalid_move", "wrong_format"))
            return self.state.step()

                             
        player = gs['players'][player_id]
        if card_index < 0 or card_index >= len(player['hand']):
            self.state.set_invalid_move(self.m("invalid_move", "out_of_range", count=len(player['hand'])))
            return self.state.step()

                       
        played_card = player['hand'].pop(card_index)
        gs['current_trick'].append((player_id, played_card))

        self.state.add_observation(
            message=self.m("action", "played", player_id=player_id, card=self._card_to_string(played_card)),
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
        
                                    
        if len(gs['current_trick']) == self.state.num_players:
            return self._resolve_trick()
        else:
                                 
            return self._next_player_in_trick()
    
    def _next_player_in_trick(self) -> Tuple[bool, ta.Info]:
        pass                                                
        next_player = (self.state.current_player_id + 1) % self.state.num_players
        self.state.manually_set_current_player_id(next_player)
        
        self._announce_turn(next_player)
        return self.state.step(rotate_player=False)
    
    def _resolve_trick(self) -> Tuple[bool, ta.Info]:
        pass                               
        gs = self.state.game_state
        
                                
        winner_id, winning_card = self._determine_trick_winner(gs['current_trick'], gs['trump_suit'])
        
                                        
        trick_points = sum(card['points'] for _, card in gs['current_trick'])
        
                                          
        gs['points_won'][winner_id] += trick_points
        gs['tricks_won'][winner_id].append(gs['current_trick'].copy())
        
        self.state.add_observation(
            message=self.m("action", "trick_win", winner=winner_id, card=self._card_to_string(winning_card), points=trick_points),
            observation_type=ta.ObservationType.GAME_MESSAGE
        )
        
                             
        gs['current_trick'] = []
        
                                          
        self._deal_new_cards()
        
                            
        if self._is_game_over():
            return self._end_game()
        
                                 
        gs['trick_leader'] = winner_id
        self.state.manually_set_current_player_id(winner_id)
        
        self._announce_turn(winner_id)
        return self.state.step(rotate_player=False)
    
    def _determine_trick_winner(self, trick: List[Tuple[int, Dict]], trump_suit: str) -> Tuple[int, Dict]:
        pass                                
        if not trick:
            return 0, {}
        
                                                             
        lead_player_id, lead_card = trick[0]
        lead_suit = lead_card['suit']
        
                                                   
        trump_cards = [(pid, card) for pid, card in trick if card['suit'] == trump_suit]
        
                                                              
        if trump_cards:
            winner_id, winning_card = max(trump_cards, key=lambda x: x[1]['power'])
            return winner_id, winning_card
        
                                       
                                                  
        lead_suit_cards = [(pid, card) for pid, card in trick if card['suit'] == lead_suit]
        
        if lead_suit_cards:
                                                                                
            winner_id, winning_card = max(lead_suit_cards, key=lambda x: x[1]['power'])
            return winner_id, winning_card
        else:
                                                                                
                                                                            
            return lead_player_id, lead_card
    
    def _deal_new_cards(self):
        pass                                           
        gs = self.state.game_state
        
        if not gs['deck']:
            return
        
                                                                  
        players_to_deal = []
        start_player = gs['trick_leader']
        
        for i in range(self.state.num_players):
            player_id = (start_player + i) % self.state.num_players
            players_to_deal.append(player_id)
        
        for player_id in players_to_deal:
            if gs['deck'] and len(gs['players'][player_id]['hand']) < gs['cards_in_hand']:
                new_card = gs['deck'].pop()
                gs['players'][player_id]['hand'].append(new_card)
    
    def _is_game_over(self) -> bool:
        pass                             
        gs = self.state.game_state
        
                                                          
        for player in gs['players'].values():
            if player['hand']:
                return False
        
        return True
    
    def _end_game(self) -> Tuple[bool, ta.Info]:
        pass                                     
        gs = self.state.game_state
        gs['phase'] = 'finished'
        
                                   
        winner_id = max(gs['points_won'].keys(), key=lambda pid: gs['points_won'][pid])
        winner_points = gs['points_won'][winner_id]
        
                              
        sorted_players = sorted(gs['points_won'].items(), key=lambda x: x[1], reverse=True)

        scores = "".join(
            self.m("outcome", "player_line", player_id=player_id, points=points, tricks=len(gs['tricks_won'][player_id])).render()
            for player_id, points in sorted_players
        )
        summary = self.m("outcome", "head", winner=winner_id, points=winner_points, scores=scores)
        
        if self.state.num_players == 2:
                                            
            self.state.set_winner(winner_id, summary)
        else:
                                          
            self.state.set_outcome(
                reward=1 if self.state.current_player_id == winner_id else 0,
                reason=summary
            )
        
        return self.state.step(rotate_player=False)
    
    def _announce_turn(self, player_id: int):
        pass                                      
        gs = self.state.game_state
        
        hand_str = self._render_player_hand(player_id)
        trick_str = self._render_current_trick(player_id)

                             
        scores = []
        for pid in range(self.state.num_players):
            scores.append(self.m("turn", "score_entry", player_id=pid, points=gs['points_won'][pid]).render(_pid=player_id))
        scores_str = " | ".join(scores)

        if gs['deck']:
            trump_info = self.m("turn", "trump_info_deck", trump_suit=gs['trump_suit'], deck_count=len(gs['deck'])).render(_pid=player_id)
        else:
            trump_info = self.m("turn", "trump_info", trump_suit=gs['trump_suit']).render(_pid=player_id)

        self.state.add_observation(
            to_id=player_id,
            message=self.m("turn", "board", hand=hand_str, trick=trick_str, scores=scores_str, trump_info=trump_info),
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def get_board_str(self) -> str:
        pass                                                         
        gs = self.state.game_state
        if not gs:
            return "Game not started"
            
        output = []
        output.append("=== BRISCOLA GAME ===")
        output.append(f"Trump suit: {gs['trump_suit']}")
        
        if gs['trump_card']:
            output.append(f"Trump card: {self._card_to_string(gs['trump_card'])}")
        
        output.append(f"Cards left in deck: {len(gs['deck'])}")
        output.append("")
        
                       
        if gs['current_trick']:
            output.append("Current trick:")
            for player_id, card in gs['current_trick']:
                trump_indicator = " (TRUMP)" if card['suit'] == gs['trump_suit'] else ""
                output.append(f"  Player {player_id}: {self._card_to_string(card)}{trump_indicator}")
            output.append("")
        
                            
        for player_id in range(self.state.num_players):
            if player_id in gs['players']:
                player = gs['players'][player_id]
                hand_size = len(player['hand'])
                points = gs['points_won'][player_id]
                tricks = len(gs['tricks_won'][player_id])
                
                output.append(f"Player {player_id}: {points} points, {tricks} tricks, {hand_size} cards in hand")
        
        return "\n".join(output)