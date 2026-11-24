from players.base_player import Player
import os
import litellm
import time
from utils.conversation import get_conv_template
import subprocess

class LiteLLMPlayer(Player):
    def __init__(self, public_name, delta=1, player_id=0, **kwargs):
        super().__init__(public_name, delta, player_id)        
        assert 'model_name' in kwargs, 'model_name must be provided'
        init_litellm()
        if "gemini-1.5-pro" in kwargs["model_name"]:
            self.model_name = kwargs["model_name"] + "-002"
        else:
            self.model_name = kwargs["model_name"]
        
        self.conv = get_conv_template("default")
        self.user_name = "user"
        self.model_args = load_model_args(self.model_name)

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
                kwargs = self.model_args.copy()
                if self.timeout:
                    kwargs['timeout'] = self.timeout

                response = litellm.completion(
                    model=self.model_name,
                    messages=self.conv.to_openai_api_messages(),
                    **kwargs
                )
                self.text_response = response['choices'][0]['message']['content'].strip()
                if format_checker(self.text_response):
                    print(self.text_response)
                    self.conv.append_message(self.conv.roles[1], self.text_response)
                    break
            except Exception as e:
                if self.timeout and "timeout" in str(e).lower():
                    raise e
                print(e)
                time.sleep(4 ** (count + 1))
            count += 1
        return self.text_response

    def set_system_message(self, message):
        self.conv.system_message = message


def init_litellm():
    command = "source litellm/init_litellm.sh && env"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        key_value = line.split("=", 1)
        if len(key_value) == 2:
            os.environ[key_value[0]] = key_value[1]
            

def load_model_args(model_name):
    args = {}
    if "vertex_ai" in model_name and "claude" in model_name:
        args["vertex_location"] = "us-east5"
    if "vertex_ai" in model_name and "mistral" in model_name:
        args["vertex_location"] = "europe-west4"
    return args