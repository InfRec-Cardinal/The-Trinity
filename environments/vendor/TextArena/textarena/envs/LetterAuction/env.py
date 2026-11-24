import re, random
from typing import Optional, Tuple, Dict, Any, List

import textarena as ta

import nltk
nltk.download("words")
from nltk.corpus import words

en_uk_dict = set(words.words())


class LetterAuctionEnv(ta.Env):
    pass                                           
    def __init__(self, starting_coins: int = 100, max_turns: int = 26):
        pass                                                           
        
             
                                  
           
        self.letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.letter_values = [1 for _ in self.letters]
        self.starting_coins = starting_coins
        self.max_turns = max_turns 

    @property
    def terminal_render_keys(self):
        return ["rendered_text", "turn"]

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                             
                                   
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed, max_turns=self.max_turns)

                                     
        self.player_states = {
            0: {
                "coins": self.starting_coins,
                "letters": [],
                "letter_values": [],
                "letter_bid_history": {
                    i: None for i in range(len(self.letters))
                },
                "word": None,
                "word_value": 0,
            },
            1: {
                "coins": self.starting_coins,
                "letters": [],
                "letter_values": [],
                "letter_bid_history": {
                    i: None for i in range(len(self.letters))
                },
                "word": None,
                "word_value": 0,
            }
        }

                             
        self.current_player = 0 
        random.shuffle(self.letters) 
        self.round_number = 0 
        self.round_letter = self.letters[self.round_number]
        self.bid_amount = self.letter_values[self.round_number] 

                                   
        game_state = {
            "player_states": self.player_states,
            "rendered_text": self.render_text(),
            "turn": self.current_player,
        }
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
    

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        pass                                              
        prompt = (
            f"You are Player {player_id}. You are currently in the Letter Auction game.\n"
            "The goal of the game is to strategically bid on letters to form the highest value word. This is how the game works.\n"
            "You must listen to the gamemaster for guidance to play the game.\n"
            "The game consists of a series of rounds. In each round, a letter will be put up for auction.\n"
            "You can bid on the letter using your coins. The player with the highest bid wins the letter.\n"
            "The letter will be added to your collection, and the coins you bid will be deducted from your total.\n"
            "This bidding of letters will repeat till all the letters have been auctioned off. You are not rewarded for saving your coins.\n"
            "After all the letters have been auctioned, you will use the letters to form the highest value english word from the letters won.\n"
            "The player with the highest value word wins the game.\n"
            "If you want to bid, submit your bid amount in square brackets like [bid 2] or [bid 10].\n"
            "If you do not want to bid, submit [pass].\n"
            "For the submission of the highest value word, you will be prompted at the end of the game to submit them in square brackets like [dog].\n"
            "Here is your starting information:\n"
            f"Your current coins: {self.player_states[player_id]['coins']}\n"
            f"Your current letters: {self.player_states[player_id]['letters']}\n"
            "\n"
            f"[Game] Player 0 will go first. The first letter for bid: {self.round_letter}.\n"
            f"Starting bid is {self.bid_amount} coin. You can bid any amount of coins, or choose not to bid.\n"
        )
        return prompt
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                 
        player_id = self.state.current_player_id

                              
        if player_id != self.current_player:
            raise ValueError(f"Invalid player ID: {player_id}. It is not the turn of player {player_id}.")

                                
        self.state.add_observation(from_id=player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        self.auction_over_prompt = ""
        next_player = True                    

        if self.round_number < len(self.letters):
                           
            match = re.search(r"\[(bid \d+|pass)\]", action, re.IGNORECASE)

            if not match:
                reason = f"Invalid action: {action}. Please enter a valid action: '[bid <amount>]' or '[pass]'."
                self.state.set_invalid_move(reason=reason)
            else:
                action_text = match.group(1).lower()
                                                                               
                if self.player_states[player_id]["letter_bid_history"][self.round_number] is None:
                    self.player_states[player_id]["letter_bid_history"][self.round_number] = "pass" if "pass" in action_text else "bid"

                if "pass" in action_text:
                    next_player = self._pass_bid(player_id)
                else:
                    bid_amount = int(action_text.split()[1])
                    next_player = self._place_bid(player_id, bid_amount)

        else:
                                   
            match = re.search(r"\[([a-zA-Z]+)\]", action)
            if not match:
                reason = f"Invalid action: {action}. Please enter a valid action: '[<word>]'."
                self.state.set_invalid_move(reason=reason)
            else:
                word = match.group(1).lower()
                self._calculate_word_value(player_id, word)

                                        
        self.state.game_state["rendered_text"] = self.render_text()

                                   
        if self._check_game_done():
            p0_score = self.player_states[0]["word_value"]
            p1_score = self.player_states[1]["word_value"]

            if p0_score > p1_score:
                self.state.set_winner(player_id=0, reason=f"Player 0 wins with a score of {p0_score}")
            elif p1_score > p0_score:
                self.state.set_winner(player_id=1, reason=f"Player 1 wins with a score of {p1_score}")
            else:
                self.state.set_draw(reason="It's a draw!")

        return self.state.step(rotate_player=next_player)

    
    def _pass_bid(self, player_id: int) -> bool:
        pass                                                                           
        opponent_id = 1 - player_id
        letter = self.round_letter
        round_num = self.round_number
        bid_status = self.player_states[opponent_id]["letter_bid_history"][round_num]

        prompt = f"Player {player_id} passes on the letter '{letter}'."
        
                                                                             
        if bid_status is None:
                                                           
            next_player = True
            prompt += self._turn_manager(next_round=False, next_player=next_player)

        elif bid_status == "bid":
                                                        
            self._assign_letter(opponent_id, letter, self.bid_amount)
            prompt += f" Player {opponent_id} will have '{letter}' for {self.bid_amount}."
            next_player = False
            prompt += self._turn_manager(next_round=True, next_player=next_player)

        else:
                                                           
            prompt += f" Player {opponent_id} also passes on the letter '{letter}'. So, no one will gain the letter."
            next_player = False
            prompt += self._turn_manager(next_round=True, next_player=next_player)

        self.state.add_observation(message=prompt, observation_type=ta.ObservationType.GAME_MESSAGE)

        return next_player

    def _place_bid(self, player_id: int, bid_amount: int) -> bool:
        pass                                    
        opponent_id = 1 - player_id
        letter = self.round_letter
        round_num = self.round_number
        opponent_status = self.player_states[opponent_id]["letter_bid_history"][round_num]

                                                  
        if self.player_states[player_id]["coins"] < bid_amount:
            reason = f"Invalid bid: {bid_amount}. You do not have enough coins."
            self.state.set_invalid_move(reason=reason)
            return False

                                                                        
        if opponent_status == "bid" and bid_amount <= self.bid_amount:
            reason = f"Invalid bid: {bid_amount}. You must bid more than the current bid of {self.bid_amount}."
            self.state.set_invalid_move(reason=reason)
            return False

        prompt = f"Player {player_id} bids {bid_amount} on the letter '{letter}'."

                                          
        if opponent_status is None:
            self.bid_amount = bid_amount
            next_player = True
            prompt += self._turn_manager(next_round=False, next_player=next_player)

                                          
        elif opponent_status == "bid":
                                                                                       
                                                                              
            self.bid_amount = bid_amount
            next_player = True
            prompt += self._turn_manager(next_round=False, next_player=next_player)

                                 
        else:
                                                       
            prompt += f" Since Player {opponent_id} passes on the letter '{letter}', Player {player_id} will have it for {bid_amount}."
            self._assign_letter(player_id, letter, bid_amount)
            next_player = True
            prompt += self._turn_manager(next_round=True, next_player=next_player)

        self.state.add_observation(message=prompt, observation_type=ta.ObservationType.GAME_MESSAGE)

        return next_player


    def _assign_letter(self, player_id: int, letter: str, bid_amount: int) -> None:
        pass                                   
        self.player_states[player_id]["letters"].append(letter)
        self.player_states[player_id]["letter_values"].append(bid_amount)
        self.player_states[player_id]["coins"] -= bid_amount

    def _turn_manager(self, next_round: bool = False, next_player: Optional[bool] = False) -> str:
        pass                                                                                                                       

             
                                                                                   
                                                                                     
        
                
                                                                      
           

        if next_player:
                                  
            self.current_player = 1 - self.current_player

        if next_round:
                                                               
            self.round_number += 1
            if self.round_number < len(self.letters):
                self.round_letter = self.letters[self.round_number]
                self.bid_amount = self.letter_values[self.round_number]
                next_prompt = f" Player {self.current_player}, do you want to start bid on the letter '{self.round_letter}' for {self.bid_amount}?"
            else:
                                     
                next_prompt = "The auction is over. Now, players will use the letters they've won to form the highest value english word from the letters won. The player with the highest value word wins the game. To submit the word, submit it in square brackets like [dog]."

        else:
            next_prompt = f" Player {self.current_player}, do you want to bid on the letter '{self.round_letter}' for more than {self.bid_amount}?"

        return next_prompt


    def _calculate_word_value(self, player_id: int, word: str) -> None:
        pass                                                                     
                                    
        word = word.upper()

        if word.lower() not in en_uk_dict:
            self.player_states[player_id]["word"] = ""
            self.player_states[player_id]["word_value"] = 0

            reason=f"Invalid word: {word}. Please enter a valid English word."
            self.state.set_invalid_move(reason=reason)
            return
        
                                                         
        for letter in word:
            if letter not in self.player_states[player_id]["letters"]:
                self.player_states[player_id]["word"] = ""
                self.player_states[player_id]["word_value"] = 0

                self.state.set_invalid_move(reason=f"Invalid word: {word}. You do not have the letter '{letter}'.")
                return

                                  
        word_value = sum(self.player_states[player_id]["letter_values"][self.player_states[player_id]["letters"].index(letter)] for letter in word)
        self.player_states[player_id]["word"] = word
        self.player_states[player_id]["word_value"] = word_value

        message=f"Player {player_id} chooses the word '{word}' with a value of {self.player_states[player_id]['word_value']}."
        self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                                
        self._turn_manager(next_round=False, next_player=True)

    def _check_game_done(self) -> bool:
        pass                             
        for player_id in self.player_states:
            if self.player_states[player_id]["word"] is None:
                return False
            
        return True
    
    def render_text(self) -> str:
        pass                              
        
                
                                         
           
        rendered_text = f"Round {self.round_number + 1}/{len(self.letters) + 1}\n"                        
        rendered_text += f"All letters: {self.letters}\n"
        rendered_text += f"Current letter: {self.round_letter}\n"
        rendered_text += f"Player 0: {self.player_states[0]['coins']} coins, {self.player_states[0]['letters']}\n"
        rendered_text += f"Player 1: {self.player_states[1]['coins']} coins, {self.player_states[1]['letters']}\n"
        rendered_text += f"Current player: {self.current_player}\n"
        return rendered_text
    
