import os
from typing import Dict, List

import anthropic
from dotenv import load_dotenv

from scigym.api import LLM

load_dotenv()


class Claude(LLM):
    def __init__(
        self,
        model_name: str = "claude-3-5-haiku-20241022",
        api_key: str = os.getenv("CLAUDE_API_KEY", ""),
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
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.messages = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages

    def get_response(self, user_message: str) -> tuple:
        self.add_message("user", user_message)

        response = self.client.messages.create(
            model=self.model_name,
            system=self.system_prompt,
            messages=self.messages,
            max_tokens=self.max_length,
            temperature=self.temperature,
        )

        assert len(response.content) > 0
        assert isinstance(response.content[0], anthropic.types.TextBlock)
        response_text = response.content[0].text

        self.add_message("assistant", response_text)

        return response_text, {}
