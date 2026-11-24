import re, random
from collections import deque
from typing import Any, Dict, List, Tuple, Optional

import textarena as ta
from textarena.envs.WordLadder.renderer import create_board_str
from textarena.envs.utils.word_lists import EnglishDictionary


                                                  
import nltk
from nltk.corpus import words
nltk.download("words")


class WordLadderEnv(ta.Env):
    pass                                                         

    def __init__(self, min_distance: int=5, max_distance: int=7, max_turns: int=100):
        pass             
                                                                                        
                                                                                        
                                                                      
           
        super().__init__()
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.max_turns = max_turns
        self.word_list = words.words("en-basic")                    
        self.universal_word_list = self._load_universal_word_list()

    def _load_universal_word_list(self):
        pass                                                                  
        dictionary = EnglishDictionary(keep_proper_nouns=False, include_nltk=True)
        return dictionary.get_all_words()

    @staticmethod
    def _one_letter_diff(w1: str, w2: str) -> bool:
        pass                                                     
        return len(w1) == len(w2) and sum(a != b for a, b in zip(w1, w2)) == 1

    @staticmethod
    def _build_neighbor_map(words_of_same_len: List[str]) -> Dict[str, List[str]]:
        pass                                                                     
        word_set = set(words_of_same_len)
        neighbours: Dict[str, List[str]] = {w: [] for w in words_of_same_len}
        alphabet = "abcdefghijklmnopqrstuvwxyz"

        for word in words_of_same_len:
            for i, orig_ch in enumerate(word):
                for ch in alphabet:
                    if ch == orig_ch:
                        continue
                    candidate = word[:i] + ch + word[i + 1 :]
                    if candidate in word_set:
                        neighbours[word].append(candidate)
        return neighbours

    def _find_valid_pairs(self, neighbours: Dict[str, List[str]], min_steps: int, max_steps: int) -> List[Tuple[str, str, List[str]]]:
        pass                                                                         
                                                                              
                                                                              
                                            
           
        valid_pairs = []
        for start in neighbours.keys():
            visited = {start}
            q = deque([(start, [start])])                               

            while q:
                current, path = q.popleft()
                dist = len(path) - 1
                if dist > max_steps:
                    continue
                                                                 
                if start != current and min_steps <= dist <= max_steps:
                    valid_pairs.append((start, current, path))

                if dist == max_steps:
                    continue                                      

                for nxt in neighbours[current]:
                    if nxt not in visited:
                        visited.add(nxt)
                        q.append((nxt, path + [nxt]))
        return valid_pairs

    def _sample_start_target(self) -> Tuple[str, str]:
        pass                                                                                                                                    
        lengths_tried = []                                                                     

        while True:
                                                                            
            available_lengths = [L for L in range(3, 12) if L not in lengths_tried] or list(range(3, 12))
            length = random.choice(available_lengths)
            lengths_tried.append(length)

            bucket = [w.lower() for w in self.word_list if len(w) == length]
            if len(bucket) < 2:                                     
                continue

            neighbours = self._build_neighbor_map(bucket)
            pairs = self._find_valid_pairs(neighbours, self.min_distance, self.max_distance)
            if pairs:
                start, target, _ = random.choice(pairs)
                return start, target


    def get_board_str(self):
        return create_board_str(game_state=self.state.game_state)

    def _render_text(self) -> str:
        return f"Word Ladder History: {' -> '.join(self.history)}.  Target Word: {self.target_word}\n"

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        return (
            f"You are Player {player_id}.  Your goal is to reach the target word "
            "by changing **one letter at a time**.\n"
            f"- Start word:  **{self.start_word}**\n"
            f"- Target word: **{self.target_word}**\n"
            "Submit each move in square brackets, e.g.  `[word]`.\n"
            "History appears below as you play.  Good luck!\n"
        )

    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                   
        self.state = ta.SinglePlayerState(num_players=num_players, seed=seed, max_turns=self.max_turns)
        self.start_word, self.target_word = self._sample_start_target()
        self.current_word = self.start_word
        self.history = [self.start_word]
        game_state = {"start_word": self.start_word, "target_word": self.target_word, "rendered_text": self._render_text()}
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)

    def _is_one_alphabet_different(self, next_word: str) -> bool:
        pass                                                                             
        return self._one_letter_diff(self.current_word, next_word.lower())

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                                                            
        player_id = self.state.current_player_id
        self.state.add_observation(from_id=player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        match = re.search(r"\[([a-zA-Z]+)\]", action)
        if not match:
            reason = f"Invalid format. Wrap your word in square brackets, e.g. `[word]`."
            self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)
        else:
            next_word = match.group(1).lower()

                               
            if len(next_word) != len(self.target_word):
                reason = f"`{next_word}` has wrong length; target is {len(self.target_word)} letters."
                self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)

            elif next_word not in self.universal_word_list:
                reason = f"`{next_word}` is not a recognised English word."
                self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)

            elif not self._is_one_alphabet_different(next_word):
                reason = f"`{next_word}` is not exactly one letter different from `{self.current_word}`."
                self.state.set_invalid_move(reward=self._get_percentage_completion(), reason=reason)

            else: 
                self.current_word = next_word
                self.history.append(next_word)

                if next_word == self.target_word:
                    self.state.set_outcome(reward=1, reason=f"Congratulations! You reached the target word.")
                else:
                    self.state.add_observation(from_id=ta.GAME_ID, to_id=player_id, message=f"Nice! Keep going.\n{self._render_text()}", observation_type=ta.ObservationType.GAME_MESSAGE)

        if self.state.check_turn_limit() and not self.state.done:
            pct_complete = self._get_percentage_completion()
            reason = f"The turn limit has been reached. You reached `{self.current_word}` which shares {round(pct_complete * 100)}% of its letters with the target `{self.target_word}`."
            self.state.set_outcome(reward=pct_complete, reason=reason)

                                               
        self.state.game_state["rendered_text"] = self._render_text()
        return self.state.step()


    def _get_percentage_completion(self) -> float:
        pass                                                                                                             
        matches = sum(c1 == c2 for c1, c2 in zip(self.current_word, self.target_word))
        return matches/len(self.target_word)
