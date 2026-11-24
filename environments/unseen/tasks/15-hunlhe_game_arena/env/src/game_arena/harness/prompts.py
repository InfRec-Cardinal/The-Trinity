                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                          

from game_arena.harness import prompt_templates


CORE_PROMPTS = frozenset([
    prompt_templates.WITH_LEGAL_ACTIONS,
    prompt_templates.NO_LEGAL_ACTIONS,
    prompt_templates.NO_LEGAL_ACTIONS_NO_HISTORY,
    prompt_templates.NO_LEGAL_ACTIONS_WITH_PIECE_DICT,
    prompt_templates.NO_LEGAL_ACTIONS_WITH_ASCII_BOARD,
])


RETHINK_PROMPTS = frozenset([
    prompt_templates.NO_LEGAL_ACTIONS_RETHINK_APPENDED,
    prompt_templates.NO_LEGAL_ACTIONS_WITH_ASCII_BOARD_RETHINK_APPENDED,
    prompt_templates.NO_LEGAL_ACTIONS_WITH_PIECE_DICT_RETHINK_APPENDED,
    prompt_templates.RETHINK_WITH_ENV_UNPARSABLE,
    prompt_templates.RETHINK_WITH_ENV_ILLEGAL,
    prompt_templates.RETHINK_WITH_ENV_ILLEGAL_HISTORY,
    prompt_templates.RETHINK_WITH_ENV_RULE,
])


IMAGE_TEXT_PROMPTS = frozenset([
    prompt_templates.WITH_BOARD_IMAGE,
    prompt_templates.WITH_BOARD_IMAGE_RETHINK_APPENDED,
    prompt_templates.WITH_SVG_RENDERED_IMAGE,
])
