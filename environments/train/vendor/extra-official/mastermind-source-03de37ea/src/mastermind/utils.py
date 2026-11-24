import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import rootutils

COLOR_MAP = {
    "red": "\033[91m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "orange": "\033[33m",
    "purple": "\033[95m",
    "pink": "\033[95m",
    "brown": "\033[33m",
    "black": "\033[90m",
    "white": "\033[97m",
}
RESET = "\033[0m"


def make_output_path(base_path: Optional[Path] = None, game_type: Optional[str] = None) -> Path:
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if base_path:
        output_path = Path(base_path) / current_datetime
    else:
        root = rootutils.find_root(search_from=__file__, indicator=".project-root")
        subfolder = game_type if game_type else "full_game"
        output_path = Path(root) / "results" / subfolder / current_datetime
    output_path.mkdir(parents=True)
    return output_path


def resolve_output_dir(base_path: Optional[Path] = None) -> Path:
    output_dir = Path(base_path) if base_path is not None else Path.cwd() / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def make_output_file_paths(base_path: Optional[Path] = None, prefix: str = "full_game") -> Tuple[Path, Path]:
    output_dir = resolve_output_dir(base_path)
    if base_path is None:
        output_dir = output_dir / prefix
        output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    results_path = output_dir / f"{prefix}_{timestamp}.jsonl"
    summary_path = output_dir / f"{prefix}_{timestamp}_summary.json"
    return results_path, summary_path


def parse_guess(turn: Dict[str, str]) -> List[str]:
    if isinstance(turn['content'], list):
        return turn['content']
                                                                   
    elif isinstance(turn['content'], str):
        matches = re.findall(r"(?:FINAL GUESS:\s*)?\[([^\]]+)\]", turn["content"])
        if matches:
                                                              
            return [item.strip().strip("'").strip('"') for item in matches[-1].split(",")]
        else:
            return []
    else:
        return []


def colorize_code(code):
    return [f"{COLOR_MAP.get(color, '')}{color}{RESET}" for color in code]


def print_summary(model, game, result, num_runs):
                                     
    labels = [
        "Model:",
        "Code Length:",
        "Number of Colors:",
        "Last Code:",
        "Max Guesses:",
        "Games Played:",
        "Games Won:",
    ]
    max_label_length = max(len(label) for label in labels)

                 
    print("=== Summary ===")
    print(f"{'Model:'.ljust(max_label_length)} {model.get_model_info()}")
    print(f"{'Code Length:'.ljust(max_label_length)} {game.code_length}")
    print(f"{'Number of Colors:'.ljust(max_label_length)} {game.num_colors}")
    print(f"{'Last Code:'.ljust(max_label_length)} {', '.join(colorize_code(game.secret_code))}")
    print(f"{'Max Guesses:'.ljust(max_label_length)} {game.max_guesses}")
    print(f"{'Games Played:'.ljust(max_label_length)} {num_runs}")
    print(f"{'Games Won:'.ljust(max_label_length)} {sum(r['solved'] for r in result)}")
