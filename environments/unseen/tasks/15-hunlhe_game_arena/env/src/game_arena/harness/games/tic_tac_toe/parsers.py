                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                   

from game_arena.harness import parsers


class TicTacToeSoftParser(parsers.SoftMoveParser):
  pass                          

  def _parse_selected_action(
      self, parser_input: parsers.TextParserInput
  ) -> str | None:
    selected_action = (
        ("" if parser_input.text.startswith("(") else "(")
        + parser_input.text.replace(" ", "")
        + ("" if parser_input.text.endswith(")") else ")")
    )
    return selected_action
