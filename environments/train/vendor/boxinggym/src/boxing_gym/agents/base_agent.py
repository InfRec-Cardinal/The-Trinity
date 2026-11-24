from typing import (
    Any,
    Dict,
    List, 
)

from abc import ABC, abstractmethod
                                           
MODEL_COST_PER_INPUT = {
    'gpt-4': 3e-05,
    'gpt-4o': 3e-05,
    "gpt-4o-2024-05-13": 3e-05,
    "gpt-4-1106-vision-preview": 0.03/1000,
    'gpt-3.5-turbo-0125': 3e-05,
    "gpt-4-turbo-2024-04-09": 0.01/1000,
}
                                           
MODEL_COST_PER_OUTPUT = {
    'gpt-4': 6e-05,
    "gpt-4-1106-vision-preview": 3e-05,
    'gpt-3.5-turbo-0125': 3e-05,
    "gpt-4-turbo-2024-04-09": 0.03/1000,
    "gpt-4o-2024-05-13": 3e-05,
}

class BaseAgent(ABC):
    pass                     
       
    def __init__(
        self, 
        llm: Any,
        model_id: str, 
    ) -> None:
        pass                                                         

             
                                                                                 
                                                        
           
        self.llm = llm
        self.model_id = model_id
    
    def calc_cost(
        self, 
        response
    ) -> float:
        pass                                                                                                                                                   

             
                                                                    

                
                                        
           
        model_name = response.model
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (
            MODEL_COST_PER_INPUT[model_name] * input_tokens
            + MODEL_COST_PER_OUTPUT[model_name] * output_tokens
        )
        return cost
        
    @abstractmethod
    def get_prompt(self) -> List[Dict[str, str]]:
        pass                                           
           
        raise NotImplementedError

    @abstractmethod
    def get_response(self) -> str:
        pass                                         
           
        raise NotImplementedError

    @abstractmethod 
    def run(self) -> Dict[str, Any]:
        pass                      
           
        raise NotImplementedError