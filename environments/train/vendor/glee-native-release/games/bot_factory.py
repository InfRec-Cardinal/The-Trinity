from games.bargaining.bargaining_bot import BargainingBot
from games.persuasion.persuasion_bot import PersuasionBot
from games.negotiation.negotiation_bot import NegotiationBot

BOTS = {
    'bargaining': BargainingBot,
    'persuasion': PersuasionBot,
    'negotiation': NegotiationBot
}


def bot_factory(game_type, player_1, player_2, player_start, game_args):
    return BOTS[game_type](player_1, player_2, player_start, **game_args)
