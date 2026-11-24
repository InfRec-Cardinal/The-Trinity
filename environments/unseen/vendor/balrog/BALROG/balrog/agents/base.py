class BaseAgent:
    pass                                                        

    def __init__(self, client_factory, prompt_builder):
        pass                                                        
        self.client = client_factory()
        self.prompt_builder = prompt_builder

    def act(self, obs):
        pass                                              
        raise NotImplementedError

    def update_prompt(self, observation, action):
        pass                                                    
        self.prompt_builder.update_observation(observation)
        self.prompt_builder.update_action(action)

    def reset(self):
        pass                           
        self.prompt_builder.reset()
