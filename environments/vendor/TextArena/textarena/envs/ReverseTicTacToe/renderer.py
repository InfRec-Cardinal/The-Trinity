from typing import List

def create_board_str(board: List[List[str]]) -> str:
    lines = []
    for r in range(3):
        row = []
        for c in range(3):
            val = board[r][c]
            row.append(val if val else " ")
        lines.append("  " + " | ".join(row))
        if r < 2: lines.append(" ---+---+---")
    return "\n".join(lines)
