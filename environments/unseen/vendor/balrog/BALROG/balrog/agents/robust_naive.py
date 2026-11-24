import copy
import re

from balrog.agents.base import BaseAgent


class RobustNaiveAgent(BaseAgent):
    pass                                                                                  

    def __init__(self, client_factory, prompt_builder):
        pass                                                             
        super().__init__(client_factory, prompt_builder)
        self.client = client_factory()

    def act(self, obs, prev_action=None):
        pass                                                                     

             
                                                                   
                                                                   

                
                                                           
           
        if prev_action:
            self.prompt_builder.update_action(prev_action)

        self.prompt_builder.update_observation(obs)

        messages = self.prompt_builder.get_prompt()

                                                                     
        naive_instruction = """
You must choose exactly one of the listed actions and output it strictly in the following format:

<|ACTION|>YOUR_CHOSEN_ACTION<|END|>

Replace YOUR_CHOSEN_ACTION with the chosen action. Output no other text, explanation, or reasoning.
""".strip()

        if messages and messages[-1].role == "user":
            messages[-1].content += "\n\n" + naive_instruction

        response = self.client.generate(messages)
        final_answer = self._extract_final_answer(response)
        return final_answer

    def _extract_final_answer(self, answer):
        pass                                                                                 

             
                                                            

                
                                                                                     
           
        completion_text = answer.completion
                                                                    
        match = re.search(r"<\|ACTION\|>(.*?)<\|END\|>", completion_text, re.DOTALL)
        if match:
            extracted_action = match.group(1).strip()
        else:
                                                                                           
            extracted_action = completion_text.strip()

        final_answer = copy.deepcopy(answer)
        final_answer = final_answer._replace(completion=extracted_action)

        return final_answer
