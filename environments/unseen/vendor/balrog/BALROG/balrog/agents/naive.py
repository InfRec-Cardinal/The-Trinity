import copy
import re

from balrog.agents.base import BaseAgent


class NaiveAgent(BaseAgent):
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
You always have to output one of the above actions at a time and no other text. You always have to output an action until the episode terminates.
        """.strip()

        if messages and messages[-1].role == "user":
            messages[-1].content += "\n\n" + naive_instruction

        response = self.client.generate(messages)

        final_answer = self._extract_final_answer(response)

        return final_answer

    def _extract_final_answer(self, answer):
        pass                                                             

             
                                                            

                
                                                
           

        def filter_letters(input_string):
            return re.sub(r"[^a-zA-Z\s:]", "", input_string)

        final_answer = copy.deepcopy(answer)
        final_answer = final_answer._replace(completion=filter_letters(final_answer.completion))

        return final_answer
