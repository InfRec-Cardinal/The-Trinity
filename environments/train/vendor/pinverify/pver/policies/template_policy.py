from typing import Dict, Any
from omegaconf import DictConfig

                                                                            
                                               
                                         

class TemplatePolicy:
    pass                                                                   
       
    def __init__(self, cfg: DictConfig, client: Any = None):
        pass             
                                            
                                                
           
        self.cfg = cfg
        self.client = client
        
                                                                     
                                           
                                     

    def reset(self, obs: Dict[str, Any]):
        pass                                                
           
                                              
        pass

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        pass                             
           
                                             
             
        
                                     
             
        
                            
                                                           
        
                                       
                                  
                                                  
        
        action = {
            "decision": "Unsure",                        
            "nav_rel": "front",              
        }
        return action
