import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from tqdm import tqdm

from mastermind.game import Mastermind
from mastermind.models import ChatHistory, LanguageModel
from mastermind.solvers import Solver
from mastermind.utils import COLOR_MAP, RESET, make_output_file_paths, parse_guess

GameResult = Dict[str, str]
Guess = List[str]
Scores = Tuple[int, int]
GuessHistory = List[Tuple[Guess, Scores]]
ProgressHistory = List[int]

GREEN = COLOR_MAP["green"]
RED = COLOR_MAP["red"]
YELLOW = COLOR_MAP["yellow"]


class GameState(Enum):
    ONGOING = auto()
    WON = auto()
    LOST = auto()


class Evaluator:
    def __init__(
        self,
        game: Mastermind,
        model: Union[LanguageModel, Solver],
        use_cot: bool = False,
        use_fewshot_example: bool = False,
        compute_progress: bool = False,
    ):
        self.game = game
        self.model = model
        self.attempts = 0
        self.state = GameState.ONGOING
        self.use_cot = use_cot
        self.use_fewshot_example = use_fewshot_example
        self.compute_progress = compute_progress

    def _init_chat_history(self) -> ChatHistory:
        return [
            {"role": "system", "content": "You are a player in a Mastermind game. Your role is to guess the secret code. You must always respond with a guess."},
            {"role": "user", "content": f"{self._init_instruction()}\n\n{self._first_guess_template()}"},
        ]

    def _init_instruction(self) -> str:
        task_instruction = (
            f"You are playing Mastermind as the guesser. A secret color code has been chosen and your goal is to figure it out through a series of guesses.\n\n"
            f"Game rules:\n"
            f"- The secret code consists of {self.game.code_length} colors. Duplicates are allowed.\n"
            f"- The only allowed colors are: {self.game.possible_colors}.\n"
            f"- You have at most {self.game.max_guesses} guesses to find the code.\n"
            f"- After each guess you will receive feedback:\n"
            f"  1. How many colors are correct AND in the correct position.\n"
            f"  2. How many colors are correct but in the WRONG position.\n"
            f"- A color is only counted once in the feedback, with exact matches taking priority.\n\n"
            f"How to respond:\n"
            f"- You must always make a guess. Never ask the user to guess for you.\n"
            f"- End every response with your guess on its own line in this exact format:\n"
            f"  FINAL GUESS: ['color1', 'color2', ...]\n"
            f"- Only use colors from the allowed list above.\n"
            f"- Use the feedback from previous guesses to narrow down the secret code.\n"
            f"{self._example_template()}"
        )
        return task_instruction

    def _example_template(self) -> str:
        sample_guess = random.sample(self.game.possible_colors, k=self.game.code_length)
        if self.use_fewshot_example:
            example = (
                "\n### Example game (Secret Code: ['white', 'green', 'red', 'brown']):\n"
                "<User> The game has started. Make your first guess.\n"
                "<Assistant> I'll start with a spread of colors.\nFINAL GUESS: ['yellow', 'black', 'green', 'brown']\n"
                "<User> Feedback: Correct color and position: 1. Correct color but wrong position: 1.\nWhat is your next guess?\n"
                "<Assistant> One color is in the right spot and one is present but misplaced. I'll adjust.\nFINAL GUESS: ['white', 'brown', 'green', 'brown']\n"
                "<User> Feedback: Correct color and position: 2. Correct color but wrong position: 1.\nWhat is your next guess?\n"
                "<Assistant> Getting closer. Two exact matches now.\nFINAL GUESS: ['white', 'green', 'white', 'brown']\n"
                "<User> Feedback: Correct color and position: 3. Correct color but wrong position: 0.\nWhat is your next guess?\n"
                "<Assistant> Three exact matches. The third position must be 'red'.\nFINAL GUESS: ['white', 'green', 'red', 'brown']\n"
                "<User> Feedback: Correct color and position: 4. Correct color but wrong position: 0.\nYou solved it!\n"
                "###\n"
            )
        else:
            example = (
                "\n### Example interaction:\n"
                "<User> The game has started. Make your first guess.\n"
                f"<Assistant> FINAL GUESS: {sample_guess}\n"
                f"<User> Feedback: Correct color and position: 1. Correct color but wrong position: 1.\nWhat is your next guess?\n"
                f"<Assistant> One color is in the right spot and one is present but misplaced. I'll adjust my guess.\nFINAL GUESS: {sample_guess}\n"
                "###\n"
            )
        return example

    def _first_guess_template(self) -> str:
        return "The game has started. Make your first guess."

    def _guess_template(self) -> str:
        if self.use_cot:
            return "Analyze the feedback so far step-by-step (at most ~400 words), then give your next guess."
        return "What is your next guess? Keep your reasoning to at most ~400 words."

    def _run_single_game(self, num_game: int, run_timestamp: Optional[str], compute_progress: bool = False) -> GameResult:
        game = self.game.clone()
        chat_history: ChatHistory = self._init_chat_history()
        guess_history: GuessHistory = []
        turn_history = []
        state = GameState.ONGOING
        attempts = 0

        total_guesses_bar = tqdm(
            total=game.max_guesses, desc=f"{YELLOW}[Game #{num_game}]{RESET} Attempts", unit="attempt"
        )

        while state == GameState.ONGOING:
            chat_history = self.model(chat_history)
            guess = parse_guess(chat_history[-1])
            exact_matches, partial_matches, hint = game.evaluate(guess)
            guess_history.append((guess, (exact_matches, partial_matches)))
            turn_history.append(
                {
                    "attempt": attempts + 1,
                    "guess": guess,
                    "exact_matches": exact_matches,
                    "partial_matches": partial_matches,
                    "feedback": hint,
                    "assistant_message": chat_history[-1]["content"],
                }
            )

            attempts += 1
            total_guesses_bar.update(1)

            if exact_matches == game.code_length:
                total_guesses_bar.desc = f"{GREEN}[Game #{num_game}] Game Solved{RESET}"
                total_guesses_bar.refresh()
                state = GameState.WON
                total_guesses_bar.close()
            elif attempts >= game.max_guesses:
                total_guesses_bar.desc = f"{RED}[Game #{num_game}] Game Over{RESET}"
                total_guesses_bar.refresh()
                state = GameState.LOST
                total_guesses_bar.close()
            else:
                chat_history.append({"role": "user", "content": f"Feedback: {hint}\n{self._guess_template()}"})

        progress_history = []
        if compute_progress:
            progress_history = self.progress(guess_history, game)

        return {
            "run_timestamp": run_timestamp,
            "game_index": num_game,
            "chat_history": chat_history,
            "turn_history": turn_history,
            "guess_history": guess_history,
            "progress_history": progress_history,
            "valid": True if not attempts == 1 else False,
            "solved": False if state == GameState.LOST else True,
            "num_guesses": attempts,
            "game": game.to_json(),
            "model": self.model.get_model_info(),
        }

    def run(
        self,
        num_games: int = 1,
        num_parallel: int = 1,
        save_results: bool = False,
        save_path: Optional[Path] = None,
        compute_progress: bool = False,
    ) -> List[GameResult]:

        results = []
        results_lock = threading.Lock()
        results_file = None
        summary_file = None
        run_timestamp = None
        if save_results:
            results_file, summary_file = make_output_file_paths(save_path, prefix="full_game")
            run_timestamp = results_file.stem.removeprefix("full_game_")

        def run_and_collect(num_game: int):
            try:
                result = self._run_single_game(num_game, run_timestamp, compute_progress=compute_progress)
                with results_lock:
                    results.append(result)
                    if save_results:
                        with open(results_file, "a") as f:
                            f.write(json.dumps(result) + "\n")
                        with open(summary_file, "w") as f:
                            json.dump(
                                {
                                    "run_timestamp": run_timestamp,
                                    "model": self.model.get_model_info(),
                                    "game_type": "full_game",
                                    "code_length": self.game.code_length,
                                    "num_colors": len(self.game.possible_colors),
                                    "num_games_requested": num_games,
                                    "num_games_completed": len(results),
                                    "games_solved": sum(r["solved"] for r in results),
                                    "save_results": True,
                                    "results_file": str(results_file),
                                },
                                f,
                            )
            except Exception as e:
                print(f"Error in game #{num_game}: {e}")

        with ThreadPoolExecutor(max_workers=num_parallel) as executor:
            futures = [executor.submit(run_and_collect, i) for i in range(num_games)]
            for future in as_completed(futures):
                future.result()

        results.sort(key=lambda r: r["game_index"])
        return results

    def progress(self, guess_history: GuessHistory, game: Optional["Mastermind"] = None) -> ProgressHistory:
        g = game or self.game
                                                                              
                                                                              
                                                                              
        remaining_states = list(product(g.possible_colors, repeat=g.code_length))
        progress_history = [len(remaining_states)]
        for i in range(1, len(guess_history)):
            guess, feedback = guess_history[i - 1]
            remaining_states = [
                possible_code for possible_code in remaining_states
                if g.evaluate_guess(guess, possible_code) == feedback
            ]
            progress_history.append(len(remaining_states))
        return progress_history

    def reset(self):
        self.game.reset()
        self.state = GameState.ONGOING
        self.attempts = 0
        if isinstance(self.model, Solver):
            self.model.reset()
