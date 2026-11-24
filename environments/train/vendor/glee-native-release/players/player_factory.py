from players.terminal_player import TerminalPlayer
from players.litellm_player import LiteLLMPlayer
from players.otree_player import OtreePlayer
from players.demo_player import DemoPlayer
from players.otree_litellm_player import OtreeLiteLLMPlayer
from players.http_player import HTTPPlayer
from players.huggingface_player import HuggingFacePlayer


PLAYERS = {
    'terminal': TerminalPlayer,
    'otree': OtreePlayer,
    'demo': DemoPlayer,
    'otree_LLM': OtreeLiteLLMPlayer,
    'litellm': LiteLLMPlayer,
    'http': HTTPPlayer,
    'huggingface': HuggingFacePlayer,
    'hf': HuggingFacePlayer,               
}


def player_factory(player_type, player_args):
    return PLAYERS[player_type](**player_args)
