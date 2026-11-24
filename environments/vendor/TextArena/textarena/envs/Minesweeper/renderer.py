from typing import List

def create_board_str(grid: List[List[int]], revealed: List[List[bool]], flags: List[List[bool]]) -> str:
    pass                                                                              
       
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

                   
    col_header = "    " + " ".join(f"{c:1}" for c in range(cols))

                
    top_border = "  ┌" + "──" * cols + "─┐"

                   
    board_rows = []
    for r in range(rows):
        row_content = ""
        for c in range(cols):
            if flags[r][c]:
                cell = "F"
            elif not revealed[r][c]:
                cell = "."
            elif grid[r][c] == -1:
                cell = "*"
            else:
                cell = str(grid[r][c])
            row_content += f" {cell}"
        board_rows.append(f"{r:2}│{row_content} │")

                   
    bottom_border = "  └" + "──" * cols + "─┘"

    return "\n".join([col_header, top_border, *board_rows, bottom_border])
