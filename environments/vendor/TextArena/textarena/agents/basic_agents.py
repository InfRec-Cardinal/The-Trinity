import asyncio
from abc import ABC, abstractmethod
import os, time
from typing import Optional, Tuple

from textarena.core import Agent
import textarena as ta 

__all__ = ["HumanAgent", "OpenRouterAgent", "GeminiAgent", "OpenAIAgent", "HFLocalAgent", "CerebrasAgent", "AWSBedrockAgent", "AnthropicAgent", "GroqAgent", "OllamaAgent", "LlamaCppAgent"]
STANDARD_GAME_PROMPT = "You are a competitive game player. Make sure you read the game instructions carefully, and always follow the required format."
    

class HumanAgent(Agent):
    pass                                                                    
    def __init__(self):
        super().__init__()

    def __call__(self, observation: str) -> str:
        pass                                                      
        
             
                                                           
            
                
                                                     
           
        print("\n\n+++ +++ +++")                                                                     
        return input(f"Current observations: {observation}\nPlease enter the action: ")


class OpenRouterAgent(Agent):
    pass                                                               
    def __init__(self, model_name: str, system_prompt: Optional[str] = STANDARD_GAME_PROMPT, verbose: bool = False, **kwargs):
        pass             
                                                    
                                                                                                   
                                                                           
                                                                                  
           
        super().__init__()
        self.model_name = model_name 
        self.verbose = verbose 
        self.system_prompt = system_prompt
        self.kwargs = kwargs

        try:
            from openai import OpenAI
            from openai._exceptions import OpenAIError
        except ImportError:
            raise ImportError("OpenAI package is required for OpenRouterAgent. Install it with: pip install openai")
        
        api_key = os.getenv("OPENROUTER_API_KEY")                                                           
        if not api_key:
            raise ValueError("OpenRouter API key not found. Please set the OPENROUTER_API_KEY environment variable.")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _make_request(self, observation: str) -> str:
        pass                                                                             
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
        response = self.client.chat.completions.create(model=self.model_name, messages=messages, n=1, stop=None, **self.kwargs)
        return response.choices[0].message.content.strip()

    def _retry_request(self, observation: str, retries: int = 3, delay: int = 5) -> str:
        pass                                                    

             
                                                    
                                                         
                                                          

               
                                                                     
           
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response

            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception

    def __call__(self, observation: str) -> str:
        pass                                                                               

             
                                                           

                
                                        
           
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class GeminiAgent(Agent):
    pass                                                                
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, generation_config: Optional[dict]=None):
        pass                                    
        
             
                                                    
                                                                                                    
                                                                           
                                                                                      
           
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose

        try: from google import genai
        except ImportError: raise ImportError("Google GenAI package is required for GeminiAgent. Install it with: pip install google-genai")
        
                                                             
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
        
                                     
        self.client = genai.Client(api_key=api_key, http_options={'headers': {'x-goog-api-client': f'TextArena/{ta.__version__}'}})
        
                                                           
        if generation_config is None:
            generation_config = {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192, "response_mime_type": "text/plain"}
        self.generation_config = generation_config
    
    def _make_request(self, observation: str) -> str:
        pass                                                                             
        
             
                                                           
        
                
                                             
           
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=f"Instructions: {self.system_prompt}\n\n{observation}",
            config=self.generation_config
        )
        if self.verbose: print(f"\nObservation: {observation}\nResponse: {response.text}")
        return response.text.strip()
    
    def _retry_request(self, observation: str, retries: int = 3, delay: int = 5) -> str:
        pass                                                    
        
             
                                                    
                                                         
                                                          
        
               
                                                                     
           
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                return self._make_request(observation)
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        pass                                                                                       
        
             
                                                           
        
                
                                        
           
        if not isinstance(observation, str): 
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class OpenAIAgent(Agent):
    pass                                                         

    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, api_key: str|None=None, base_url: str|None=None,**kwargs):
        pass                                    
        
             
                                                    
                                                                                                    
                                                                           
                                                                 
                                                                   
                                                                                  
           
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs

        try: from openai import OpenAI
        except ImportError: raise ImportError("OpenAI package is required for OpenAIAgent. Install it with: pip install openai")

        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key: raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def _make_request(self, observation: str) -> str:
        pass                                                                             
        
             
                                                           
        
                
                                             
           
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
        
                                                                  
        completion = self.client.chat.completions.create(model=self.model_name, messages=messages, n=1, stop=None, **self.kwargs)
        return completion.choices[0].message.content.strip()
    
    def _retry_request(self, observation: str, retries: int=3, delay: int=5) -> str:
        pass                                                    
        
             
                                                    
                                                         
                                                          
        
               
                                                                     
           
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        pass                                                                                       
        
             
                                                           
        
                
                                        
           
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class HFLocalAgent(Agent):
    def __init__(self, model_name: str, device: str = "auto", quantize: bool = False, max_new_tokens: int = 1024, hf_kwargs: dict | None = None):
        super().__init__()

        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

        hf_kwargs = hf_kwargs or {}

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **hf_kwargs)

        if quantize:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                load_in_8bit=True,
                device_map=device,
                **hf_kwargs,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map=device,
                **hf_kwargs,
            )

        self.system_prompt = STANDARD_GAME_PROMPT
        self.pipeline = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=max_new_tokens)

    def __call__(self, observation: str) -> str:
        try:
            response = self.pipeline(self.system_prompt + "\n" + observation, num_return_sequences=1, return_full_text=False)
            return response[0]["generated_text"].strip()
        except Exception as e:
            return f"An error occurred: {e}"



