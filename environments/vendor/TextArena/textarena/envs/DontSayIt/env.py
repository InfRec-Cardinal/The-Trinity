import nltk, random 
nltk.download(["words", "averaged_perceptron_tagger_eng"])
from typing import Any, Dict, Optional, Tuple

import textarena as ta


class DontSayItEnv(ta.Env):
    def __init__(self, max_turns: int, hardcore: Optional[bool] = False):
        pass             
                                                                                                          
                                                                                    
           
        all_words = nltk.corpus.words.words("en") if hardcore else nltk.corpus.words.words("en-basic")
        self.word_list = [word for word in all_words if nltk.pos_tag([word])[0][1] in ["NN"]]                                 
        self.max_turns = max_turns

    def reset(self, num_players: int, seed: Optional[int]=None):
        self.state = ta.TwoPlayerState(num_players=num_players, max_turns=self.max_turns, seed=seed)
        self.state.reset(game_state={"target_words":{0:random.choice(self.word_list), 1:random.choice(self.word_list)}}, player_prompt_function=self._generate_player_prompt)

    def _generate_player_prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        return (
            f"You are Player {player_id} in a game of DontSayIt.\nYour secret word is: '{game_state['target_words'][player_id]}'.\n"
            "Your goal is to get the other player to say your secret word before you say theirs.\n"
            "You can converse freely, but try to be subtle to avoid making it obvious.\n On your turn, simply type your message.\n"
            f"The game lasts for {self.state.max_turns} turns in total.\n"
        )

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.state.add_observation(from_id=self.state.current_player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        if self.state.game_state["target_words"][1-self.state.current_player_id].lower() in action.lower(): self.state.set_winner(player_id=1-self.state.current_player_id, reason=f"Player {self.state.current_player_id} mentioned the opponent's secret word.")            
        elif self.state.check_turn_limit(): self.state.set_draw(reason="The turn limit has been reached")
        return self.state.step()
