from typing import List

def create_board_str(board: List[List[str]]) -> str:
    lines = []
    for r in range(3):
        lines.append("  " + " | ".join([(board[r][c] if board[r][c] else " ") for c in range(3)]))
        if r < 2: lines.append(" ---+---+---")
    return "\n".join(lines)
