import re, random, json, os, importlib.resources
from typing import Any, Dict, Optional, Tuple
import textarena as ta
from textarena.envs.TwentyQuestions.renderer import create_board_str

class TwentyQuestionsEnv(ta.Env):
    def __init__(self, hardcore: Optional[bool]=False, max_turns: int=21):
        pass             
                                                           
                                                                  
           
        self.hardcore = hardcore
        self.max_turns = max_turns

                                   
        self.gamemaster = ta.agents.OpenRouterAgent(model_name="openai/gpt-4o")
        self.gamemaster_options = ["Yes", "No", "I don't know"]
        self.gamemaster_context = None
        self.gamemaster_history = []

                            
        self.word_list = self._load_words()
        
    def _load_words(self, words_path: Optional[str] = None):
        try:
            if words_path is not None:
                                   
                if not os.path.exists(words_path): raise FileNotFoundError(f"Words data file not found at: {words_path}")
                with open(words_path, "r", encoding="utf-8") as file: word_data = json.load(file)
            else:
                                      
                with importlib.resources.files('textarena.envs.TwentyQuestions').joinpath('twenty_questions_words.json').open('r') as file:
                    word_data = json.load(file)
            category = "hardcore" if self.hardcore else "basic"
            words = word_data.get(category, [])
            if not words: raise ValueError(f"No words found for difficulty level '{category}'.")
            return words
        except Exception as e: raise FileNotFoundError(f"Failed to load words data: {str(e)}")
        
    def get_board_str(self): return create_board_str(game_state=self.state.game_state)
    def get_gamemaster_response(self, action: str) -> str:
                                   
        if self.gamemaster_context is None: raise ValueError("Gamemaster context is not set.")
        if self.gamemaster_history is None: raise ValueError("History is not set.")
        if self.gamemaster_options is None: raise ValueError("Gamemaster options are not set.")
        options = ", ".join(f"'{opt}'" for opt in self.gamemaster_options)                                    
        history = "\n".join(f"Q: {q}\nA: {a}" for q, a in self.gamemaster_history)                                 
        prompt = (f"{self.gamemaster_context}\n{history}\n\nQ: {action}\nOptions: {options}\n\nPlease respond with the most appropriate option.")                
        response = self.gamemaster(prompt).strip()                                         
                           
        if any(option.lower() in response.lower() for option in self.gamemaster_options): self.gamemaster_history.append((action, response))                         
        else: self.gamemaster_history.append((action, "I'm sorry, I don't understand. Please try asking again."))                         
        return response

    def reset(self, num_players: int, seed: Optional[int] = None):
        self.state = ta.SinglePlayerState(num_players=num_players, seed=seed, max_turns=self.max_turns)
                             
        self.game_theme = random.choice(list(self.word_list.keys()))
        self.game_word = random.choice(self.word_list[self.game_theme])
                                
        self.gamemaster_context = (
            f"You are the gamemaster for the game of '20 Questions'.\n"
            f"You will provide responses to the players' questions that guides them into guessing the target word: {self.game_word}\n"
        )
        self.state.reset(game_state={"target_word": self.game_word, "rendered_text": f"Game word: {self.game_word}"}, player_prompt_function=self._prompt)
    
    def _prompt(self, player_id: int, game_state: Dict[int, Any]) -> str:
        return (
            f"You are Player {player_id}. You are playing 20 Questions ({'Hardcore' if self.hardcore else 'Basic'}).\n"
            f"The gamemaster has chosen an object that can be one or two words. This object is related to {self.game_theme}. You have to guess this object by asking yes-or-no questions.\n"
            "The game will last for a maximum of 20 questions. After 20 questions, the gamemaster will prompt you to make a guess.\n"
            "You may ask your question in any manner, so long they are not wrapped in square brackets.\n"
            "Then, to make your final word guess, ensure that you wrap it with square brackets, e.g. [plane], [diving bell].\n"
            "As you play, the history of your questions and gamemaster's responses will be displayed."
        )
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        player_id = self.state.current_player_id
        self.state.add_observation(from_id=player_id, to_id=-1, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        action_match = re.compile(r"\[([a-zA-Z\s]+)\]").search(action)                     
        if not action_match or (action_match and '?' in action):                                                                                                          
            gamemaster_response = self.get_gamemaster_response(action)
            if "history" not in self.state.game_state: self.state.game_state["history"] = []
            self.state.game_state["history"].append((action, gamemaster_response))
            if self.state.turn == self.state.max_turns-2: gamemaster_response += "\nYou have run out of questions. What is your final guess?"
            self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=gamemaster_response, observation_type=ta.ObservationType.GAME_MESSAGE)
        else:                            
            action_text = action_match.group(1).lower()
            if self.game_word in action_text: self.state.set_outcome(reward=1, reason=f"Congratulations! You guessed the word.")
            else: self.state.set_outcome(reward=0, reason=f"Invalid guess. You guessed incorrectly.")
            self.state.game_state["rendered_text"] = f"Game word: {self.game_word}"
        if self.state.check_turn_limit() and not self.state.done: self.state.set_outcome(reward=0, reason=f"The turn limit has been reached")
        return self.state.step()
    
    
