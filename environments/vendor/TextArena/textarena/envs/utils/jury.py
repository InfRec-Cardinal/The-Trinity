import random
from typing import Optional, List, Dict

import textarena as ta

default_models = [
    "amazon/nova-pro-v1",
    "openai/gpt-4o-mini",
    "anthropic/claude-3-haiku",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-405b-instruct",
    "qwen/qwen-turbo",
    "minimax/minimax-01",
    "microsoft/phi-4",
    "deepseek/deepseek-chat"
]

JUROR_SYSTEM_PROMPT = (
    "You are a fair and impartial juror. You will be given a context and a list of "
    "possible options. Please select the single most appropriate option from the list, "
    "responding with only that exact option name (e.g., 'Affirmative', 'Negative', etc.)."
)

class OpenRouterJury:
    pass                                                                                         

               
                                                                                
                                                                       
                                                                    
       

    def __init__(self, options: List[str], jury_size: int=5, model_names: Optional[List[str]]=default_models):
        pass                                              

             
                                                                                 
                                                  
                                                                                    
                                             
           
        self.available_models = model_names if model_names is not None else default_models
        self.jury = []
        for _ in range(jury_size):
            model_name = random.choice(self.available_models)
            juror = ta.agents.OpenRouterAgent(model_name=model_name, system_prompt=JUROR_SYSTEM_PROMPT)
            self.jury.append(juror)
        self.options = options

    def _create_juror_prompt(self, context: str) -> str:
        pass                                                          

             
                                                                      

                
                                                                                       
           
        options_formatted = ", ".join([f"'{option}'" for option in self.options])
        prompt = (
            f"Based on the following context, choose the single best option.\n\n"
            f"Context: {context}\n\n"
            f"Options: {options_formatted}\n\n"
            f"Please respond with only one of the above options."
        )
        return prompt

    def evaluate(self, context: str) -> Dict[str, float]:
        pass                                                                   

             
                                                                  

                
                                                                                            
                                                                                           
                                                  
           
        result_dict = {option: 0 for option in self.options}
        num_casted_votes = 0

        jury_prompt = self._create_juror_prompt(context=context)

        for juror in self.jury:
            try:
                judgement = juror(jury_prompt)
                chosen_option = None
                for option in self.options:
                    if option.lower() in judgement.lower():
                        chosen_option = option
                        break

                if chosen_option:
                    result_dict[chosen_option] += 1
                    num_casted_votes += 1
                                                                      
            except Exception as exc:
                pass

                   
        if num_casted_votes > 0:
            for key in result_dict.keys():
                result_dict[key] /= num_casted_votes
                                                                            

        return result_dict
