from players.base_player import Player


class TerminalPlayer(Player):
    def __init__(self, public_name, delta=1.0, player_id=0):
        super().__init__(public_name, delta, player_id)

    def get_text_answer(self, format_checker, decision=False):
        for i in range(5):
            text = input()
            if format_checker(text):
                return text
            else:
                print("Invalid input. Please try again.")
        else:
            raise Exception("Failed to get a valid response in 5 attempts.")

    def add_message(self, message, role):
        if role == 'system':
            self.buffer += message

    def clean_conv(self):
        pass

    def set_system_message(self, message):
        pass