class CerebrasAgent(Agent):
    pass                                                                         
    def __init__(self, model_name: str, system_prompt: str | None = None):
        pass                                      

             
                                                    
                                                                                                          
           
        super().__init__()
        self.model_name = model_name
        
        try: from cerebras.cloud.sdk import Cerebras
        except ImportError: raise ImportError("Cerebras SDK is required for CerebrasAgent. Install it with: pip install cerebras-cloud-sdk")
            
        self.client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))                                         

                                
        if system_prompt is None:
            self.system_prompt = "You are a competitive game player. Make sure you read the game instructions carefully, and always follow the required format."
        else:
            self.system_prompt = system_prompt

    def __call__(self, observation: str) -> str:
        pass                                                                               

             
                                                           

                
                                                     
           
        try:
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
            response = self.client.chat.completions.create(model=self.model_name, messages=messages, top_p=0.9, temperature=0.9)
            action = response.choices[0].message.content.strip()                                
            return action
        except Exception as e:
            return f"An error occurred: {e}"


class AWSBedrockAgent(Agent):
    pass                                                                                          
    def __init__(self, model_id: str,  region_name: str="us-east-1", system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, **kwargs):
        pass                                         
        
             
                                                                     
                                                              
                                                                    
                                                             
                                                                        
           
        super().__init__()
        self.model_id = model_id
        self.region_name = region_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("Boto3 is required for AWSBedrockAgent. Install it with: pip install boto3")
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    def _make_request(self, observation: str) -> str:
        pass                                      
        conversation = [{"role": "user", "content": [{"text": observation}]}]
        systemPrompt = [{ "text": self.system_prompt }]
        try:
            inference_config={"maxTokens": 512, "temperature": 0.9, "topP": 0.9, **self.kwargs}
            response = self.client.converse(modelId=self.model_id, messages=conversation, system=systemPrompt, inferenceConfig=inference_config)
            response_text = response["output"]["message"]["content"][0]["text"].strip()
            if self.verbose:
                print(f"\nObservation: {observation}\nResponse: {response_text}")
            return response_text
        except Exception as e:
            return f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}"

    def __call__(self, observation: str) -> str:
        pass                                                                     
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._make_request(observation)


class AnthropicAgent(Agent):
    pass                                                                   
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, max_tokens: int=1000, temperature: float=0.9, verbose: bool=False):
        pass                                       

             
                                                                                                
                                                                                                    
                                                                       
                                                                                       
                                                                           
           
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.verbose = verbose
        
        try: import anthropic
        except ImportError: raise ImportError("Anthropic package is required for AnthropicAgent. Install it with: pip install anthropic")
        self.client = anthropic.Anthropic()
    
    def _make_request(self, observation: str) -> str:
        pass                                                                           
        messages=[{"role": "user", "content": [{"type": "text", "text": observation}]}]
        response = self.client.messages.create(model=self.model_name, max_tokens=self.max_tokens, temperature=self.temperature, system=self.system_prompt, messages=messages)
        return response.content[0].text.strip()
    
    def _retry_request(self, observation: str, retries: int=3, delay: int=5) -> str:
        pass                                                    

             
                                                    
                                                         
                                                          

               
                                                                     
           
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        pass                                                                                          
        
             
                                                           
        
                
                                        
           
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class GroqAgent(Agent):
    pass                                                       
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT,
                 verbose: bool=False, **kwargs):
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Groq package is required for GroqAgent. Install it with: pip install groq")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY.")
        self.client = Groq(api_key=api_key)

    def _make_request(self, observation: str) -> str:
        messages=[{"role":"system","content":self.system_prompt},
                  {"role":"user","content":observation}]
        resp = self.client.chat.completions.create(
            model=self.model_name, messages=messages, n=1, **self.kwargs)
        return resp.choices[0].message.content.strip()

    def _retry_request(self, observation: str, retries: int=3, delay: int=5) -> str:
        last_exc=None
        for i in range(1, retries+1):
            try:
                out = self._make_request(observation)
                if self.verbose: print(f"\nObservation: {observation}\nResponse: {out}")
                return out
            except Exception as e:
                last_exc=e
                print(f"Attempt {i} failed with error: {e}")
                if i < retries: time.sleep(delay)
        raise last_exc

    def __call__(self, observation: str) -> str:
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received {type(observation)}")
        return self._retry_request(observation)


class OllamaAgent(Agent):
    pass                                             
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT,
                 host: Optional[str]=None, verbose: bool=False, **kwargs):
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs
        try:
            from ollama import Client
        except ImportError:
            raise ImportError("Ollama package is required for OllamaAgent. Install it with: pip install ollama")
        host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = Client(host=host)

    def _make_request(self, observation: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": observation}
        ]
        resp = self.client.chat(model=self.model_name, messages=messages, **self.kwargs)
                                                                                    
        return resp["message"]["content"].strip()

    def __call__(self, observation: str) -> str:
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received {type(observation)}")
        try:
            out = self._make_request(observation)
            if self.verbose: print(f"\nObservation: {observation}\nResponse: {out}")
            return out
        except Exception as e:
            return f"ERROR (Ollama): {e}"


class LlamaCppAgent(Agent):
    pass                                                                 
    def __init__(self, model_path: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT,
                 n_ctx: int=8192, n_threads: Optional[int]=None, chat_format: Optional[str]=None,
                 verbose: bool=False, **gen_kwargs):
        super().__init__()
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.gen_kwargs = gen_kwargs
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python is required. Install with: pip install llama-cpp-python")
                                                                      
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, chat_format=chat_format)

    def __call__(self, observation: str) -> str:
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received {type(observation)}")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": observation}
        ]
                                                                                                        
        out = self.llm.create_chat_completion(messages=messages, **self.gen_kwargs)
        text = out["choices"][0]["message"]["content"].strip()
        if self.verbose: print(f"\nObservation: {observation}\nResponse: {text}")
        return text
