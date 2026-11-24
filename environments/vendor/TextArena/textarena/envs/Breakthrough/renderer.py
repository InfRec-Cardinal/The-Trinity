from string import ascii_lowercase
def create_board_str(board, board_size: int) -> str:
    piece_symbols = {'W': '♙', 'B': '♟'}                                    
                                                     
    squares = {}
    for row in range(board_size):
        for col in range(board_size):
            square = f"{ascii_lowercase[col]}{str(row + 1)}"
            squares[square] = piece_symbols.get(board[row][col], " ")
    files = [ascii_lowercase[i] for i in range(board_size)]                               
    header_footer = "     " + "   ".join(files)
    lines = [header_footer]             
    lines.append("   ┌" + "┬".join(["───"] * board_size) + "┐")
    for row in range(board_size - 1, -1, -1):
        rank = str(row + 1)
        line = f"{rank.rjust(2)} │"
        for col in range(board_size):
            square = f"{ascii_lowercase[col]}{rank}"
            line += f" {squares[square]} │"
        lines.append(line + f" {rank.rjust(2)}")
        if row != 0: lines.append("   ├" + "┼".join(["───"] * board_size) + "┤")
    lines.append("   └" + "┴".join(["───"] * board_size) + "┘")
    lines.append(header_footer)
    return "\n".join(lines)
