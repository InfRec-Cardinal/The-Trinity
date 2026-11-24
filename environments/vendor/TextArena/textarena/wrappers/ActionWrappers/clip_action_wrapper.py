from textarena.core import ActionWrapper, Env

__all__ = ["ClipWordsActionWrapper", "ClipCharactersActionWrapper"]


class ClipWordsActionWrapper(ActionWrapper):
    pass                                                                    

                                                                                                   
       

    def __init__(self, env: Env, max_num_words: int):
        pass                                              

             
                                               
                                                                                  
           
        super().__init__(env)
        self.max_num_words = max_num_words

    def action(self, action: str) -> str:
        pass                                                            

             
                                              

                
                                      
           
        word_list = action.split()
        if len(word_list) <= self.max_num_words:
            return action
        else:
                                 
            return " ".join(word_list[: self.max_num_words])


class ClipCharactersActionWrapper(ActionWrapper):
    pass                                                                         

                                                                                                        
       

    def __init__(self, env: Env, max_num_characters: int=1_000):
        pass                                                   

             
                                               
                                                                                            
           
        super().__init__(env)
        self.max_num_characters = max_num_characters

    def action(self, action: str) -> str:
        pass                                                                 

             
                                              

                
                                      
           
        if len(action) <= self.max_num_characters:
            return action
        else:
                                 
            return action[-self.max_num_characters:]
