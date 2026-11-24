import os.path
from players.base_player import Player
import re
import json
from games.base_game import Game
from utils.utils import pretty_number


class NegotiationGame(Game):
    def __init__(self, player_1: Player, player_2: Player, data_logger,
                 max_rounds: int,
                 seller_value: float,
                 buyer_value: float,
                 complete_information: bool,
                 product_price_order: int,                                                           
                 messages_allowed: bool,
                 timeout=60):
        super().__init__(player_1, player_2, data_logger, timeout)
        self.max_rounds = max_rounds
        self.player_1.final_value = product_price_order * seller_value
        self.player_2.final_value = product_price_order * buyer_value
        self.complete_information = complete_information
        self.messages_allowed = messages_allowed

        assert player_1.public_name != player_2.public_name, "Players should have different names"

        self.player_1.new_chat()
        self.player_2.new_chat()

        p1_rules, p1_action = self.construct_player_info('p1')
        p2_rules, p2_action = self.construct_player_info('p2')

        self.all_names = [self.player_1.public_name, self.player_2.public_name]

        path = 'games/negotiation/prompts/'
        self.set_rules(os.path.join(path, 'rules_prompt.json'), p1_rules, 'p1')
        self.set_rules(os.path.join(path, 'rules_prompt.json'), p2_rules, 'p2')

        self.add_format(os.path.join(path,
                                     'offer_format.json' if self.messages_allowed else
                                     'offer_format_messages_unallowed.json'),
                        p1_action, 'p1')
        self.add_format(os.path.join(path,
                                     'offer_format.json' if self.messages_allowed else
                                     'offer_format_messages_unallowed.json'),
                        p2_action, 'p2')

        self.player_1.deal_with_jhon_text = "Sell the product to Jhon for ${}".format(
            pretty_number(self.player_1.final_value))
        self.player_2.deal_with_jhon_text = "Buy the product from Jhon for ${}".format(
            pretty_number(self.player_2.final_value))
        self.player_1.deal_with_jhon_caption = "SellToJhon"
        self.player_2.deal_with_jhon_caption = "BuyFromJhon"
        self.player_1.act_name = "sell the product"
        self.player_2.act_name = "buy the product"

                                         
        base_game_params = {
            "max_rounds": max_rounds,
            "complete_information": complete_information,
            "product_price_order": product_price_order,
            "messages_allowed": messages_allowed
        }

        if complete_information:
                                                   
            player_1_params = {
                **base_game_params,
                "role": "seller",
                "seller_value": seller_value,
                "buyer_value": buyer_value
            }
            player_2_params = {
                **base_game_params,
                "role": "buyer",
                "seller_value": seller_value,
                "buyer_value": buyer_value
            }
        else:
                                                    
            player_1_params = {**base_game_params, "role": "seller", "seller_value": seller_value}
            player_2_params = {**base_game_params, "role": "buyer", "buyer_value": buyer_value}

        self.player_1.set_game_params(player_1_params)
        self.player_2.set_game_params(player_2_params)

                                             
        game_params = {
            "max_rounds": max_rounds,
            "seller_value": seller_value,
            "buyer_value": buyer_value,
            "complete_information": complete_information,
            "product_price_order": product_price_order,
            "messages_allowed": messages_allowed
        }

                                      
        try:
            self.game()
        except AssertionError as e:
            self._log_game_failure("AssertionError", e, game_params)
            raise
        except Exception as e:
            self._log_game_failure("Exception", e, game_params)
            raise

    def build_next_rounds_info_seller(self, seller_value, other_player_name):
        if self.max_rounds == 1:
            message = f"If {other_player_name} rejects the offer, you will sell the product to another buyer, John, "
        else:
            message = f"If {other_player_name} rejects the offer, he can make a counteroffer to buy your product. " \
                      "You can either accept or reject his counteroffer. " \
                      f"If you reject {other_player_name}'s counteroffer, you can make a new counteroffer, and so on.\n"
            if self.max_rounds <= 20:
                message += f"You have {self.max_rounds} rounds to close the deal. However, "
            first_a = "A" if message.strip()[-1] == "." else "a"
            message += f"{first_a}t any moment, " \
                       f"you can choose to stop the negotiation with {other_player_name} " \
                       f"and sell the product to another buyer, John, "
        message += f"who is willing to buy the product from you for ${pretty_number(seller_value)}."
        return message

    def build_next_rounds_info_buyer(self, buyer_value, other_player_name):
        if self.max_rounds == 1:
            message = f"If you reject the offer, you will buy the product from another seller, John, "
        else:
            message = f"If you reject the offer, you can make a counteroffer to buy the product. " \
                      f"{other_player_name} can either accept or reject your counteroffer. " \
                      f"If {other_player_name} rejects your counteroffer, " \
                      f"{other_player_name} can make a new counteroffer, and so on. "
            if self.max_rounds <= 20:
                message += f"\nYou have {self.max_rounds} rounds to close the deal. However, "
            first_a = "A" if message.strip()[-1] == "." else "a"
            message += f"{first_a}t any moment, you can choose to stop the negotiation with {other_player_name}" \
                       f" and buy the product from another seller, John, "
        message += f"who is willing to sell the product to you for ${pretty_number(buyer_value)}."
        return message

    def get_other_player(self, base='p1'):
        base_player = self.player_1 if base == 'p1' else self.player_2
        other_player = self.player_2 if base == 'p1' else self.player_1
        return base_player, other_player

    def construct_player_info(self, player='p1'):
        base_player, other_player = self.get_other_player(player)
        rules_info = dict()

        rules_info['{{player_name}}'] = base_player.public_name
        rules_info['{{rival_name}}'] = other_player.public_name
        rules_info['{{complete_information_message}}'] = self.complete_information_message(other_player)
        rules_info['{{self_final_value}}'] = pretty_number(base_player.final_value)
        rules_info['{{next_rounds_info_seller}}'] = self.build_next_rounds_info_seller(base_player.final_value, 
                                                                                       other_player.public_name)
        rules_info['{{next_rounds_info_buyer}}'] = self.build_next_rounds_info_buyer(base_player.final_value, 
                                                                                     other_player.public_name)

        action_info = dict()
        action_info['{{rival_name}}'] = other_player.public_name
        return rules_info, action_info

    def complete_information_message(self, other_player):
        if self.complete_information:
            return f"The product is worth ${pretty_number(other_player.final_value)} to {other_player.public_name}. "
        else:
            return f"You don't know the value of the product to {other_player.public_name}. "

    @staticmethod
    def lower_name(name):
        return name.lower().replace(" ", "_")

    def is_offer_in_format(self, string_action):
        pass                                                 

                
                                                       
           
                                                                         
        action_match = re.search(r'\{.*?\}', string_action, re.DOTALL)
        if not action_match:
            return False, "No JSON object found in response"

        action_str = action_match.group()
        action_str = re.sub(r"(?<=\d),(?=\d{3})", "", action_str)

                                                            
        action = None
        for attempt in range(2):
            try:
                action = json.loads(action_str)
                break
            except json.JSONDecodeError as e:
                if "$" in action_str and attempt == 0:
                    action_str = action_str.replace("$", "")
                else:
                    return False, f"JSON parse error: {e.msg} at position {e.pos}"

        if not isinstance(action, dict):
            return False, f"Expected dict, got {type(action).__name__}"

                             
        required_keys = ["product_price"] + (["message"] if self.messages_allowed else [])
        missing_keys = [k for k in required_keys if k not in action]
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

                                  
        if not isinstance(action["product_price"], (int, float, str)):
            return False, f"product_price must be number or string, got {type(action['product_price']).__name__}"

                                                                
        if isinstance(action["product_price"], str):
            try:
                float(action["product_price"].replace("$", ""))
            except ValueError:
                return False, f"product_price string '{action['product_price']}' cannot be converted to number"

                                        
        if self.messages_allowed and not isinstance(action["message"], str):
            return False, f"message must be string, got {type(action['message']).__name__}"

        return True, ""

    @staticmethod
    def is_decision_in_format(string_action):
        pass                                                    

                
                                                       
           
        VALID_DECISIONS = ["DealWithJhon", "AcceptOffer", "SellToJhon", "BuyFromJhon", "RejectOffer"]

                                                           
        action_str = string_action
        action = None
        for attempt in range(2):
            action_match = re.search(r'\{.*?\}', action_str, re.DOTALL)
            if not action_match:
                return False, "No JSON object found in response"

            try:
                action = json.loads(action_match.group())
                break
            except json.JSONDecodeError as e:
                if "$" in action_str and attempt == 0:
                    action_str = action_str.replace("$", "")
                else:
                    return False, f"JSON parse error: {e.msg} at position {e.pos}"

        if not isinstance(action, dict):
            return False, f"Expected dict, got {type(action).__name__}"

        if "decision" not in action:
            return False, "Missing required key: 'decision'"

        if not isinstance(action["decision"], str):
            return False, f"decision must be string, got {type(action['decision']).__name__}"

        if action["decision"] not in VALID_DECISIONS:
            return False, f"decision must be one of {VALID_DECISIONS}, got '{action['decision']}'"

        return True, ""

    def is_decision_in_format_yes_no(self, string_action):
        return self.is_decision_in_format(string_action)

    @staticmethod
    def get_offer_text(player, round_number):
        text = player.req_offer_text
        if round_number == 1:               
            text = text.replace("{{offer_type}}", "offer")
        else:
            text = text.replace("{{offer_type}}", "counteroffer")
        return text

    def get_proposer_text(self, **kwargs):
        round_number, proposer, receiver = kwargs["round_number"], kwargs["proposer"], kwargs["receiver"]
        proposer_message_format = self.get_offer_text(proposer, round_number)
        proposer_text = (
                (f"Round {round_number}\n" if 1 < self.max_rounds <= 20 else "")
                + f"Send your {'counter' if round_number > 1 else ''}offer to {receiver.public_name}. \n")
        return proposer_message_format, proposer_text

    def proposer_turn(self, **kwargs):
        round_number, receiver, proposer = kwargs["round_number"], kwargs["receiver"], kwargs["proposer"]
        proposer_message_format, proposer_text = self.get_proposer_text(round_number=round_number,
                                                                        proposer=proposer,
                                                                        receiver=receiver)
        proposer.add_to_buffer(proposer_text)
        proposer.edit_system_message(proposer_message_format)
        proposer.act(self.is_offer_in_format)
        self.data_logger.add_action(player_name=proposer.public_name,
                                    data=proposer.last_action_json,
                                    round_number=round_number)

    def get_receiver_text(self, **kwargs):
        (round_number, proposer_name,
         receiver_jhon_caption, receiver_act_name, receiver_jhon_text, counteroffer_is_option) = \
            (kwargs["round_number"], kwargs["proposer_name"],
             kwargs["receiver_jhon_caption"], kwargs["receiver_act_name"], kwargs["receiver_jhon_text"],
             kwargs["counteroffer_is_option"])
        proposer_message_part = {"proposer_offer": kwargs["proposer_offer"]}
        if self.messages_allowed:
            proposer_message_part["proposer_message"] = kwargs["proposer_message"]
        receiver_message_format = f"Answer with {{\"decision\": \"AcceptOffer\"}}, " + \
                                  (f"or {{\"decision\": \"RejectOffer\"}}, "
                                   if counteroffer_is_option else f"or {{\"decision\": \"RejectOffer\"}}, ") + \
                                  f"or {{\"decision\": \"{receiver_jhon_caption}\"}}"
        receiver_text = (
                (f"Round {round_number}\n" if 1 < self.max_rounds <= 20 else "")
                + f"{proposer_name}'s offer:"
                + (f"\n# {proposer_name}'s message: {proposer_message_part['proposer_message']} \n" +
                   f"# {proposer_name}'s offer:" if self.messages_allowed
                   else "") + f" The product price will be ${pretty_number(proposer_message_part['proposer_offer'])}. \n" +
                f"You have three options:\n"
                f"(1) Accept {proposer_name}'s offer, and {receiver_act_name} for ${pretty_number(proposer_message_part['proposer_offer'])}\n" +
                (f"(2) Reject {proposer_name}'s offer and proceed to the next round, where you will send "
                 f"{proposer_name} a counteroffer\n"
                 if counteroffer_is_option else f"(2) Reject {proposer_name}'s offer\n") +
                f"(3) {receiver_jhon_text}\n")
        return receiver_message_format, receiver_text

    def receiver_turn(self, **kwargs):
        round_number, receiver, proposer = kwargs["round_number"], kwargs["receiver"], kwargs["proposer"]
        proposer_message_parts = {"proposer_offer": proposer.last_action_json['product_price']}
        if self.messages_allowed:
            proposer_message_parts["proposer_message"] = proposer.last_action_json['message']
        receiver_jhon_caption, receiver_act_name, receiver_jhon_text = \
            (receiver.deal_with_jhon_caption, receiver.act_name, receiver.deal_with_jhon_text)
        counteroffer_is_option = round_number < self.max_rounds
        receiver_message_format, receiver_text = self.get_receiver_text(round_number=round_number,
                                                                        proposer_name=proposer.public_name,
                                                                        receiver_jhon_caption=receiver_jhon_caption,
                                                                        receiver_act_name=receiver_act_name,
                                                                        receiver_jhon_text=receiver_jhon_text,
                                                                        counteroffer_is_option=counteroffer_is_option,
                                                                        **proposer_message_parts)
        receiver.add_to_buffer(receiver_text)
        receiver.edit_system_message(receiver_message_format)
        receiver.act(self.is_decision_in_format)
        self.data_logger.add_action(player_name=receiver.public_name,
                                    data=receiver.last_action_json,
                                    round_number=round_number)

    def get_response_text(self, **kwargs):
        round_number, decision, proposer_name, receiver_name = \
            kwargs["round_number"], kwargs["decision"], kwargs["proposer_name"], kwargs["receiver_name"]
        response_texts = {}
        if decision == "AcceptOffer":
            response_texts["proposer"] = f"{receiver_name} accepted your offer."
            response_texts["receiver"] = f"You accepted {proposer_name}'s offer."
        elif decision == "RejectOffer" and round_number < self.max_rounds:
            response_texts["proposer"] = f"{receiver_name} rejected your offer from round {round_number}.\n\n"
            response_texts["receiver"] = f"You chose to make a counteroffer to {proposer_name}.\n\n"
        elif decision == "RejectOffer":                                       
            response_texts["proposer"] = (f"{receiver_name} rejected your offer from round {round_number}"
                                          f" and ended the negotiation.\n\n")
            response_texts["receiver"] = f"You chose to reject {proposer_name}'s offer and end the negotiation.\n\n"
        else:                  
            response_texts["proposer"] = (f"{receiver_name} rejected your offer from round {round_number}"
                                          f" and ended the negotiation.\n\n")
            response_texts["receiver"] = f"You chose to buy the product from the another seller, John.\n\n" \
                if "Buy" in decision else \
                f"You chose to sell the product to the another buyer, John.\n\n"
        return response_texts

    def update_round(self, **kwargs):
        round_number, receiver, proposer = kwargs["round_number"], kwargs["receiver"], kwargs["proposer"]
        decision = receiver.last_action_json["decision"]
        response_texts = self.get_response_text(round_number=round_number, decision=decision,
                                                proposer_name=proposer.public_name,
                                                receiver_name=receiver.public_name)
        proposer.add_to_buffer(response_texts["proposer"])
        receiver.add_to_buffer(response_texts["receiver"])
        game_end = 2 if decision == "AcceptOffer" else (1 if decision == "RejectOffer" else 0)
        return game_end

    def game(self):
        for round_number in range(1, self.max_rounds + 1):
            proposer = self.player_1 if round_number % 2 else self.player_2
            receiver = self.player_2 if round_number % 2 else self.player_1

            self.proposer_turn(round_number=round_number, proposer=proposer, receiver=receiver)

            self.receiver_turn(round_number=round_number, receiver=receiver, proposer=proposer)

            game_end = self.update_round(round_number=round_number, receiver=receiver, proposer=proposer)
            if game_end != 1:                        
                if game_end == 2:                     
                    print(f"{receiver.public_name} accepted the offer!")
                else:                             
                    print(f"{receiver.public_name} rejected the offer and chose not to make a counteroffer.")
                break
        else:
            print(f"Game over. There is no agreement after {self.max_rounds} rounds.")
        self.data_logger.save()
        self.player_1.end_chat()
        self.player_2.end_chat()
        self.player_1.clean_history()
        self.player_2.clean_history()
