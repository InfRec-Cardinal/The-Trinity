from textarena.core import ActionWrapper, Env

__all__ = ["ActionFormattingWrapper"]


class ActionFormattingWrapper(ActionWrapper):
    pass                                                                         
    
                                                                                
                                                                                  
                                                                              
                                                   
    
            
                             
                                
        
                                
                                             
       

    def __init__(self, env: Env):
        pass                                               
        
             
                                               
           
        super().__init__(env)

    def action(self, action: str) -> str:
        pass                                                                
        
                                                                          
                                                                     
        
             
                                               
            
                
                                                                        
           
        action = action.strip().strip("'\"")
        
        if "[" not in action and "]" not in action:
            return f"[{action}]"
        else:
            return action