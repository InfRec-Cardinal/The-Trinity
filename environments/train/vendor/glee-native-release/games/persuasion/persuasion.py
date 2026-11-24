from players.base_player import Player
import json
import re
import random
from utils.utils import pretty_number, add_ordinal_suffix
from games.base_game import Game
from consts import *


class PersuasionGame(Game):
    def __init__(self, player_1: Player, player_2: Player, data_logger,
                 is_myopic: bool, product_price, p: float,
                 c, v=0, total_rounds=20, is_seller_know_cv: bool = True, is_buyer_know_p: bool = True,
                 seller_message_type: str = "text", allow_buyer_message: bool = False, timeout=360):
        pass                              
                                                  
                                                    
        super().__init__(player_1, player_2, data_logger, timeout)
        self.is_myopic = is_myopic
        self.product_price = product_price
        assert 0 <= p <= 1
        assert 0 <= c <= 1
        assert 1 <= v
        self.p = p                                                                                            
        self.c = c * product_price
        self.v = v * product_price
        self.total_rounds = total_rounds
        self.is_seller_know_cv = is_seller_know_cv
        self.is_buyer_know_p = is_buyer_know_p

        self.seller_message_type = seller_message_type
        self.allow_buyer_message = allow_buyer_message

        if self.is_myopic:
            self.player_2.public_name = "the buyer"

        self.sold_counter = 0
        self.sold_quality_counter = 0
        self.recommended_counter = 0

        self.buyer_cv = None
        self.seller_cv = None
        self.buyer_p = None
        self.seller_p = None

        p_info = self.construct_player_info()

        path = 'games/persuasion/prompts/'
        self.set_rules(os.path.join(path, 'rules_prompt.json'), p_info, 'p1')
        self.set_rules(os.path.join(path, 'rules_prompt.json'), p_info, 'p2')
        self.player_1.req_offer_text, self.player_2.req_offer_text = self.build_offer_prompt()

                                         
        base_game_params = {
            "is_myopic": is_myopic,
            "product_price": product_price,
            "total_rounds": total_rounds,
            "seller_message_type": seller_message_type,
            "allow_buyer_message": allow_buyer_message
        }

                                               
        seller_params = {
            **base_game_params,
            "role": "seller",
            "p": p                         
        }

        buyer_params = {
            **base_game_params,
            "role": "buyer"
        }

                                                     
        if is_seller_know_cv:
            seller_params["c"] = c
            seller_params["v"] = v

                                                 
        if is_buyer_know_p:
            buyer_params["p"] = p

                                                                   
        buyer_params["c"] = c
        buyer_params["v"] = v

        self.player_1.set_game_params(seller_params)
        self.player_2.set_game_params(buyer_params)

                                             
        game_params = {
            "is_myopic": is_myopic,
            "product_price": product_price,
            "p": p,
            "c": c,
            "v": v,
            "total_rounds": total_rounds,
            "is_seller_know_cv": is_seller_know_cv,
            "is_buyer_know_p": is_buyer_know_p,
            "seller_message_type": seller_message_type,
            "allow_buyer_message": allow_buyer_message
        }

                                      
        try:
            self.game()
        except AssertionError as e:
            self._log_game_failure("AssertionError", e, game_params)
            raise
        except Exception as e:
            self._log_game_failure("Exception", e, game_params)
            raise

    def build_seller_intro(self):
        buyer = "random buyers" if self.is_myopic else self.player_2.public_name
        intro = f"You are {self.player_1.public_name}, a seller trying to sell products to {buyer} " \
                f"for ${self.product_price} each. "
        if self.is_myopic:
            intro += "We will relay your messages to the buyers."
        else:
            intro += f"We will relay your messages to {self.player_2.public_name}."
        return intro

    def build_cv_message(self):
        if self.is_seller_know_cv:
            self.buyer_cv = f"{self.player_1.public_name} knows how much each product worth to you."
            self.seller_cv = f"A high-quality product is worth ${pretty_number(self.v)} " \
                             f"to {self.player_2.public_name}, " \
                             f"and a low-quality product is worth only ${pretty_number(self.c)} to them."
        else:
            self.buyer_cv = f"{self.player_1.public_name} does not know how much each product worth to you."
            self.seller_cv = f"You do not know how much a high-quality product is worth " \
                             f"to {self.player_2.public_name}, " \
                             f"nor do you know how much a low-quality product is worth to them."

    def build_p_message(self):
        if self.is_buyer_know_p:
            msg = f"Each product in the game has a {self.p * 100:.2f}% chance of being high quality and " \
                  f"a {(1-self.p) * 100:.2f}% chance of being low quality."
            self.buyer_p = msg
            self.seller_p = f"and {self.player_2.public_name} knows this"
        else:
            self.buyer_p = f"You do not know what percentage of the products are of high quality."
            self.seller_p = f"and {self.player_2.public_name} does not know this"

    def generate_round_prior(self):
        seller_name = self.player_1.public_name
        if not self.is_myopic:
            text = f"For {self.total_rounds} rounds, in each round, {seller_name} " \
                   f"will randomly choose one of the products she is selling, reveal its true quality, " \
                   f"and then send you a recommendation regarding that product. " + \
                   f"You will decide whether to buy it or pass, in which case the product " \
                   f"will be thrown away and no one will ever be able to buy it. At the end of the round,"
        else:
            text = f"For each buyer, including yourself, {seller_name} randomly selects a product and reveals its " \
                   f"true quality. Based on the quality of the product, {seller_name} then provides you with a " \
                   f"recommendation regarding that specific product. Each buyer also have access to the seller’s " \
                   f"previous sales record: how many potential buyers there have been, how many products were sold, " \
                   f"and the proportion of high-quality products sold." \
                   "You must decide whether to buy the product or pass on it. If you pass, the product will be " \
                   "discarded, and no one will be able to buy it. After making your decision, "
        return text

    def create_myopic_know_statistics_message(self):
        if self.is_myopic:
            message = " or about any specific previous product, but they have statistics about your selling recoder: " \
                      "how many products you have sold, " \
                      "and how many of them are of high quality."
        else:
            message = ""
        return message

    def construct_player_info(self):
        self.build_p_message()
        self.build_cv_message()
        intro = self.build_seller_intro()
        player_info = dict()
        player_info['{{buyer_p_message}}'] = self.buyer_p
        player_info['{{buyer_cv_message}}'] = self.buyer_cv
        player_info['{{c}}'] = pretty_number(self.c)
        player_info['{{v}}'] = pretty_number(self.v)
        player_info['{{product_price}}'] = pretty_number(self.product_price)
        player_info['{{seller_intro}}'] = intro
        player_info['{{seller_p_message}}'] = self.seller_p
        player_info['{{seller_cv_message}}'] = self.seller_cv
        player_info['{{p}}'] = pretty_number(self.p * 100)
        player_info['{{total_rounds}}'] = f"{self.total_rounds}"
        player_info['{{buyer_v1}}'] = f'{self.player_2.public_name}, the buyer' if not self.is_myopic \
            else "random buyers"
        player_info['{{buyer_v2}}'] = self.player_2.public_name if not self.is_myopic else f"the buyers"
        player_info['{{buyer_v2_cap}}'] = player_info['{{buyer_v2}}'].capitalize()
        if self.is_myopic:
            player_info['{{buyer_v3}}'] = "one of the buyers"
        else:
            player_info['{{buyer_v3}}'] = f"{self.player_2.public_name}, the buyer"

        player_info['{{_seller_name}}'] = self.player_1.public_name
        player_info['{{rounds_prior}}'] = self.generate_round_prior()
        player_info['{{myopic_know_statistics}}'] = self.create_myopic_know_statistics_message()

        return player_info

    def build_offer_prompt(self, path='games/persuasion/prompts/format_prompt.json'):
        with open(path) as f:
            offer_prompt = json.load(f)
        if self.seller_message_type == "text":
            req_offer_text_player_1 = offer_prompt["seller_text"]
        elif self.seller_message_type == "binary":
            req_offer_text_player_1 = offer_prompt["seller_binary"]
        else:
            raise ValueError(f"Invalid seller message type: {self.seller_message_type}")
        req_offer_text_player_1 = req_offer_text_player_1.replace("{{rival_name}}",
                                                                  "the buyer" if self.is_myopic else
                                                                  self.player_2.public_name)
        if self.allow_buyer_message:
            req_offer_text_player_2 = offer_prompt["buyer_text"]
        else:
            req_offer_text_player_2 = offer_prompt["buyer_binary"]
        req_offer_text_player_2 = req_offer_text_player_2.replace("{{rival_name}}", self.player_1.public_name)
        return req_offer_text_player_1, req_offer_text_player_2

    @staticmethod
    def is_offer_in_format(string_action):
        pass                                                         

                
                                                       
           
                                                                         
        action_match = re.search(r'\{.*?\}', string_action, re.DOTALL)
        if not action_match:
            return False, "No JSON object found in response"

        action_str = action_match.group()

        try:
            action = json.loads(action_str)
        except json.JSONDecodeError as e:
            return False, f"JSON parse error: {e.msg} at position {e.pos}"

        if not isinstance(action, dict):
            return False, f"Expected dict, got {type(action).__name__}"

        if "message" not in action:
            return False, "Missing required key: 'message'"

        if not isinstance(action["message"], str):
            return False, f"message must be string, got {type(action['message']).__name__}"

        return True, ""

    def is_decision_in_format(self, string_action, player_type):
        pass                                                    

                
                                                       
           
        assert player_type in ["seller", "buyer"]

                                                                         
        action_match = re.search(r'\{.*?\}', string_action, re.DOTALL)
        if not action_match:
            return False, "No JSON object found in response"

        action_str = action_match.group()

        try:
            action = json.loads(action_str)
        except json.JSONDecodeError as e:
            return False, f"JSON parse error: {e.msg} at position {e.pos}"

        if not isinstance(action, dict):
            return False, f"Expected dict, got {type(action).__name__}"

                                                                        
        required_keys = ["decision"]
        if (player_type == "buyer" and self.allow_buyer_message) or \
           (player_type == "seller" and self.seller_message_type == "text"):
            required_keys.append("message")

        missing_keys = [k for k in required_keys if k not in action]
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

        if not isinstance(action["decision"], str):
            return False, f"decision must be string, got {type(action['decision']).__name__}"

        if action["decision"] not in ["yes", "no"]:
            return False, f"decision must be 'yes' or 'no', got '{action['decision']}'"

        return True, ""

    def is_buyer_decision_in_format(self, string_action):
        return self.is_decision_in_format(string_action, "buyer")

    def is_seller_decision_in_format(self, string_action):
        return self.is_decision_in_format(string_action, "seller")

    def generate_quality(self):
        return random.random() < self.p

    def quality_stats(self, is_quality):
        round_quality = "high-quality" if is_quality else "low-quality"
        product_worth = self.v if is_quality else self.c
        product_worth_str = pretty_number(product_worth)
        return round_quality, product_worth, product_worth_str

    def generate_seller_text(self, round_number, round_quality):
        new_buyer_msg = "A new potential buyer has arrived!\n" if self.is_myopic else ""
        seller_text = f"Round {round_number}\n" \
                      f"This round's product is {round_quality}.\n{new_buyer_msg}" + \
            (f"Send {'the potential buyer' if self.is_myopic else self.player_2.public_name} a message to help " +
             f"them decide whether to buy the product." if self.seller_message_type == "text" else
             f"Decide whether to recommend {'the buyer' if self.is_myopic else self.player_2.public_name} " +
             f"to buy the product.")
        return seller_text

    def seller_turn(self, round_number):
        is_quality = self.generate_quality()
        round_quality, product_worth, product_worth_str = self.quality_stats(is_quality)
        self.data_logger.add_action(player_name=NATURE_NAME,
                                    data={"round_quality": round_quality, "product_worth": product_worth},
                                    round_number=round_number)
        seller_text = self.generate_seller_text(round_number, round_quality)
        self.player_1.add_to_buffer(seller_text)
        self.player_1.edit_system_message(self.player_1.req_offer_text)
        self.player_1.act(self.is_offer_in_format if self.seller_message_type == "text"
                          else self.is_seller_decision_in_format)
        self.data_logger.add_action(player_name=self.player_1.public_name,
                                    data=self.player_1.last_action_json,
                                    round_number=round_number)
        return is_quality

    def generate_buyer_text(self, round_number, seller_content):
        if self.is_myopic:
            if self.sold_counter:
                buyer_intro_round = f"Statistics: Based on {self.player_1.public_name}'s recommendations, " + \
                                    f"{self.sold_counter} of the buyers purchased the products offered for them. " + \
                                    f"So far, {self.sold_quality_counter} high-quality product have been sold. " + \
                                    f"You can be the {add_ordinal_suffix(self.sold_counter+1)} buyer!\n~"
            else:
                buyer_intro_round = f"Statistics: No products have been sold yet. you can be the first one!\n~"
        else:
            buyer_intro_round = f"\n\nRound {round_number}"
        offer_text = f"{buyer_intro_round}\n"
        if self.seller_message_type == "text":
            seller_message = seller_content                                             
            offer_text += f"{self.player_1.public_name}'s message: {seller_message}"
        elif self.seller_message_type == "binary":
            seller_decision = seller_content                                              
            if seller_decision == "yes":
                offer_text += f"{self.player_1.public_name} recommends you to buy the product."
            elif seller_decision == "no":
                offer_text += f"{self.player_1.public_name} does not recommend you to buy the product."
            else:
                raise ValueError(f"Invalid seller decision: {seller_decision}")
        else:
            raise ValueError(f"Invalid seller message type: {self.seller_message_type}")
        offer_text += f'\n\nWould you like to buy the current product? \n'
        return offer_text

    def buyer_turn(self, round_number):
        seller_content = self.player_1.last_action_json["message"] if self.seller_message_type == "text" else \
            self.player_1.last_action_json["decision"]
        offer_text = self.generate_buyer_text(round_number, seller_content)
        self.player_2.add_to_buffer(offer_text)
        self.player_2.edit_system_message(self.player_2.req_offer_text)
        self.player_2.act(self.is_buyer_decision_in_format)
        self.data_logger.add_action(player_name=self.player_2.public_name,
                                    data=self.player_2.last_action_json,
                                    round_number=round_number)

    def generate_response_text(self, **kwargs):
        accepted = kwargs["accepted"]
        is_quality = kwargs["is_quality"]
        buyer_message = kwargs["buyer_message"]
        round_quality, product_worth, product_worth_str = self.quality_stats(is_quality)
        if accepted:
            seller_text = f"{self.player_2.public_name.capitalize()} bought the product!"
            buyer_response_text = \
                f"You bought the product from {self.player_1.public_name} for ${pretty_number(self.product_price)}!"
            buyer_quality_text = f"The product was {round_quality}. It's worth ${product_worth_str} for you."
        else:
            seller_text = f"{self.player_2.public_name.capitalize()} didn't bought the product."
            buyer_response_text = f"You didn't buy the product from {self.player_1.public_name}."
            buyer_quality_text = \
                f"The product was {round_quality}. It could have been worth ${product_worth_str} for you."
        if self.allow_buyer_message and buyer_message != "":
            buyer_msg = \
                f"\n{self.player_2.public_name.capitalize()}'s message: {buyer_message}"
        else:
            buyer_msg = None
        return seller_text, buyer_response_text, buyer_quality_text, buyer_msg

    def update_round(self, is_quality):
        accepted = self.player_2.last_action_json["decision"] == "yes"
        buyer_message = self.player_2.last_action_json["message"] if self.allow_buyer_message else ""
        seller_text, buyer_response_text, buyer_quality_text, buyer_msg = (
            self.generate_response_text(accepted=accepted, is_quality=is_quality, buyer_message=buyer_message))
        if buyer_msg:
            self.player_1.add_to_buffer(buyer_msg + "\n")
        self.player_1.add_to_buffer(seller_text)
        self.player_2.add_to_buffer(buyer_response_text + "\n")
        self.player_2.add_to_buffer(buyer_quality_text)
        if accepted:
            self.sold_counter += 1
            if is_quality:
                self.sold_quality_counter += 1

    def end_round(self, round_number):
        if round_number < self.total_rounds and self.is_myopic:
            self.player_2.end_chat()
            self.player_2.new_chat()
            self.player_1.add_to_buffer(f"\n{self.player_2.public_name} left. Waiting for the next buyer.".capitalize())
        self.player_1.add_to_buffer("\n\n")

    def game(self):
        for round_number in range(1, self.total_rounds + 1):
            is_quality = self.seller_turn(round_number)
            self.buyer_turn(round_number)
            self.update_round(is_quality)
            self.end_round(round_number)

        self.data_logger.save()
        self.player_1.end_chat()
        self.player_2.end_chat()
        self.player_1.clean_history()
        self.player_2.clean_history()
        print(f"Game over.")
