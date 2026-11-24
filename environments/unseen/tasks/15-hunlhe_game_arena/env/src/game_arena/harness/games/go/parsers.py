                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                          

from game_arena.harness import parsers


class GoSoftParser(parsers.SoftMoveParser):
  pass                          

  def _parse_selected_action(
      self, parser_input: parsers.TextParserInput
  ) -> str | None:
    selected_action = (
        " " + parser_input.text.strip("(),").replace(",", "").lower()
    )
    return selected_action
