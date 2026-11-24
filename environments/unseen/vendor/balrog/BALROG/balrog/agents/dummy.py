import logging
from collections import defaultdict, namedtuple

from balrog.agents.base import BaseAgent

LLMResponse = namedtuple(
    "LLMResponse",
    [
        "model_id",
        "completion",
        "stop_reason",
        "input_tokens",
        "output_tokens",
        "reasoning",
    ],
)


def make_dummy_action(text):
    pass                                 
    return LLMResponse(
        model_id="dummy",
        completion="wait",
        stop_reason="none",
        input_tokens=1,
        output_tokens=1,
        reasoning=None,
    )


class DummyAgent(BaseAgent):
    pass                               

    def __init__(self, client_factory, prompt_builder):
        pass                                                             
        super().__init__(client_factory, prompt_builder)
        self.client = client_factory()

    def act(self, obs, prev_action=None):
        pass                        
        return make_dummy_action("dummy_action")
