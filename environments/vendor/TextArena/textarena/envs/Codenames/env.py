import re, nltk, random
from nltk.corpus import words
from nltk import pos_tag
from typing import Any, Dict, Optional, Tuple, List, Union
import textarena as ta

nltk.download("words")
nltk.download('averaged_perceptron_tagger_eng')


class CodenamesEnv(ta.Env):
    def __init__(self, hardcore: Optional[bool] = False, max_turns: int = 80):
        self._load_word_list(hardcore=hardcore)
        self.max_turns = max_turns

    def _load_word_list(self, hardcore: bool = False) -> None:
        word_list = words.words("en-basic" if not hardcore else "en")
        noun_mask = [tag == "NN" for _, tag in pos_tag(word_list)]
        self.word_list = [w for w, is_noun in zip(word_list, noun_mask) if is_noun and len(w) < 8]

    def reset(self, num_players: int, seed: Optional[int] = None):
        assert num_players==4, f"The number of players must be exactly 4. Received {num_players}"
        self.state = ta.TeamMultiPlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)
        assignments = ["R"]*9 + ["B"]*8 + ["N"]*7 + ["A"]                                                                                            
        random.shuffle(assignments)                                                       
        self.board = {word: team for word, team in zip(random.sample(self.word_list, 25), assignments)}                             
        self.state.reset(game_state={"turn": 0, "team_turn": 0, "guessed_words": set(), "last_clue": None, "last_number": 0}, player_prompt_function=self._prompt)
        self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)

    def _render_player_view(self):                                                        
        view = "Codenames Words:\n"
        for word in list(self.board.keys()):
            if self.state.current_player_id in [0,2]: view += f"{word:<8} {self.board[word]} {'revealed' if word in self.state.game_state['guessed_words'] else ''}\n"                                     
            else: view += f"{word:<8} {self.board[word] if word in self.state.game_state['guessed_words'] else ''}\n"
        return view

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        prompt = (
            "You are playing Codenames, a 2v2 word deduction game. Each team (Red and Blue) has a Spymaster and an Operative.\nRules:\n"
            "1. The Spymaster gives a one-word clue + number (e.g., '[wind 2]') based on the team's secret words (the clue may not contain any of the words on the board).\n"
            "2. The Operative guesses up to N+1 words (e.g., '[breeze]') based on the clue. They can also '[pass]'.\n"
            "3. Avoid guessing opponent words, neutral words (N), or the Assassin (A), which causes instant loss.\n"
            "4. First team to guess all their words wins.\n\n"
        )
        if player_id in [0, 2]: return prompt + f"You are Player {player_id}, the Spymaster for {'Red' if player_id == 0 else 'Blue'} team. Give a one-word clue and number."
        else:                   return prompt + f"You are Player {player_id}, the Operative for {'Red' if player_id == 1 else 'Blue'} team. Guess words based on the clue."

    def _rotate_player_by_logic(self, done_guessing: bool=False, skip_guessing: bool=False):
        match self.state.current_player_id:
            case 0: next_player_id = 2 if skip_guessing else 1
            case 2: next_player_id = 0 if skip_guessing else 3
            case 1: next_player_id = 2 if done_guessing else 1
            case 3: next_player_id = 0 if done_guessing else 3
        self.state.manually_set_current_player_id(new_player_id=next_player_id)

    def _resolve_game(self) -> None:
        red_correct  = sum(1 for word, team in self.board.items() if team == "R" and word in self.state.game_state["guessed_words"])
        blue_correct = sum(1 for word, team in self.board.items() if team == "B" and word in self.state.game_state["guessed_words"])
        if red_correct > blue_correct:      self.state.set_winners(player_ids=[0, 1], reason=f"Move limit reached (80). Red revealed {red_correct} vs Blue {blue_correct}.")
        elif blue_correct > red_correct:    self.state.set_winners(player_ids=[2, 3], reason=f"Move limit reached (80). Blue revealed {blue_correct} vs Red {red_correct}.")
        else:                               self.state.set_draw(reason="Move limit reached (80) with equal score: draw.")

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        player_id = self.state.current_player_id
        current_team = "R" if player_id < 2 else "B"
        self.state.add_observation(from_id=player_id, to_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)                              

        if self.state.current_player_id in [0, 2]:                         
            match = re.search(r"\[(\w+)\s+(\d+)\]", action)
            if match:
                word = match.group(1)                     
                number = int(match.group(2))                                     

                                                                                 
                if any(word in board_word or board_word in word for board_word in self.board.keys()):
                                                                                                   
                    self.state.set_winners(player_ids=[0, 1] if current_team == "B" else [2, 3], reason=f"Player {player_id} mentioned a clue that is a subset/ exact match of words on the board.")
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()

                                                
                self.state.game_state["last_clue"] = word
                self.state.game_state["last_number"] = number
                self.state.game_state["remaining_guesses"] = number + 1                                        
                self.state.add_observation(message=f"Spymaster of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, submitted [{word} {number}].", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                self._rotate_player_by_logic() 
                self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                if self.state.check_turn_limit(): self._resolve_game()
                return self.state.step()
            else:
                self.state.add_observation(message=f"Spymaster of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, did not provide a valid clue. The teams turn will be skipped.", observation_type=ta.ObservationType.GAME_MESSAGE)
                self._rotate_player_by_logic(skip_guessing=True); self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                if self.state.check_turn_limit(): self._resolve_game()
                return self.state.step()
            
        else:                                       
            match = re.search(r"\[(\w+)\]", action)

            if match: 
                guessed_word = match.group(1).lower()

                if guessed_word == "pass":
                    self._rotate_player_by_logic(done_guessing=True); self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()

                                                              
                if guessed_word not in self.board or guessed_word in self.state.game_state["guessed_words"]:
                    self.state.add_observation(message=f"Operator of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, did not provide a valid guess. The teams turn will be skipped.", observation_type=ta.ObservationType.GAME_MESSAGE)
                    self._rotate_player_by_logic(done_guessing=True); self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()

                self.state.game_state["guessed_words"].add(guessed_word)

                                                               
                if self.board[guessed_word] == "A":                      
                    self.state.set_winners(player_ids=[2, 3] if current_team == "R" else [0, 1], reason=f"Player {player_id} selected the assassin word.")
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()
                
                                                     
                elif self.board[guessed_word] == current_team:
                                                                        
                    if all(word in self.state.game_state["guessed_words"] for word, team in self.board.items() if team == current_team):
                        self.state.set_winners(player_ids=[0, 1] if current_team == "R" else [2, 3], reason=f"Player {player_id} guessed all their team's words!")
                        return self.state.step()
                    self.state.add_observation(message=f"Operator of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, correctly guessed [{guessed_word}].", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.game_state["remaining_guesses"] -= 1
                    if self.state.game_state["remaining_guesses"] <= 0:  self._rotate_player_by_logic(done_guessing=True); self.state.game_state["remaining_guesses"] = 0 
                    self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()
                    
                                                                                         
                else:                                                       
                    opponent_team = "B" if current_team == "R" else "R"
                    if all(word in self.state.game_state["guessed_words"] for word, team in self.board.items() if team == opponent_team):
                        self.state.set_winners(player_ids=[0, 1] if opponent_team == "R" else [2, 3], reason=f"Player {player_id} guessed the opponent team's last word!")
                        return self.state.step()
                    opponent_team_name = "Red" if opponent_team == "R" else "Blue"
                    self.state.add_observation(message=f"Operator of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, wrongly guessed [{guessed_word}]. It is a {opponent_team_name + ' Team' if self.board[guessed_word]==opponent_team else 'Neutral'} word.", observation_type=ta.ObservationType.GAME_MESSAGE)
                    self.state.game_state["remaining_guesses"] = 0
                    if self.state.game_state["remaining_guesses"] <= 0:  self._rotate_player_by_logic(done_guessing=True); self.state.game_state["remaining_guesses"] = 0 
                    self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                    if self.state.check_turn_limit(): self._resolve_game()
                    return self.state.step()
            else:
                self.state.add_observation(message=f"Operator of {'Red' if current_team=='R' else 'Blue'} team, Player {player_id}, did not provide a valid guess. The teams turn will be skipped.", observation_type=ta.ObservationType.GAME_MESSAGE)
                self._rotate_player_by_logic(done_guessing=True); self.state.add_observation(to_id=self.state.current_player_id, message=self._render_player_view(), observation_type=ta.ObservationType.GAME_BOARD)
                if self.state.check_turn_limit(): self._resolve_game()
                return self.state.step()

  
