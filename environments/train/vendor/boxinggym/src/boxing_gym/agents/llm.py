from typing import (
    Any,
    Dict,
    List, 
)

import asyncio

from src.boxing_gym.agents.base_agent import BaseAgent

                                                                        
                                                 
class LLMAgent(BaseAgent):
    pass                                                             
       
    def __init__(
        self, 
        llm: Any,
        model_id: str, 
        use_vision: bool,
        batch_mode: bool=True,
        warm_start_examples: List = [],
        logger=None,
        vision_only=False,
                      
        **model_args,
    ) -> None:
        super().__init__(llm=llm, model_id=model_id)
        self.model_args = model_args
        self.all_responses = []
        self.total_inference_cost = 0

        self.batch_mode = batch_mode

        self.warm_start_examples = warm_start_examples

        self.use_vision = use_vision 

        self.vision_only = vision_only 

        self.logger = logger
        self.messages_all = []

    def get_prompt(
        self, 
        system_message: str, 
        user_message: str, 
        data_image: str, 
        incontext_info: List):
        raise NotImplementedError()

    async def get_response(
        self, 
        messages: List[Dict[str, str]],
        n: int = 1, 
        temperature: float = 0.7,
    ) -> Any:
        pass                                        
           
        self.model_args['temperature'] = temperature
        self.model_args['n'] = n

                                        
        self.logger.info(f"running with temperature: {self.model_args['temperature']}, n = {self.model_args['n']}")
        return await self.llm(messages=messages, **self.model_args)
    
    async def run(
        self, 
        expertise: str,
        user_message: str,
        data_image: str, 
        incontext_info: List,
        n: int = 1, 
        temperature: float = 0.7,
    ) -> Dict[str, Any]:

        
        pass                  

             
                                                      
                                                  

                
                                                                                                    
           

                        
        messages = self.get_prompt(
            system_message=expertise, 
            user_message=user_message, 
            data_image=data_image, 
            n=n,
            incontext_info=incontext_info)

                                                   

        self.messages_all.append(messages)

                          
        response = await self.get_response(messages=messages, n=n, temperature=temperature)

                                                            

                    
        cost = self.calc_cost(response=response)
        print(f"Cost for running: {cost}")
        self.total_inference_cost += cost

        if self.batch_mode:
                                            
            full_response = {
                'response': response,
                'response_str': response.choices[0].message.content,
                'cost': cost
            }
                                                  
            
            self.all_responses.append(full_response)
                                    
            return full_response['response_str']
        else:
            return [choice.message.content for choice in response.choices]
    
    async def batch_prompt_sync(
        self, 
        expertise: str, 
        messages: List[str],
        incontext_info: List,
        data_image: str,
        n: int = 1,
        temperature: float = 0.7,
    ) -> List[str]:
        pass                                           

             
                                                      
                                                         

                
                                                                    
           
        responses = [self.run(expertise=expertise, 
                              user_message=message, 
                              incontext_info=incontext_info,
                              data_image=data_image,
                              n=n,
                              temperature=temperature) for message in messages]
        return await asyncio.gather(*responses)

    def batch_prompt(
        self, 
        expertise: str, 
        messages: List[str], 
        incontext_info: List,
        data_image: str,
        temperature: float = 0.7,
        n: int = 1,
    ) -> List[str]:
        pass
                                             

             
                                                      
                                                         
                                                                      

                
                                                                    
           
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError(f"Loop is already running.")
        return loop.run_until_complete(self.batch_prompt_sync(
            expertise=expertise, 
            messages=messages, 
            temperature=temperature, 
            data_image=data_image,
            n=n,
            incontext_info=incontext_info
            ))

class ModelCriticismLLMAgent(LLMAgent):
    def add_incontext_examples(self, messages: List[str], incontext_info: List):
      for i, results in enumerate(incontext_info):
        messages.append(
            {
                "role": "user", 
                "content": [
                {"type": "text", "text": f"""
                    1. Program {i}: \n {results["test_fn"]}  \n 
                    2. Bayesian p val: \n {results["bayesian_pval_rescaled"]}. \n
                    2. Explanation: \n {results["t_data"]['test_statistic_explanation']}. \n
                """
                },
                ]
            }

        )

        self.logger.info(messages[-1])
        if "fig" in results:
            messages.append(
                {
                    "role": "user", 
                    "content": [
                    {"type": "text", "text": f"""
                        1. Program {i}: \n {results["discrepancy_fn"]}  \n 
                        2. Image: \n 
                    """},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{results['fig']}"}},
                    ]
                }
            )

    def get_prompt(
        self,
        system_message: str,
        user_message: str,
        data_image: str, 
        n: int,
        incontext_info: List = [],
    ) -> List[Dict[str, str]]:
        pass                                            
           
        messages = []
        if data_image is None:
            system_msg_dict = {
                "role": "system", 
                "content": system_message
            }
            
               
                                 
                                    
                             
                   
                                                               
                                                                                     
                                                                                                         
                   
               

        messages.append(system_msg_dict)

        messages.append({"role": "user", "content": user_message})

        self.logger.info(f"data_image: {data_image}")
        
        if len(incontext_info) > 0: 
          self.add_incontext_examples(messages=messages, incontext_info=incontext_info)
        return messages

