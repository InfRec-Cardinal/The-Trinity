from players.base_player import Player
import random


class DemoPlayer(Player):
    pass                                                                                                    
    def __init__(self, public_name, player_id=3, game='bargaining',
                 delta=1, max_amount=1000, other_player_name='Alice', messages_allowed=True, always_reject=False,
                 seller_message_type='text', allow_buyer_message=True, max_rounds=3, jhon_caption="SellToJhon",
                 print_msg=False):
        super().__init__(public_name, delta, player_id)
        self.game = game
        self.turn_number = 0

        self.max_amount = max_amount
        self.other_player_name = other_player_name
        self.messages_allowed = messages_allowed
        self.always_reject = always_reject

        self.seller_message_type = seller_message_type
        self.allow_buyer_message = allow_buyer_message
        self.max_rounds = max_rounds
        self.jhon_caption = jhon_caption

        self.print_msg = print_msg

    def get_text_answer(self, format_checker, decision=False):
        self.turn_number += 1
        print("Demo turn number:", self.turn_number, "in game", self.game)
        if self.game == 'bargaining':
            rand = random.randint(0, 1)
            if rand and self.turn_number > 1 and not self.always_reject:
                accept_option = '{"decision": "accept"}'
            else:
                accept_option = '{"decision": "reject"}'
            if format_checker(accept_option):
                return accept_option
            else:
                offer = random.randint(0, self.max_amount)
                make_offer_option = ('{"' + self.public_name.lower() + '_gain": ' + str(offer) + ', "' +
                                     self.other_player_name.lower() + '_gain": ' + str(self.max_amount - offer) +
                                     ', "message": "I think this is a fair deal"}') if self.messages_allowed else '}'
                print("Offer:", make_offer_option)
                if format_checker(make_offer_option):
                    return make_offer_option
                else:
                    raise ValueError("Invalid format?!")
        elif self.game == 'persuasion':
            if self.seller_message_type == "text":
                msg = '{"message": "My message"}'
            elif self.seller_message_type == "binary":
                rand = random.randint(0, 1)
                msg = '{"decision": "yes"}' if rand else '{"decision": "no"}'
            else:
                raise ValueError(f"Invalid seller message type: {self.seller_message_type}")
            if format_checker(msg):
                return msg
            else:
                rand = random.randint(0, 1)
                if rand and self.turn_number > 1:
                    if self.allow_buyer_message:
                        decision_option = '{"decision": "yes", "message": "I accept"}'
                    else:
                        decision_option = '{"decision": "yes"}'
                else:
                    if self.allow_buyer_message:
                        decision_option = '{"decision": "no", "message": "I reject"}'
                    else:
                        decision_option = '{"decision": "no"}'
                if format_checker(decision_option):
                    return decision_option
                else:
                    raise ValueError(f"Invalid format: {decision_option}")
        elif self.game == 'negotiation':
            rand = random.randint(0, 2)
            if self.turn_number == self.max_rounds and rand == 1:
                rand = 0
            if rand == 0 and self.turn_number > 1:
                accept_option = ('{"decision": "' + self.jhon_caption
                                 + '", "message": "By"}' if self.messages_allowed else '"}')
            elif rand == 2 and self.turn_number > 1:
                accept_option = '{"decision": "AcceptOffer"' + ', "message": "Ok"}'
            else:             
                accept_option = ('{"decision": "RejectOffer"'
                                 + ', "message": "No"}' if self.messages_allowed else '}')
            if format_checker(accept_option):
                return accept_option
            else:
                offer = random.randint(0, self.max_amount)
                make_offer_option = ('{"product_price": ' + str(offer) +
                                     ', "message": "I think this is a fair deal"}' if self.messages_allowed else '}')
                if format_checker(make_offer_option):
                    return make_offer_option
                else:
                    raise ValueError("Invalid format?!")
        else:
            raise ValueError("Invalid game?!")

    def add_message(self, message, role):
        if self.print_msg:
            print("Message from", role, ":", message)

    def set_system_message(self, message):
        if self.print_msg:
            print("System message: ", message)

    def clean_conv(self):
        self.turn_number = 0
        if self.print_msg:
            print("Conversation cleaned")
