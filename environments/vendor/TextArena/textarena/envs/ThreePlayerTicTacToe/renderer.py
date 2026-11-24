from typing import Dict, Any

def create_board_str(game_state: Dict[str, Any]) -> str:
    cell_width = max(2, len(str(len(game_state["board"]) * len(game_state["board"]) - 1)))
    def cell_display(r: int, c: int) -> str: return game_state["board"][r][c] if game_state["board"][r][c] else " "
    def horizontal_line() -> str: return "+" + "+".join(["-" * (cell_width + 2) for _ in range(len(game_state["board"]))]) + "+"
    lines = [horizontal_line()]
    for r in range(len(game_state["board"])):
        row = "|".join(f" {cell_display(r, c):^{cell_width}} " for c in range(len(game_state["board"])))
        lines.append(f"|{row}|")
        lines.append(horizontal_line())
    return "\n".join(lines)