class StanProposalLLMAgent(LLMAgent):

    def add_incontext_examples(self, messages: List[str], incontext_info: List):

                                  
      if len(self.warm_start_examples) > 0: 
        for results in self.warm_start_examples:
          if self.vision_only:
            raise Exception("Vision only is not supported for StanProposalLLMAgent if warm-starting")
          else:
            messages.append(
                {
                    "role": "user", 
                    "content": 
                    [
                        {"type": "text", "text": f"""
                        Here is the previous program: \n
                        1. Program: {results['str_prob_prog']}\n 
                        2. The LOO score is: {results['loo']}. \n
                        2. The summary stats are: {results['summary_stats_df']}. \n
                        """
                        },
                    ]
                }
            )
                                                                                          
          self.logger.info(f"Warm start: {messages[-1]['content']}")
           

      if len(incontext_info) > 0:
        messages.append(
            {
                "role": "user", 
                "content": f"""
                  Here's a list of the best programs in descending order.
                """
            }
        )
        for i, results in enumerate(incontext_info):
          if self.vision_only:
            messages.append(
                {
                    "role": "user", 
                    "content": [
                    {"type": "text", "text": f"""
                        1. Program {i}: \n {results["str_prob_prog"]}  \n 
                        2. The LOO score: \n {results["loo"]}. \n
                        3. A plot of the posterior predictive against the true data: \n
                    """
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{results['posterior_plot']}"}}
                    ]
                }
            )
            self.logger.info(f"Exemplar: {messages[-1]['content'][0]}")
          else:
            messages.append(
                {
                    "role": "user", 
                    "content": f"""
                        1. Program {i}: \n {results["str_prob_prog"]}  \n 
                        2. The LOO score: \n {results["loo"]}. \n
                    """
                                                                                                          
                }
            )
            self.logger.info(f"Exemplar: {messages[-1]['content']}")

    def get_prompt(
        self,
        system_message: str,
        user_message: str,
        data_image: str, 
        n: int,
        incontext_info: List = [],
    ) -> List[Dict[str, str]]:
        pass                                            
           
        messages = []
        if data_image is None:
            system_msg_dict = {
                "role": "system", 
                "content": system_message
            }
            
        else:
            system_msg_dict = {
                "role": "system", 
                "content": 
                [
                    {"type": "text", "text": system_message},
                    {"type": "text", "text": "Here is a plot of the data itself. Use the properties in the plot to inform your modeling choices."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data_image}"}}
                ]
            }
            print(f"data image is not None!")

        messages.append(system_msg_dict)
        self.logger.info(f"system_msg_dict: {messages[-1]['content']}")
        messages.append({"role": "user", "content": user_message})
        if (len(incontext_info) > 0) or len(self.warm_start_examples) > 0: 
          self.add_incontext_examples(messages=messages, incontext_info=incontext_info)
            
        return messages

class StanCriticLLMAgent(LLMAgent):
    def add_incontext_examples(self, messages: List[str], incontext_info: List):
      for i, results in enumerate(incontext_info):
        if self.vision_only:
          messages.append(
              {
                  "role": "user", 
                  "content": [
                  {"type": "text", "text": f"""
                      1. Program {i}: \n {results["str_prob_prog"]}  \n 
                      2. The LOO score: \n {results["loo"]}. \n
                      3. A plot of the posterior predictive against the true data: \n
                  """
                  },
                  {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{results['posterior_plot']}"}}
                  ]
              }
          )
        else:
          messages.append(
              {
                  "role": "user", 
                  "content": f"""
                      1. Program: \n {results["str_prob_prog"]}
                      2. The LOO score: {results["loo"]}. \n
                      3. The summary stats from posterior predictive: {results["summary_stats"]} \n
                  """
              }
          )
        self.logger.info(f"Exemplar: {messages[-1]['content']}")

    def get_prompt(
        self,
        system_message: str,
        user_message: str,
        data_image: str, 
        n: int,
        incontext_info: List = [],
    ) -> List[Dict[str, str]]:
        pass                                            
           
        messages = []
        if data_image is None:
            system_msg_dict = {
                "role": "system", 
                "content": system_message
            }
        else:
            system_msg_dict = {
                "role": "system", 
                "content": 
                [
                    {"type": "text", "text": system_message},
                    {"type": "text", "text": "Here is a plot of the data itself. Use the properties in the plot to inform your criticism."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data_image}"}}
                ]
            }

        messages.append(system_msg_dict)
        messages.append({"role": "user", "content": user_message})

        if len(incontext_info) > 0: 
          self.add_incontext_examples(messages=messages, incontext_info=incontext_info)
        return messages