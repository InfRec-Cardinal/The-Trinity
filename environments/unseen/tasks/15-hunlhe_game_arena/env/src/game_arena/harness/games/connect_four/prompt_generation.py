                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                  

from . import prompt_templates


def generate_prompt(
    rows: int,
    columns: int,
    in_a_row: int,
    visual_board_state: str,
    player_name: str,
) -> str:
  pass                                         

       
                                          
                                                
                                                   
                                                                            
                                                              

          
                              
     
  return prompt_templates.CONNECT_X_PROMPT.format(
      rows=rows,
      columns=columns,
      in_a_row=in_a_row,
      visual_board_state=visual_board_state,
      player_name=player_name,
      max_column_index=columns - 1,
      rethink_prompt="",
  )
