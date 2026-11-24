from abc import ABC, abstractmethod
from consts import *


class Bot(ABC):

    def __init__(self, player_1, player_2, human_start):
        self.human_player = player_1 if human_start else player_2
        self.bot_player = player_2 if human_start else player_1
        self.human_start = human_start

        self.turn = None
        self.last_get_action = None
        self.last_get_text = None
        self.end = False
        self.show_instructions = True

    def initialize(self):
        self.player_initialize(self.bot_player)
        self.turn = 1
        self.last_get_action = None
        self.last_get_text = None
        self.end = False
        self.show_instructions = True
        assert self.get_max_rounds() <= OTREE_MAX_ROUNDS, "Max rounds should be less than otree max rounds"

    @staticmethod
    def player_initialize(player):
        player.buffer = ""
        player.clean_conv()
        player.new_chat()

    def game(self):
        pass
    
    def endgame(self):
        if not self.end:
            self.end = True
            self.bot_player.end_chat()
            self.turn -= 1                                                 

    @staticmethod
    def get_game_name():
        return "Simple"

    def get_bonus_text(self):
        return ""

    def show_proposer_page(self, otree_player):
        return not self.end and self.turn <= self.get_max_rounds()

    def show_receiver_page(self, otree_player):
        return not self.end and self.turn <= self.get_max_rounds()

    def show_response_page(self):
        return not self.end and self.turn <= self.get_max_rounds()

    def show_results_and_set_payoffs(self, otree_player):
        res = self.end or otree_player.accepted > 0 or self.turn > self.get_max_rounds()
        if res:
            self.endgame()
            self.set_payoffs(otree_player)
        return res

    def special_decision(self):
        return None

    def get_final_text(self, otree_player):
        return ""

    def vars_for_template_bot_action_duplicate(self, current):
        is_duplicate = (current == self.last_get_action)
        self.last_get_action = current
        return is_duplicate

    def vars_for_template_text_duplicate(self, current):
        is_duplicate = (current == self.last_get_text)
        self.last_get_text = current
        return is_duplicate

    def get_offer_type(self):
        return "number"

    def get_max_offer(self):
        raise Exception("Not Supported")

    @abstractmethod
    def get_otree_player_fields(self):
        pass

    @abstractmethod
    def bot_proposer_turn(self, otree_player):
        pass

    @abstractmethod
    def bot_receiver_turn(self, otree_player):
        pass

    @abstractmethod
    def set_payoffs(self, otree_player):
        pass

    @abstractmethod
    def final_quiz_options(self):
        pass

    @abstractmethod
    def get_proposer_text(self, otree_player):
        pass

    @abstractmethod
    def get_receiver_text(self, otree_player):
        pass

    @abstractmethod
    def get_response_text(self, otree_player):
        pass
    
    @abstractmethod
    def who_propose(self, minus_one=False):
        pass
    
    @abstractmethod
    def get_max_rounds(self):
        pass
    