from games.persuasion.persuasion import PersuasionGame
from games.negotiation.negotiation import NegotiationGame
from games.bargaining.bargaining import BargainingGame

GAMES = {
    'bargaining': BargainingGame,
    'persuasion': PersuasionGame,
    'negotiation': NegotiationGame
}


def game_factory(game_type, player_1, player_2, data_logger, game_args):
    return GAMES[game_type](player_1, player_2, data_logger, **game_args)