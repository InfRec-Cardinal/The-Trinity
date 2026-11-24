from typing import List, Optional, Tuple

def create_board_str(board: List[List[Tuple[int, Optional[Tuple[int, int]]]]]) -> str:
    pass                                                                                                    
    
         
                                                                  
                                                  
                                                       
    
            
                                                                 
                           
                                                
                                         
       
                           
                                    
    WORKER_SYMBOLS = {
        0: ["N1", "N2"],        
        1: ["W1", "W2"],         
        2: ["G1", "G2"]         
    }
    
                                         
    squares = {}
    for row in range(5):
        for col in range(5):
            height, worker = board[row][col]
            
                               
            if height == 4:        
                height_symbol = "4"
            else:
                height_symbol = str(height)
            
                               
            if worker is None:
                worker_symbol = "  "
            else:
                player_id, worker_num = worker
                worker_symbol = WORKER_SYMBOLS[player_id][worker_num - 1]
            
                                                                 
            squares[f"{chr(65+row)}{col+1}"] = f"{height_symbol} {worker_symbol}"

                                                                
    board_template = """
     1     2     3     4     5
  ┌─────┬─────┬─────┬─────┬─────┐
A │ {A1}│ {A2}│ {A3}│ {A4}│ {A5}│ A
  ├─────┼─────┼─────┼─────┼─────┤
B │ {B1}│ {B2}│ {B3}│ {B4}│ {B5}│ B
  ├─────┼─────┼─────┼─────┼─────┤
C │ {C1}│ {C2}│ {C3}│ {C4}│ {C5}│ C
  ├─────┼─────┼─────┼─────┼─────┤
D │ {D1}│ {D2}│ {D3}│ {D4}│ {D5}│ D
  ├─────┼─────┼─────┼─────┼─────┤
E │ {E1}│ {E2}│ {E3}│ {E4}│ {E5}│ E
  └─────┴─────┴─────┴─────┴─────┘
     1     2     3     4     5

Legend:
- Cell format is [height worker]
- Height: 0-3 for building levels, 4 for dome
- Workers: Navy(N1,N2), White(W1,W2), Grey(G1,G2)
"""
    
    return board_template.format(**squares)
