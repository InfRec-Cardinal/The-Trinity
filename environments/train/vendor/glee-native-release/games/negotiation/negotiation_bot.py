import re
from games.negotiation.negotiation import NegotiationGame
from games.base_bot import Bot
from consts import *


class NegotiationBot(Bot, NegotiationGame):

    def __init__(self, player_1, player_2, human_start, **kwargs):
        NegotiationGame.__init__(self, player_1, player_2, None, **kwargs)
        Bot.__init__(self, player_1, player_2, human_start)
        self.product_price_order = kwargs['product_price_order']

    def get_game_name(self):
        return "Negotiation"

    def get_otree_player_fields(self):
        return ['offer', 'proposer_message'] if self.messages_allowed else ['offer']

    def bot_proposer_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(PROPOSER)
        if not duplicate:
            proposer_message_format, proposer_text = \
                (NegotiationGame.get_proposer_text(self, round_number=self.turn,
                                                   proposer=self.bot_player, receiver=self.human_player))
            self.bot_player.add_to_buffer(proposer_text)
            self.bot_player.edit_system_message(proposer_message_format)
            self.bot_player.act(self.is_offer_in_format)

            otree_player.offer = (
                int(round(self.bot_player.last_action_json['product_price'])))
            if self.messages_allowed:
                otree_player.proposer_message = self.bot_player.last_action_json["message"]

    def bot_receiver_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(RECEIVER)
        if not duplicate:
            proposer_message = otree_player.proposer_message if self.messages_allowed else ""
            counteroffer_is_option = self.turn < self.get_max_rounds()
            receiver_message_format, receiver_text = (
                NegotiationGame.get_receiver_text(self, round_number=self.turn,
                                                  proposer_name=self.human_player.public_name,
                                                  proposer_offer=otree_player.offer, proposer_message=proposer_message,
                                                  receiver_jhon_caption=self.bot_player.deal_with_jhon_caption,
                                                  receiver_act_name=self.bot_player.act_name,
                                                  receiver_jhon_text=self.bot_player.deal_with_jhon_text,
                                                  counteroffer_is_option=counteroffer_is_option))
            self.bot_player.add_to_buffer(receiver_text)
            self.bot_player.edit_system_message(receiver_message_format)
            self.bot_player.act(self.is_decision_in_format)

            decision = self.bot_player.last_action_json["decision"]
            otree_player.accepted = 2 if decision == "AcceptOffer" else (1 if decision == "RejectOffer" else 0)

    def set_payoffs(self, otree_player):
        otree_player.utility = 0
        if self.human_start:
            if otree_player.accepted == 2:
                otree_player.utility = otree_player.offer - self.human_player.final_value
            else:                                                            
                otree_player.utility = 0
        else:
            if otree_player.accepted == 2:
                otree_player.utility = self.human_player.final_value - otree_player.offer
            else:                                                            
                otree_player.utility = 0

    def final_quiz_options(self):
        if self.human_start:
            question_text = f"What is the minimum worth of the product for you in this game?"
        else:
            question_text = f"What is the maximum worth of the product for you in this game?"
        right_answer = self.human_player.final_value
        wrong_answers = [right_answer * 0.25, right_answer * 0.5, right_answer * 2, right_answer * 4,
                         self.bot_player.final_value]
        return question_text, right_answer, wrong_answers

    def get_proposer_text(self, otree_player):
        self.vars_for_template_text_duplicate(PROPOSER)
        _, proposer_text = NegotiationGame.get_proposer_text(self, round_number=self.turn,
                                                             proposer=self.human_player, receiver=self.bot_player)
        return proposer_text

    def get_receiver_text(self, otree_player):
        self.vars_for_template_text_duplicate(RECEIVER)
        proposer_message = otree_player.proposer_message if self.messages_allowed else ""
        counteroffer_is_option = self.turn < self.get_max_rounds()
        _, receiver_text = (
            NegotiationGame.get_receiver_text(self, round_number=self.turn, proposer_name=self.bot_player.public_name,
                                              proposer_offer=otree_player.offer, proposer_message=proposer_message,
                                              receiver_jhon_caption=self.human_player.deal_with_jhon_caption,
                                              receiver_act_name=self.human_player.act_name,
                                              receiver_jhon_text=self.human_player.deal_with_jhon_text,
                                              counteroffer_is_option=counteroffer_is_option))
        return receiver_text

    def get_response_text(self, otree_player):
        duplicate = self.vars_for_template_text_duplicate(RESPONSE)
        human_offer = self.who_propose(duplicate) == HUMAN
        proposer = self.human_player if human_offer else self.bot_player
        receiver = self.bot_player if human_offer else self.human_player

        decision = "AcceptOffer" if otree_player.accepted == 2 else ("RejectOffer" if otree_player.accepted == 1
                                                                     else receiver.deal_with_jhon_caption)
        response_texts = NegotiationGame.get_response_text(self, round_number=self.turn, decision=decision,
                                                           proposer_name=proposer.public_name,
                                                           receiver_name=receiver.public_name)
        if not duplicate:
            self.turn += 1
            proposer.add_to_buffer(response_texts["proposer"])
            receiver.add_to_buffer(response_texts["receiver"])

        if human_offer:
            return response_texts["proposer"]
        else:
            return response_texts["receiver"]

    def who_propose(self, minus_one=False):
        real_turn = self.turn - int(minus_one)
        return HUMAN if (real_turn + int(self.human_start)) % 2 == 0 else BOT

    def get_max_rounds(self):
        return min(self.max_rounds, OTREE_MAX_ROUNDS)

    def get_bonus_text(self):
        if self.product_price_order == 100:
            avg_bonus = 5
        elif self.product_price_order == 10000:
            avg_bonus = 15
        else:                                    
                                                        
            avg_bonus = 25
        return (f"You will receive a bonus based on your performance in the game. "
                f"The average bonus is {avg_bonus} cents.")

    def show_proposer_page(self, otree_player):
        return Bot.show_proposer_page(self, otree_player) and (self.turn + int(self.human_start)) % 2 == 0

    def show_receiver_page(self, otree_player):
        return Bot.show_receiver_page(self, otree_player) and (self.turn + int(self.human_start)) % 2 == 1

    def show_results_and_set_payoffs(self, otree_player):
        res = self.end or otree_player.accepted in [0, 2] or self.turn > self.get_max_rounds()
        if res:
            self.endgame()
            self.set_payoffs(otree_player)
        return res

    def special_decision(self):
        human_offer = self.who_propose() == HUMAN
        receiver = self.bot_player if human_offer else self.human_player

        base_deal = receiver.deal_with_jhon_caption
        words = re.findall(r'[A-Z][a-z]*', base_deal)
        deal = ' '.join(words)
        return [(0, 2, "Accept Offer", "green"), (1, 1, "Reject Offer", "red"), (2, 0, deal, "blue")]

    def get_max_offer(self):
        return None
