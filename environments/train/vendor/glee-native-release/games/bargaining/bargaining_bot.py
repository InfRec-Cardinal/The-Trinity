from games.bargaining.bargaining import BargainingGame
from games.base_bot import Bot
from consts import *


class BargainingBot(Bot, BargainingGame):

    def __init__(self, player_1, player_2, human_start, **kwargs):
        BargainingGame.__init__(self, player_1, player_2, None, **kwargs)
        Bot.__init__(self, player_1, player_2, human_start)

    def get_game_name(self):
        return "Bargaining"

    def get_otree_player_fields(self):
        return ['offer', 'proposer_message'] if self.messages_allowed else ['offer']

    def bot_proposer_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(PROPOSER)
        if not duplicate:
            inflation_update = self.get_inflation_update(round_number=self.turn,
                                                         self_player=self.bot_player,
                                                         other_player=self.human_player)
            offer_text = self.generate_make_offer_txt(round_number=self.turn,
                                                      player_inflation_update=inflation_update,
                                                      other_player_name=self.human_player.public_name)
            self.bot_player.add_to_buffer(offer_text)
            self.bot_player.edit_system_message(self.bot_player.req_offer_text)
            self.bot_player.act(self.is_offer_in_format)

            otree_player.offer = (
                int(round(self.bot_player.last_action_json[f"{self.lower_name(self.human_player.public_name)}_gain"])))
            if self.messages_allowed:
                otree_player.proposer_message = self.bot_player.last_action_json["message"]

    def bot_receiver_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(RECEIVER)
        if not duplicate:
            proposer_gain = self.money_to_divide - otree_player.offer
            receiver_gain = otree_player.offer
            offer_message = otree_player.proposer_message if self.messages_allowed else None

            inflation_update = self.get_inflation_update(round_number=self.turn,
                                                         self_player=self.bot_player,
                                                         other_player=self.human_player)
            system_message, accept_offer_text = (
                self.generate_accept_offer_txt(round_number=self.turn,
                                               proposer_name=self.human_player.public_name,
                                               proposer_gain=proposer_gain,
                                               receiver_name=self.bot_player.public_name,
                                               receiver_gain=receiver_gain,
                                               offer_message=offer_message,
                                               inflation_update=inflation_update))
            self.bot_player.edit_system_message(system_message)
            self.bot_player.add_to_buffer(accept_offer_text)
            self.bot_player.act(self.is_decision_in_format)

            otree_player.accepted = 1 if self.bot_player.last_action_json["decision"] == "accept" else 0

    def set_payoffs(self, otree_player):
        if otree_player.accepted > 0:
            decrease = self.human_player.delta ** (self.turn - 1)
            human_offer = self.who_propose() == HUMAN
            if human_offer:
                otree_player.utility = decrease * float((self.money_to_divide - otree_player.offer))
            else:             
                otree_player.utility = float(decrease * otree_player.offer)
        else:
            otree_player.utility = 0

    def final_quiz_options(self):
        question_text = f"In each round, by what percentage is the money worth less for you?"
        right_answer = (1 - self.human_player.delta) * 100
                                                   
        wrong_answers = [0, 0.01 * 100, 0.02 * 100, 0.03 * 100, 0.05 * 100, 0.1 * 100, 0.2 * 100]
        return question_text, right_answer, wrong_answers

    def get_proposer_text(self, otree_player):
        self.vars_for_template_text_duplicate(PROPOSER)
        inflation_update = self.get_inflation_update(round_number=self.turn,
                                                     self_player=self.human_player,
                                                     other_player=self.bot_player)
        offer_text = self.generate_make_offer_txt(round_number=self.turn,
                                                  player_inflation_update=inflation_update,
                                                  other_player_name=self.bot_player.public_name)
        return offer_text

    def get_receiver_text(self, otree_player):
        self.vars_for_template_text_duplicate(RECEIVER)
        human_gain = otree_player.offer
        bot_gain = self.money_to_divide - otree_player.offer
        offer_message = otree_player.proposer_message if self.messages_allowed else None
        inflation_update = self.get_inflation_update(round_number=self.turn,
                                                     self_player=self.human_player,
                                                     other_player=self.bot_player)
        _, accept_offer_text = self.generate_accept_offer_txt(round_number=self.turn,
                                                              proposer_name=self.bot_player.public_name,
                                                              proposer_gain=bot_gain,
                                                              receiver_name=self.human_player.public_name,
                                                              receiver_gain=human_gain,
                                                              offer_message=offer_message,
                                                              inflation_update=inflation_update)
        return accept_offer_text

    def get_response_text(self, otree_player):
        duplicate = self.vars_for_template_text_duplicate(RESPONSE)
        human_offer = self.who_propose() == HUMAN
        accepted = otree_player.accepted > 0
        proposer = self.human_player if human_offer else self.bot_player
        receiver = self.bot_player if human_offer else self.human_player

        first_txt, second_txt = self.generate_response_texts(accepted=accepted, round_number=self.turn,
                                                             proposer_name=proposer.public_name,
                                                             receiver_name=receiver.public_name)
        if not duplicate:
            proposer.add_to_buffer(first_txt)
            receiver.add_to_buffer(second_txt)
            self.turn += 1
        return first_txt if human_offer else second_txt

    def who_propose(self, minus_one=False):
        real_turn = self.turn - int(minus_one)
        return HUMAN if (real_turn + int(self.human_start)) % 2 == 0 else BOT

    def get_max_rounds(self):
        return min(self.max_rounds, OTREE_MAX_ROUNDS)

    def get_bonus_text(self):
        if self.money_to_divide == 100:
            avg_bonus = 5
        elif self.money_to_divide == 10000:
            avg_bonus = 15
        else:                                    
                                                    
            avg_bonus = 25
        return (f"You will receive a bonus based on your performance in the game. "
                f"The average bonus is {avg_bonus} cents.")

    def show_proposer_page(self, otree_player):
        return Bot.show_proposer_page(self, otree_player) and (self.turn + int(self.human_start)) % 2 == 0

    def show_receiver_page(self, otree_player):
        return Bot.show_receiver_page(self, otree_player) and (self.turn + int(self.human_start)) % 2 == 1

    def get_final_text(self, otree_player):
        return f"There is no agreement after {self.get_max_rounds()} rounds.<br>" \
            if otree_player.accepted == 0 and self.turn == self.get_max_rounds() else ""

    def get_offer_type(self):
        return "slider"

    def get_max_offer(self):
        return self.money_to_divide
