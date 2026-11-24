import re, random
from enum import Enum
from typing import Optional, Tuple, List

import textarena as ta
from textarena.core import GAME_ID
from textarena.envs.Hanabi.renderer import create_board_str

class Suit(Enum):
    pass                                
       
    WHITE = "white"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    RED = "red"


class Card:
    pass                                                  
       
    def __init__(self, suit: Suit, rank: int):
        assert 1 <= rank <= 5, f"The rank should be between 1 and 5, received {rank}."
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"a {self.suit.value} card with rank {self.rank}"

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit


class HanabiEnv(ta.Env):
    def __init__(self, info_tokens: int = 8, fuse_tokens: int = 3,):

        self.deck_size = 50
        self.info_tokens = info_tokens
        self.fuse_tokens = fuse_tokens

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                        

             
                                                                                
                                                                                    

                

           
        assert num_players <= 5, f"Hanabi is played with 2 to 5 players, received {num_players} players."
        self.state = ta.TeamMultiPlayerState(num_players=num_players, seed=seed, error_allowance=1)
        self.num_players = num_players
        self.hand_size = 5 if num_players <= 3 else 4                                                             
        self.deck = self._generate_deck()

        game_state = {
            "info_tokens": self.info_tokens,
            "fuse_tokens": self.fuse_tokens,
            "fireworks": {
                Suit.WHITE: 0,
                Suit.YELLOW: 0,
                Suit.GREEN: 0,
                Suit.BLUE: 0,
                Suit.RED: 0,
            },
            "deck_size": self.deck_size,
            "deck": self.deck,
            "player_hands": {
                player: self.generate_hand(self.deck) for player in range(self.num_players)
            },
            "discard_pile": [],
            "last_round": -1,
        }
        self.state.reset(game_state=game_state, player_prompt_function=self._initial_prompt)

                         
        self.state.add_observation(to_id=self.state.current_player_id, message=self._state_description(),
                                   observation_type=ta.ObservationType.GAME_MESSAGE)

    def get_board_str(self) -> str:
        pass                                               
        return create_board_str(game_state=self.state.game_state)

    def _initial_prompt(self, player_id: int, game_state: dict) -> str:
        return self.m("player_prompt", "intro", player_id=player_id, num_players=self.state.num_players)

    def _card(self, card: "Card"):
        pass                                                                                     
        return self.m("card", "desc", color=self.m("color", card.suit.value), rank=card.rank)

    def _state_description(self):
        pass                                                            

                
                                                         
           
        pid = self.state.current_player_id
        discard_pile = "".join(
            self._card(card).render(_pid=pid) + "\n" for card in self.state.game_state['discard_pile']
        )
        visible_cards = ""

        for player_id in range(self.num_players):
            if player_id == self.state.current_player_id:
                continue
            else:
                visible_cards += self.m("state", "player_cards_header", pid=player_id).render(_pid=pid)
                for i, card in enumerate(self.state.game_state['player_hands'][player_id]):
                    if card is not None:
                        visible_cards += self.m("state", "card_line", idx=i, card=self._card(card)).render(_pid=pid)

        return self.m(
            "state", "description",
            pid=self.state.current_player_id,
            fuse=self.state.game_state['fuse_tokens'],
            info=self.state.game_state['info_tokens'],
            c_white=self.m("color", Suit.WHITE.value), fw_white=self.state.game_state['fireworks'][Suit.WHITE],
            c_yellow=self.m("color", Suit.YELLOW.value), fw_yellow=self.state.game_state['fireworks'][Suit.YELLOW],
            c_green=self.m("color", Suit.GREEN.value), fw_green=self.state.game_state['fireworks'][Suit.GREEN],
            c_blue=self.m("color", Suit.BLUE.value), fw_blue=self.state.game_state['fireworks'][Suit.BLUE],
            c_red=self.m("color", Suit.RED.value), fw_red=self.state.game_state['fireworks'][Suit.RED],
            visible_cards=visible_cards,
            discard_pile=discard_pile,
        )

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                           
             
                                              

                
                                                                              
           
        self.state.add_observation(from_id=self.state.current_player_id, to_id=self.state.current_player_id,
                                   message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
                           
        if re.compile(r"\[reveal\]", re.IGNORECASE).search(action):                          
            self._handle_reveal(action)

        elif re.compile(r"\[play\]", re.IGNORECASE).search(action):                        
            self._handle_play(action)

        elif re.compile(r"\[discard\]", re.IGNORECASE).search(action):                           
            self._handle_discard(action)

        else:                 
            self.state.set_invalid_move(reason=self.m("invalid", "generic_action_reason"))

                                          
        self._check_game_end()

                                                                          
        if self.state.game_info[self.state.current_player_id]["invalid_move"]:
            message = self.m("skip_turn", pid=self.state.current_player_id,
                             count=self.state.error_allowance + 1)
            self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=message,
                                       observation_type=ta.ObservationType.GAME_MESSAGE)
                                                   
            self.state.game_info[self.state.current_player_id]["invalid_move"] = False
            self.state.made_invalid_move = False
            self.state.error_count = 0

                                                                                                         
        self._rotate_players()

        return self.state.step(rotate_player=False)

    def _handle_discard(self, action: str) -> None:
        pass                                                    

             
                                              

                
                
           
        card_idx = re.findall(r"(\d)", action)
        if card_idx:
            try:
                card = self.state.game_state['player_hands'][self.state.current_player_id].pop(int(card_idx[0]))
            except IndexError:
                self.state.set_invalid_move(reason=self.m("invalid", "discard_nonexist_reason"))
                self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                           message=self.m("invalid", "discard_nonexist_detail",
                                                          max_card=self.hand_size - 1, card_index=card_idx[0]),
                                           observation_type=ta.ObservationType.GAME_MESSAGE)
                return


                                              
            self.state.game_state['discard_pile'].append(card)

                                     
            if self.state.game_state['info_tokens'] < 8:
                self.state.game_state['info_tokens'] += 1
                message = self.m("discard", "replenished", pid=self.state.current_player_id, card=self._card(card))

            else:
                message = self.m("discard", "cap_reached", pid=self.state.current_player_id, card=self._card(card))

                            
            self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=message,
                                       observation_type=ta.ObservationType.GAME_MESSAGE)

                             
            card = self._draw_card(self.state.game_state['deck'])

                                                 
            self.state.game_state['player_hands'][self.state.current_player_id].append(card)

        else:                              
            self.state.set_invalid_move(reason=self.m("invalid", "discard_parse_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                       message=self.m("invalid", "discard_parse_detail"),
                                       observation_type=ta.ObservationType.GAME_MESSAGE)

    def _handle_play(self, action: str) -> None:
        pass                                                 

             
                                              

                
                
           
        card_idx = re.findall(r"(\d)", action)
        if card_idx:
            try:
                card = self.state.game_state['player_hands'][self.state.current_player_id].pop(int(card_idx[0]))
            except IndexError:
                self.state.set_invalid_move(reason=self.m("invalid", "play_nonexist_reason"))
                self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                           message=self.m("invalid", "play_nonexist_detail",
                                                          max_card=self.hand_size - 1, card_index=card_idx[0]),
                                           observation_type=ta.ObservationType.GAME_MESSAGE)
                return


                            
            if self._play(card):
                message = self.m("play", "success", pid=self.state.current_player_id, card=self._card(card))
                self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=message,
                                           observation_type=ta.ObservationType.GAME_MESSAGE)

            else:            
                self.state.game_state['fuse_tokens'] -= 1
                message = self.m("play", "fail", pid=self.state.current_player_id, card=self._card(card),
                                 fuse_tokens=self.state.game_state['fuse_tokens'])
                self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=message,
                                           observation_type=ta.ObservationType.GAME_MESSAGE)

                                                  
                self.state.game_state['discard_pile'].append(card)

                             
            card = self._draw_card(self.state.game_state['deck'])

                                                 
            self.state.game_state['player_hands'][self.state.current_player_id].append(card)

        else:                              
            self.state.set_invalid_move(reason=self.m("invalid", "play_parse_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                       message=self.m("invalid", "play_parse_detail"),
                                       observation_type=ta.ObservationType.GAME_MESSAGE)

    def _handle_reveal(self, action: str) -> None:
        pass                                                   

             
                                              

                
                
           
                        
        if self.state.game_state['info_tokens'] == 0:                                       
            self.state.set_invalid_move(reason=self.m("invalid", "reveal_no_info_reason"))

        else:                                                        
            card_index, color, player, rank = self._parse_hint(action)

            if not self.check_valid_move(card_index, color, player, rank):
                return

                                                                 
                                                                              
            if color:                                         
                hint = self.m("reveal", "hint_color", card_index=card_index[0], player=player[0],
                              color=self.m("color", color[0]))

            else:                                         
                hint = self.m("reveal", "hint_rank", card_index=card_index[0], player=player[0], rank=rank[0])

            self.state.game_state['info_tokens'] = self.state.game_state['info_tokens'] - 1
            self.state.add_observation(from_id=self.state.current_player_id, to_id=-1, message=hint,
                                       observation_type=ta.ObservationType.GAME_MESSAGE)

    def check_valid_move(self, card_index: list, color: list, player: list, rank: list) -> bool:
        pass                                                                                                     

             
                                                          
                                                    
                                                        
                                                   

                
                                                

           
        if player == [] or card_index == [] or (color == [] and rank == []):                     
            self.state.set_invalid_move(reason=self.m("invalid", "reveal_incomplete_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                    message=self.m("invalid", "reveal_incomplete_detail"),
                                    observation_type=ta.ObservationType.GAME_MESSAGE)
            return False

        if int(player[0]) == self.state.current_player_id:
            self.state.set_invalid_move(reason=self.m("invalid", "reveal_own_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                    message=self.m("invalid", "reveal_own_detail"),
                                    observation_type=ta.ObservationType.GAME_MESSAGE)
            return False

        elif int(player[0]) < 0 or int(player[0]) >= self.num_players:
            self.state.set_invalid_move(reason=self.m("invalid", "reveal_bad_teammate_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                    message=self.m("invalid", "reveal_bad_teammate_detail",
                                                   max_player=self.num_players - 1,
                                                   pid=self.state.current_player_id),
                                    observation_type=ta.ObservationType.GAME_MESSAGE)
            return False

        if int(card_index[0]) < 0 or int(card_index[0]) >= self.hand_size:
            self.state.set_invalid_move(reason=self.m("invalid", "reveal_bad_card_reason"))
            self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                    message=self.m("invalid", "reveal_bad_card_detail",
                                                   max_card=self.hand_size - 1, card_index=card_index[0]),
                                    observation_type=ta.ObservationType.GAME_MESSAGE)
            return False

                                                             
        if color and color[0]:                                        
            try:
                Suit(color[0])
            except ValueError:
                self.state.set_invalid_move(reason=self.m("invalid", "reveal_bad_color_reason"))
                self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                        message=self.m("invalid", "reveal_bad_color_detail", color=color[0]),
                                        observation_type=ta.ObservationType.GAME_MESSAGE)
                return False

                                                           
        if rank and rank[0]:                                       
            try:
                rank_value = int(rank[0])
                if rank_value < 1 or rank_value > 5:
                    self.state.set_invalid_move(reason=self.m("invalid", "reveal_bad_rank_reason"))
                    self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                            message=self.m("invalid", "reveal_bad_rank_detail", rank=rank[0]),
                                            observation_type=ta.ObservationType.GAME_MESSAGE)
                    return False
            except ValueError:
                self.state.set_invalid_move(reason=self.m("invalid", "reveal_bad_rank_format_reason"))
                self.state.add_observation(from_id=GAME_ID, to_id=self.state.current_player_id,
                                        message=self.m("invalid", "reveal_bad_rank_format_detail", rank=rank[0]),
                                        observation_type=ta.ObservationType.GAME_MESSAGE)
                return False

        return True

    @staticmethod
    def _parse_hint(action: str):
        pass                                              
           
        player = re.findall(r"player (\d+)", action)
        card_index = re.findall(r"card (\d)", action)
        color = re.findall(r"color ([A-Z]|[a-z]*)", action)
        rank = re.findall(r"rank (\d)", action)
        return card_index, color, player, rank

    def _play(self, card: Card) -> bool:
        pass                                                                                                                       
                                                                               

             
                                        

                
                                                                                 
           
        rocket = self.state.game_state['fireworks'][card.suit]

        if rocket == card.rank - 1:                                    
            self.state.game_state['fireworks'][card.suit] += 1
            return True

        return False                

    def _rotate_players(self):
        pass                                                             
           
        next_player_id = (self.state.current_player_id + 1) % self.num_players
        self.state.manually_set_current_player_id(new_player_id=next_player_id)
        if not self.state.made_invalid_move:
            self.state.add_observation(to_id=next_player_id,
                                       message=self._state_description(),
                                       observation_type=ta.ObservationType.GAME_MESSAGE)

    def _check_game_end(self):
        pass                                                                             

                                                                                  
                                                                                
                                                                                
                                                                              
                                                                                   
                                                                         
                                                                               

                
                

           
                           
        if len(self.state.game_state['deck']) == 0:                        
            if self.state.game_state['last_round'] == -1:                        
                self.state.add_observation(from_id=-1, to_id=-1, message=self.m("final_round"),
                                           observation_type=ta.ObservationType.GAME_MESSAGE)
                self.state.game_state['last_round'] = self.state.current_player_id

            elif self.state.game_state['last_round'] == self.state.current_player_id:                      
                self.state.set_draw(reason=self.m("outcome", "deck_empty"))
                self.state.rewards = {pid: self._calculate_scores() for pid in range(self.num_players)}

        if self.state.game_state['fuse_tokens'] <= 0:                                 
            self.state.set_draw(reason=self.m("outcome", "fuse_empty"))
            self.state.rewards = {pid: self._calculate_scores() for pid in range(self.num_players)}

                            
        if self._completed_fireworks():
            self.state.set_winners(list(range(self.num_players)), reason=self.m("outcome", "win"))
            self.state.rewards = {pid: self._calculate_scores() for pid in range(self.num_players)}

    def _completed_fireworks(self) -> bool:
        pass                                               

                
                                                       
           
        for rocket in self.state.game_state['fireworks'].keys():
            if self.state.game_state['fireworks'][rocket] < 5:
                return False
        return True

    def _calculate_scores(self) -> int:
        pass                                                                  

                
                                 
           
        return sum([x for x in self.state.game_state['fireworks'].values()])

    @staticmethod
    def _generate_deck() -> List[Card]:
        pass                                                                                                                        
                                                                                                          

                
                                                                                 
           
        ranks = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
        deck = []

        for suit in Suit:
            for rank in ranks.keys():
                for q in range(ranks[rank]):
                    deck.append(Card(suit=suit, rank=rank))

        return deck

    def generate_hand(self, deck: List[Card]) -> List[Card]:
        pass                                                           

             
                                                                       

                
                                                                                  

              
                                                                                  
           
        return [self._draw_card(deck) for _ in range(self.hand_size)]

    @staticmethod
    def _draw_card(deck: List[Card]) -> Optional[Card]:
        pass                                      
             
                                               

                
                                                                                     
           
        if len(deck) > 0:
            return deck.pop(random.randrange(len(deck)))
        else:
            return None


