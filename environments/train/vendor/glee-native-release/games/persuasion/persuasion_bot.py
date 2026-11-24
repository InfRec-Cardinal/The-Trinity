from games.persuasion.persuasion import PersuasionGame
from games.base_bot import Bot
from consts import *


class PersuasionBot(Bot, PersuasionGame):
    def __init__(self, player_1, player_2, human_start, **kwargs):
        PersuasionGame.__init__(self, player_1, player_2, None, **kwargs)
        Bot.__init__(self, player_1, player_2, human_start)

        self.is_quality = None

        if (not self.human_start) and self.is_myopic:                              
            raise ValueError("Myopic buyer is not supported in bot mode")

    def get_game_name(self):
        return "Persuasion"

    def get_otree_player_fields(self):
        proposer = ['proposer_message'] if self.seller_message_type == 'text' else ['proposer_recommendation']
        receiver = ['receiver_message'] if self.allow_buyer_message else []
        fields = proposer + receiver + ['additional_info']
        return fields

    def bot_proposer_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(PROPOSER)
        if not duplicate:
            self.is_quality = self.generate_quality()
            otree_player.additional_info = str(self.is_quality)
            round_quality, product_worth, product_worth_str = self.quality_stats(self.is_quality)
            seller_text = self.generate_seller_text(self.turn, round_quality)
            self.bot_player.add_to_buffer(seller_text)            
            self.bot_player.edit_system_message(self.bot_player.req_offer_text)            
            self.bot_player.act(self.is_offer_in_format if self.seller_message_type == "text"
                                else self.is_seller_decision_in_format)            

            if self.seller_message_type == "text":
                otree_player.proposer_message = self.bot_player.last_action_json["message"]
            else:          
                decision_text = self.bot_player.last_action_json["decision"]
                otree_player.proposer_recommendation = True if decision_text == "yes" else False

    def bot_receiver_turn(self, otree_player):
        duplicate = self.vars_for_template_bot_action_duplicate(RECEIVER)
        if not duplicate:
            if self.seller_message_type == "text":
                seller_content = otree_player.proposer_message
            else:
                seller_content = "yes" if otree_player.proposer_recommendation else "no"

            offer_text = self.generate_buyer_text(self.turn, seller_content)
            self.bot_player.add_to_buffer(offer_text)            
            self.bot_player.edit_system_message(self.bot_player.req_response_text)            
            self.bot_player.act(self.is_buyer_decision_in_format)            
            otree_player.accepted = 1 if self.bot_player.last_action_json["decision"] == "yes" else 0
            if self.allow_buyer_message:
                otree_player.receiver_message = self.bot_player.last_action_json["message"]

    def set_payoffs(self, otree_player):
        if self.human_start:                   
            otree_player.utility = self.sold_counter * self.product_price
        else:                  
            buyer_value = self.sold_quality_counter * self.v + (self.sold_counter - self.sold_quality_counter) * self.c
            buyer_paid = self.sold_counter * self.product_price
            otree_player.utility = buyer_value - buyer_paid

    def final_quiz_options(self):
        question_text = f"What is the fixed price of the products in this game?"
        right_answer = self.product_price
        wrong_answers = [right_answer * 0.25, right_answer * 0.5, right_answer * 2, self.product_price * self.v]
        return question_text, right_answer, wrong_answers

    def get_proposer_text(self, otree_player):
        duplicate = self.vars_for_template_text_duplicate(PROPOSER)
        if not duplicate:
            self.is_quality = self.generate_quality()
            otree_player.additional_info = str(self.is_quality)
        round_quality, product_worth, product_worth_str = self.quality_stats(self.is_quality)
        seller_text = self.generate_seller_text(self.turn, round_quality)
        return seller_text

    def get_receiver_text(self, otree_player):
        self.vars_for_template_text_duplicate(RECEIVER)
        seller_content = self.bot_player.last_action_json["message"] if self.seller_message_type == "text" else \
            self.bot_player.last_action_json["decision"]
        offer_text = self.generate_buyer_text(self.turn, seller_content)
        return offer_text

    def get_response_text(self, otree_player):
        duplicate = self.vars_for_template_text_duplicate(RESPONSE)
        self.vars_for_template_bot_action_duplicate(None)                                                
        if self.human_start:
            buyer_message = self.bot_player.last_action_json["message"] if self.allow_buyer_message else ""            
        else:
            buyer_message = otree_player.receiver_message if self.allow_buyer_message else ""
        seller_text, buyer_response_text, buyer_quality_text, buyer_msg = (
            self.generate_response_text(accepted=otree_player.accepted > 0,
                                        is_quality=self.is_quality,
                                        buyer_message=buyer_message))

        if self.human_start:
            response_text = buyer_msg + "\n" + seller_text if buyer_msg else seller_text
            if not duplicate:
                self.bot_player.add_to_buffer(buyer_response_text + "\n")            
                self.bot_player.add_to_buffer(buyer_quality_text)            
            if self.turn < self.get_max_rounds() and self.is_myopic:
                if not duplicate:
                    self.bot_player.end_chat()            
                    self.bot_player.new_chat()            
                response_text += f"\n{self.bot_player.public_name} left. New customer incoming!"
            response_text += "\n\n"
        else:
            response_text = buyer_response_text + "\n" + buyer_quality_text
            if not duplicate:
                if buyer_msg:
                    self.bot_player.add_to_buffer(buyer_msg + "\n")            
                self.bot_player.add_to_buffer(seller_text)            
                if self.turn < self.get_max_rounds() and self.is_myopic:
                    self.bot_player.add_to_buffer(f"\n{self.human_player.public_name} left. New customer incoming!")
                self.bot_player.add_to_buffer("\n\n")

        if not duplicate:
            self.turn += 1
            if otree_player.accepted > 0:
                self.sold_counter += 1
                if self.is_quality:
                    self.sold_quality_counter += 1
        self.is_quality = None
        return response_text

    def who_propose(self, minus_one=False):
        return HUMAN if self.human_start else BOT

    def get_max_rounds(self):
        return min(self.total_rounds, OTREE_MAX_ROUNDS)

    def get_bonus_text(self):
        if self.product_price == 100:
            avg_bonus = 5
        elif self.product_price == 10000:
            avg_bonus = 15
        else:                                    
                                                  
            avg_bonus = 25
        return (f"You will receive a bonus based on your performance in the game. "
                f"The average bonus is {avg_bonus} cents.")

    def initialize(self):
        self.is_quality = None
        Bot.initialize(self)

    def show_proposer_page(self, otree_player):
        return Bot.show_proposer_page(self, otree_player) and self.human_start

    def show_receiver_page(self, otree_player):
        return Bot.show_receiver_page(self, otree_player) and not self.human_start

    def show_results_and_set_payoffs(self, otree_player):
        res = self.end or self.turn > self.get_max_rounds()
        if res:
            self.endgame()
            self.set_payoffs(otree_player)
        return res
