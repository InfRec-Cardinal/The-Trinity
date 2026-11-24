def create_board_str(game_state: dict) -> str:
    board = game_state["board"]

                               
    symbol_map = {
        "r": "🔴", "R": "🟥",
        "b": "⚫", "B": "⬛",
        ".": "  "
    }

    lines = []
    
                   
    header = "    " + "    ".join(str(c) for c in range(8))
    lines.append(header)
    
                
    lines.append("  ┌" + "────┬" * 7 + "────┐")

    for r in range(8):
        row = board[r]
        row_symbols = " │ ".join(symbol_map.get(cell, cell) for cell in row)
        lines.append(f"{r} │ {row_symbols} │")
        if r < 7:
            lines.append("  ├" + "────┼" * 7 + "────┤")
        else:
            lines.append("  └" + "────┴" * 7 + "────┘")

    return "\n".join(lines)
