from players.base_player import Player


class OtreePlayer(Player):
    def __init__(self, public_name, delta=1.0, player_id=0):
        super().__init__(public_name, delta, player_id)

    def get_text_answer(self, format_checker, decision=False):
        raise Exception("Not supported")

    def add_message(self, message, role):
        pass

    def clean_conv(self):
        pass

    def new_chat(self):
        pass

    def edit_system_message(self, format_requested):
        pass

    def end_chat(self):
        pass
