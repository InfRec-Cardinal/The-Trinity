import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

from scigym.api import LLM


class Gemini(LLM):
    pass                                         

    def __init__(
        self,
        model_name: str = "gemini-2.5-pro-preview-03-25",
        api_key: str = os.getenv("GEMINI_API_KEY", ""),
        system_prompt: str = "",
        temperature: float = 1.0,
        *args,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            system_prompt=system_prompt,
            temperature=temperature,
            *args,
            **kwargs,
        )

    def initialize(self):
        self.client = genai.Client(api_key=self.api_key)
        chat_config = types.GenerateContentConfig(
            system_instruction=self.system_prompt, temperature=self.temperature
        )
        self.chat = self.client.chats.create(model=self.model_name, config=chat_config)

    def add_message(self, role: str, content: str):
        pass                                                  
                                                                                                 
                                                                  
           

    def get_messages(self) -> List[Dict[str, str]]:
        pass                                     
                                                                        
           
        gemini_history = self.chat.get_history()
        standard_messages = []

        for i, msg in enumerate(gemini_history):
            role = "user" if i % 2 == 0 else "assistant"
            if hasattr(msg, "parts") and msg.parts is not None and len(msg.parts) > 0:
                content = msg.parts[0].text
            else:
                content = str(msg)
            standard_messages.append({"role": role, "content": content})

        return standard_messages

    def get_response(self, user_message: str) -> tuple:
        pass                                
                                     
        response = self.chat.send_message(user_message)
        response_text = response.text

                                 
        usage_stats = {}
        if response.usage_metadata is not None:
            if response.usage_metadata.prompt_token_count is not None:
                usage_stats["input_tokens"] = response.usage_metadata.prompt_token_count
            if response.usage_metadata.candidates_token_count is not None:
                usage_stats["output_tokens"] = response.usage_metadata.candidates_token_count
            if response.usage_metadata.thoughts_token_count is not None:
                usage_stats["thoughts_tokens"] = response.usage_metadata.thoughts_token_count

        return response_text, usage_stats
