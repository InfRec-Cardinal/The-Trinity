from players.base_player import Player
import os
import litellm
import time
from utils.conversation import get_conv_template
from players.litellm_player import init_litellm


class OtreeLiteLLMPlayer(Player):
    def __init__(self, public_name, delta=1, player_id=0, **kwargs):
        super().__init__(public_name, delta, player_id)

        init_litellm()
        self.model_name = kwargs.get('model_name', 'gemini-1.5-flash')

        self.conv = get_conv_template("default")
            
        assert self.conv is not None, f"Conversation template not found for model {self.model_name}"

        self.user_name = "user"

    def add_message(self, message, role='user'):
        if role == 'system':
            self.conv.system_message = message
        else:
            self.conv.append_message(self.conv.roles[0], message)

    def clean_conv(self):
        self.conv.messages = list()

    def get_text_answer(self, format_checker, decision=False):
        count = 0
        while count < 7:
            try:
                kwargs = {}
                if self.timeout:
                    kwargs['timeout'] = self.timeout
                response = litellm.completion(
                    model=self.model_name,
                    messages=self.conv.to_openai_api_messages(),
                    **kwargs
                )
                self.text_response = response['choices'][0]['message']['content'].strip()
                if format_checker(self.text_response):
                    self.conv.append_message(self.conv.roles[1], self.text_response)
                    break
            except Exception as e:
                if self.timeout and "timeout" in str(e).lower():
                    raise e
                print("Error generating content", e)
                time.sleep(1)
            count += 1
        return self.text_response

    def set_system_message(self, message):
        self.conv.system_message = message
