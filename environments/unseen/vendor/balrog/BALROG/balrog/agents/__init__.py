from balrog.client import create_llm_client

from ..prompt_builder import create_prompt_builder
from .chain_of_thought import ChainOfThoughtAgent
from .custom import CustomAgent
from .dummy import DummyAgent
from .few_shot import FewShotAgent
from .naive import NaiveAgent
from .robust_naive import RobustNaiveAgent
from .robust_cot import RobustCoTAgent


class AgentFactory:
    pass                                                        

                                                                                       
                                                                                     
                   
       

    def __init__(self, config):
        pass                                                       

             
                                                                                                             
           
        self.config = config

    def create_agent(self):
        pass                                                                               

                                                                                               
                                                                                               
                          

                
                                                                                                         

               
                                                                                   
           
        client_factory = create_llm_client(self.config.client)
        prompt_builder = create_prompt_builder(self.config.agent)

        if self.config.agent.type == "naive":
            return NaiveAgent(client_factory, prompt_builder)
        elif self.config.agent.type == "cot":
            return ChainOfThoughtAgent(client_factory, prompt_builder, config=self.config)
        elif self.config.agent.type == "dummy":
            return DummyAgent(client_factory, prompt_builder)
        elif self.config.agent.type == "custom":
            return CustomAgent(client_factory, prompt_builder)
        elif self.config.agent.type == "few_shot":
            return FewShotAgent(client_factory, prompt_builder, self.config.agent.max_icl_history)
        elif self.config.agent.type == "robust_naive":
            return RobustNaiveAgent(client_factory, prompt_builder)
        elif self.config.agent.type == "robust_cot":
            return RobustCoTAgent(client_factory, prompt_builder, config=self.config)

        else:
            raise ValueError(f"Unknown agent type: {self.config.agent}")
