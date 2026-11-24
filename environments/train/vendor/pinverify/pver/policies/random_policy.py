import random

class RandomPolicy:
    def __init__(self, cfg, client=None):
        self.cfg = cfg
                                                                            
        
        self.single_view = (cfg.env.max_steps == 1)
        
    def reset(self, obs):
        pass

    def act(self, obs):
                      
                                                   
        
        choices = ["Yes", "No"]
        if not self.single_view:
             choices.append("Unsure")
             
        decision = random.choice(choices)
        
        action = {"decision": decision}
        
        if decision == "Unsure":
                                       
                                                                      
                                                        
                                                                    
                                                                           
                                                  
            
            nav_opts = ["front", "front-left", "front-right", "back", "back-left", "back-right"]
            action["nav_rel"] = random.choice(nav_opts)
            
        return action
