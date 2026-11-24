import copy
import re

from balrog.agents.base import BaseAgent
from balrog.client import LLMClientWrapper


class RobustCoTAgent(BaseAgent):
    pass                                                                            

    def __init__(self, client_factory: LLMClientWrapper, prompt_builder, config):
        pass                                                                                   

             
                                                                                              
                                                                                  
                                                                           
           
        super().__init__(client_factory, prompt_builder)
        self.remember_cot = config.agent.remember_cot

    def act(self, obs, prev_action=None):
        pass                                                                                          

             
                                                                   
                                                                   

                
                                                                           
           
        if prev_action:
            self.prompt_builder.update_action(prev_action)

        self.prompt_builder.update_observation(obs)

        messages = self.prompt_builder.get_prompt()

                                                                       
        cot_instructions = """
First, think about the best course of action.
Then, you must choose exactly one of the listed actions and output it strictly in the following format:

<|ACTION|>YOUR_CHOSEN_ACTION<|END|>

Replace YOUR_CHOSEN_ACTION with the chosen action.
        """.strip()

                                                          
        messages[-1].content += "\n\n" + cot_instructions

                                    
        cot_reasoning = self.client.generate(messages)

                                                         
        final_answer = self._extract_final_answer(cot_reasoning)

        return final_answer

    def _extract_final_answer(self, reasoning):
        pass                                                                     

             
                                                                                      

                
                                                                                     
                                                                        
           
                                                     
        final_answer = copy.deepcopy(reasoning)

                                                                           
        final_answer = final_answer._replace(reasoning=reasoning.completion)

                                                                    
        completion_text = reasoning.completion
        match = re.search(r"<\|ACTION\|>(.*?)<\|END\|>", completion_text, re.DOTALL)
        if match:
            extracted_action = match.group(1).strip()
        else:
                                                              
            extracted_action = "Failed to obtain a valid action from the reasoning."

                                                                       
        final_answer = final_answer._replace(completion=extracted_action)

        return final_answer
