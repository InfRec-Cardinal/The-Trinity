import random
import re
from typing import Optional, Tuple, List, Dict, Any

import textarena as ta

class GermanWhistEnv(ta.Env):
    def __init__(self):
        pass                                                      
        super().__init__()
        self.deck = self._create_deck()

    def _create_deck(self) -> List[Dict[str, Any]]:
        pass                                                    
        suits = ['♠', '♥', '♦', '♣']                                   
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = []

        for suit in suits:
            for rank in ranks:
                card = {
                    'rank': rank,
                    'suit': suit,
                    'power': self._get_card_power(rank)
                }
                deck.append(card)
        return deck

    def _get_card_power(self, rank: str) -> int:
        pass                                                            
        power_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
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
        if num_players != 2:
            raise ValueError("German Whist is a two-player game only")

        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)

                                                            
        game_state = self._init_game_state()

        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)

                                            
        self._announce_game_start()
        self._announce_turn(self.state.current_player_id)

    def _init_game_state(self) -> Dict[str, Any]:
        pass                                                 
                      
        deck_copy = self.deck.copy()
        random.shuffle(deck_copy)

                                      
        players = {}
        for player_id in range(2):
            player_hand = []
            for _ in range(13):
                if deck_copy:
                    player_hand.append(deck_copy.pop())

            players[player_id] = {
                'hand': player_hand
            }

                                                  
        trump_card = None
        trump_suit = None
        next_card = None

        if deck_copy:
            trump_card = deck_copy.pop()
            trump_suit = trump_card['suit']
                                                          
            deck_copy.append(trump_card)

                                                              
        if deck_copy:
            next_card = deck_copy[-1]

                                    
        return {
            'players': players,
            'deck': deck_copy,
            'trump_suit': trump_suit,
            'trump_card': trump_card,
            'current_trick': [],
                                                                    
            'tricks_won': {0: 0, 1: 0},
                                                                         
            'playing_tricks_won': {0: 0, 1: 0},
            'phase': 'learning',                               
            'trick_leader': 0,
            'next_card': next_card,                                              
            'tricks_in_learning': 0,
            'tricks_in_playing': 0
        }

    def _announce_game_start(self):
        pass                                                  
        gs = self.state.game_state
        trump_str = self._card_to_string(gs['trump_card']) if gs['trump_card'] else self.m("game_start", "no_trump_card")

        self.state.add_observation(
            message=self.m("game_start", "intro", trump_suit=gs['trump_suit'], trump_str=trump_str),
            observation_type=ta.ObservationType.GAME_MESSAGE
        )

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        if game_state['phase'] == 'learning':
            phase_info = self.m("player_prompt", "phase_learning")
        else:
            phase_info = self.m("player_prompt", "phase_playing")

        hand_size = len(game_state['players'][player_id]['hand']) if player_id in game_state['players'] else 13
        return self.m("player_prompt", "intro", player_id=player_id, phase_info=phase_info, hand_size=hand_size)

    def _render_player_hand(self, player_id: int):
        pass                                               
        gs = self.state.game_state
        if player_id not in gs['players']:
            return self.m("hand", "no_cards")

        player = gs['players'][player_id]
        hand = player['hand']

        if not hand:
            return self.m("hand", "no_cards_in_hand")

                                                    
        suits_order = [gs['trump_suit']] + [suit for suit in ['♠', '♥', '♦', '♣'] if suit != gs['trump_suit']]

        output = self.m("hand", "header")

        for suit in suits_order:
            suit_cards = [(i, card) for i, card in enumerate(hand) if card['suit'] == suit]
            if suit_cards:
                                           
                suit_cards.sort(key=lambda x: x[1]['power'], reverse=True)

                trump_indicator = self.m("hand", "trump_indicator") if suit == gs['trump_suit'] else ""
                output = self.m("hand", "suit_line", observation=output, suit=suit, trump_indicator=trump_indicator)

                for original_index, card in suit_cards:
                    output = self.m("hand", "card_line", observation=output, index=original_index + 1, card=self._card_to_string(card))

        return output

    def _render_current_trick(self):
        pass                                          
        gs = self.state.game_state
        if not gs['current_trick']:
            return self.m("trick_view", "empty")

        output = self.m("trick_view", "header")
        for player_id, card in gs['current_trick']:
            trump_indicator = self.m("trick_view", "trump_indicator") if card['suit'] == gs['trump_suit'] else ""
            output = self.m("trick_view", "card_line", observation=output, player_id=player_id, card=self._card_to_string(card), trump_indicator=trump_indicator)

        return output

    def _render_next_card_info(self):
        pass                                                     
        gs = self.state.game_state

        if gs['phase'] != 'learning':
            return self.m("next_card", "playing_phase")

        if not gs['next_card']:
            return self.m("next_card", "deck_empty")

        if gs['next_card']['suit'] == gs['trump_suit']:
            return self.m("next_card", "available_trump", card=self._card_to_string(gs['next_card']))
        return self.m("next_card", "available", card=self._card_to_string(gs['next_card']))

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
            self.state.set_invalid_move(self.m("invalid_move", "bad_position", hand_size=len(player['hand'])))
            return self.state.step()

        played_card = player['hand'][card_index]

                                       
        if not self._is_valid_play(player_id, played_card):
            lead_suit = gs['current_trick'][0][1]['suit'] if gs['current_trick'] else None
            if lead_suit:
                self.state.set_invalid_move(self.m("invalid_move", "must_follow_suit", lead_suit=lead_suit))
            else:
                self.state.set_invalid_move(self.m("invalid_move", "invalid_play"))
            return self.state.step()

                       
        player['hand'].pop(card_index)
        gs['current_trick'].append((player_id, played_card))

        self.state.add_observation(
            message=self.m("game_action", "played", player_id=player_id, card=self._card_to_string(played_card)),
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )

                                    
        if len(gs['current_trick']) == 2:
            return self._resolve_trick()
        else:
                                 
            return self._next_player_in_trick()

    def _is_valid_play(self, player_id: int, played_card: Dict[str, Any]) -> bool:
        pass                                               
        gs = self.state.game_state

                                                 
        if not gs['current_trick']:
            return True

                           
        lead_suit = gs['current_trick'][0][1]['suit']

                                                    
        if played_card['suit'] == lead_suit:
            return True

                                                                         
        player = gs['players'][player_id]
        has_lead_suit = any(card['suit'] == lead_suit for card in player['hand'])

        return not has_lead_suit

    def _next_player_in_trick(self) -> Tuple[bool, ta.Info]:
        pass                                                
        next_player = 1 - self.state.current_player_id                          
        self.state.manually_set_current_player_id(next_player)

        self._announce_turn(next_player)
        return self.state.step(rotate_player=False)

    def _resolve_trick(self) -> Tuple[bool, ta.Info]:
        pass                               
        gs = self.state.game_state

                                
        winner_id, winning_card = self._determine_trick_winner(gs['current_trick'], gs['trump_suit'])
        loser_id = 1 - winner_id

                               
        gs['tricks_won'][winner_id] += 1

        if gs['phase'] == 'learning':
            gs['tricks_in_learning'] += 1
            message = self.m("trick", "won_learning", winner_id=winner_id, card=self._card_to_string(winning_card))
        else:
            gs['tricks_in_playing'] += 1
            gs['playing_tricks_won'][winner_id] += 1
            message = self.m("trick", "won", winner_id=winner_id, card=self._card_to_string(winning_card))

        self.state.add_observation(
            message=message,
            observation_type=ta.ObservationType.GAME_MESSAGE
        )

                             
        gs['current_trick'] = []

                                                    
        if gs['phase'] == 'learning' and gs['deck']:
            self._handle_learning_phase_cards(winner_id, loser_id)

                                    
        if gs['phase'] == 'learning' and not gs['deck']:
            gs['phase'] = 'playing'
            self.state.add_observation(
                message=self.m("phase", "learning_complete"),
                observation_type=ta.ObservationType.GAME_MESSAGE
            )

                            
        if self._is_game_over():
            return self._end_game()

                                 
        gs['trick_leader'] = winner_id
        self.state.manually_set_current_player_id(winner_id)

        self._announce_turn(winner_id)
        return self.state.step(rotate_player=False)

    def _handle_learning_phase_cards(self, winner_id: int, loser_id: int):
        pass                                                  
        gs = self.state.game_state

        if not gs['deck']:
            return

                                                  
        if gs['next_card']:
            gs['players'][winner_id]['hand'].append(gs['next_card'])
            self.state.add_observation(
                to_id=winner_id,
                message=self.m("draw", "winner_received", card=self._card_to_string(gs['next_card'])),
                observation_type=ta.ObservationType.GAME_MESSAGE
            )

                                   
        if gs['deck']:
            gs['deck'].pop()

                                                  
        if gs['deck']:
            loser_card = gs['deck'].pop()
            gs['players'][loser_id]['hand'].append(loser_card)

            self.state.add_observation(
                to_id=loser_id,
                message=self.m("draw", "loser_received", card=self._card_to_string(loser_card)),
                observation_type=ta.ObservationType.GAME_MESSAGE
            )

                                                           
            if gs['deck']:
                gs['next_card'] = gs['deck'][-1]
                self.state.add_observation(
                    to_id=winner_id,
                    message=self.m("draw", "winner_preview", card=self._card_to_string(gs['next_card'])),
                    observation_type=ta.ObservationType.GAME_MESSAGE
                )
            else:
                gs['next_card'] = None
        else:
            gs['next_card'] = None

    def _determine_trick_winner(self, trick: List[Tuple[int, Dict]], trump_suit: str) -> Tuple[int, Dict]:
        pass                                
        if not trick:
            return 0, {}

                                               
        lead_suit = trick[0][1]['suit']

                                                   
        trump_cards = [(pid, card) for pid, card in trick if card['suit'] == trump_suit]
        non_trump_cards = [(pid, card) for pid, card in trick if card['suit'] != trump_suit]

                                                      
        if trump_cards:
            winner_id, winning_card = max(trump_cards, key=lambda x: x[1]['power'])
            return winner_id, winning_card

                                                        
        lead_suit_cards = [(pid, card) for pid, card in non_trump_cards if card['suit'] == lead_suit]

        if lead_suit_cards:
            winner_id, winning_card = max(lead_suit_cards, key=lambda x: x[1]['power'])
            return winner_id, winning_card

                                                    
        return trick[0][0], trick[0][1]

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

                                                                            
        p0_playing = gs['playing_tricks_won'][0]
        p1_playing = gs['playing_tricks_won'][1]

        winner_id = 0 if p0_playing > p1_playing else 1

        summary = self.m(
            "outcome", "summary",
            l0=gs['tricks_won'][0] - p0_playing, l1=gs['tricks_won'][1] - p1_playing,
            p0=p0_playing, p1=p1_playing,
            winner_id=winner_id, winner_tricks=gs['playing_tricks_won'][winner_id]
        )

        self.state.set_winner(winner_id, summary)

        return self.state.step(rotate_player=False)

    def _announce_turn(self, player_id: int):
        pass                                      
        gs = self.state.game_state

        hand_str = self._render_player_hand(player_id)
        trick_str = self._render_current_trick()
        next_card_str = self._render_next_card_info()

                            
        if gs['phase'] == 'learning':
            scores_str = self.m("turn", "scores_learning", tricks0=gs['tricks_won'][0], tricks1=gs['tricks_won'][1])
        else:
            scores_str = self.m("turn", "scores_playing", tricks0=gs['playing_tricks_won'][0], tricks1=gs['playing_tricks_won'][1])

                           
        if gs['phase'] == 'learning':
            phase_str = self.m("turn", "phase_learning", phase=gs['phase'].upper(), remaining_cards=len(gs['deck']))
        else:
            phase_str = self.m("turn", "phase", phase=gs['phase'].upper())

        message = self.m("turn", "board", hand=hand_str, trick=trick_str, next_card=next_card_str, scores=scores_str, phase=phase_str)

        self.state.add_observation(
            to_id=player_id,
            message=message,
            observation_type=ta.ObservationType.GAME_BOARD
        )

    def get_board_str(self):
        pass                                                         
        gs = self.state.game_state
        if not gs:
            return self.m("board_str", "not_started")

        output = self.m("board_str", "header")
        output = self.m("board_str", "phase", observation=output, phase=gs['phase'].upper())
        output = self.m("board_str", "trump_suit", observation=output, trump_suit=gs['trump_suit'])

        if gs['trump_card']:
            output = self.m("board_str", "trump_card", observation=output, card=self._card_to_string(gs['trump_card']))

        if gs['phase'] == 'learning':
            output = self.m("board_str", "cards_left", observation=output, count=len(gs['deck']))
            if gs['next_card']:
                output = self.m("board_str", "next_card", observation=output, card=self._card_to_string(gs['next_card']))

        output = self.m("board_str", "blank", observation=output)

                       
        if gs['current_trick']:
            output = self.m("board_str", "current_trick", observation=output)
            for player_id, card in gs['current_trick']:
                trump_indicator = self.m("board_str", "trump_indicator") if card['suit'] == gs['trump_suit'] else ""
                output = self.m("board_str", "trick_line", observation=output, player_id=player_id, card=self._card_to_string(card), trump_indicator=trump_indicator)
            output = self.m("board_str", "blank", observation=output)

                            
        for player_id in range(2):
            if player_id in gs['players']:
                player = gs['players'][player_id]
                hand_size = len(player['hand'])
                tricks = gs['tricks_won'][player_id]
                scoring = gs['playing_tricks_won'][player_id]

                output = self.m("board_str", "player_line", observation=output, player_id=player_id, scoring=scoring, tricks=tricks, hand_size=hand_size)

        return output