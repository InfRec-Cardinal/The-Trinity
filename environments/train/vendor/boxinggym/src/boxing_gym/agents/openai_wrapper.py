from typing import List, Dict
import os

import openai
from openai import AsyncOpenAI, OpenAI

                        
class AsyncOpenAIGPT4V:
    pass                                 
       
    def __init__(
        self, 
        max_tokens=512,
        ):
        pass                                            
           
        openai.api_key = os.environ.get("GPT4_API_KEY")
        self.client = AsyncOpenAI(api_key=openai.api_key)
        self.max_tokens = max_tokens

    @property
    def llm_type(self):
        return "GPT-4 V"

    async def __call__(self, 
        messages: List[Dict[str, str]], 
        **kwargs,
    ):
        pass                               
           
        print(kwargs)
        return await self.client.chat.completions.create(
                                       
                                         
        model="gpt-4o",
        messages=messages,
        max_tokens=self.max_tokens,
        **kwargs,
    )

class OpenAIGPT4:
    pass                               
       
    def __init__(
        self, 
        max_tokens=768,
        ):
        pass                                  
           
        openai.api_key = os.environ.get("GPT4_API_KEY")
        self.client = OpenAI(api_key=openai.api_key)
        self.max_tokens = max_tokens

    @property
    def llm_type(self):
        return "GPT-4"

    def __call__(self, 
        messages: List[Dict[str, str]], 
        **kwargs,
    ):
        pass                               
           
        return self.client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=self.max_tokens,
        **kwargs,
    )

class AsyncOpenAIGPT3_5_Turbo:
    pass                               
       
    def __init__(
        self, 
        max_tokens=768,
        ):
        pass                                  
           
        openai.api_key = os.environ.get("GPT4_API_KEY")
        self.client = OpenAI(api_key=openai.api_key)
        self.max_tokens = max_tokens

    @property
    def llm_type(self):
        return "GPT-3.5"

    

class AsyncOpenAIGPT3_Turbo:
    pass                                 
       
    def __init__(
        self, 
        max_tokens=512,
        ):
        pass                                            
           
        openai.api_key = os.environ.get("GPT4_API_KEY")
        self.client = AsyncOpenAI(api_key=openai.api_key)
        self.max_tokens = max_tokens

    @property
    def llm_type(self):
        return "GPT-4 V"

    async def __call__(self, 
        messages: List[Dict[str, str]], 
        **kwargs,
    ):
        pass                               
           
        print(kwargs)
        return await self.client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=messages,
        max_tokens=self.max_tokens,
        **kwargs,
    )