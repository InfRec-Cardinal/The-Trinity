import json
import os
import traceback
from abc import ABC, abstractmethod
from utils.utils import create_prompts_from_templates
from players.base_player import Player


class Game(ABC):
    def __init__(self, player_1: Player, player_2: Player, data_logger, timeout=360):
        self.player_1 = player_1
        self.player_2 = player_2
        self.player_1.timeout = timeout
        self.player_2.timeout = timeout
        self.player_1_rules = ''
        self.player_2_rules = ''
        self.data_logger = data_logger

                                                 
        self.current_round = 0
        self.current_turn = None
        self.last_action = None

    def _log_game_failure(self, error_type, error, game_args=None):
        pass                                              
        print(f"\n{'='*60}")
        print(f"[GAME_FAILURE] {self.__class__.__name__} failed")
        print(f"{'='*60}")
        print(f"Error Type: {error_type}")
        print(f"Error Message: {str(error)}")
        print(f"Game ID: {self.data_logger.game_id}")
        print(f"\nGame State:")
        print(f"  Round: {self.current_round}")
        print(f"  Turn: {self.current_turn}")
        print(f"  Last Action: {self.last_action}")

        if game_args:
            print(f"\nGame Config:")
            for key, value in game_args.items():
                print(f"  {key}: {value}")

        print(f"\nPlayer States:")
        print(f"  Player 1 ({self.player_1.public_name}):")
        p1_response = getattr(self.player_1, 'response', None)
        print(f"    Last response: {p1_response[:200] if p1_response else 'None'}")
        print(f"    History length: {len(self.player_1.history)}")
        print(f"  Player 2 ({self.player_2.public_name}):")
        p2_response = getattr(self.player_2, 'response', None)
        print(f"    Last response: {p2_response[:200] if p2_response else 'None'}")
        print(f"    History length: {len(self.player_2.history)}")
        print(f"{'='*60}\n")

                                     
        try:
            output_path = self.data_logger._get_output_path()
            os.makedirs(output_path, exist_ok=True)
            failure_file = os.path.join(output_path, "failure_report.txt")
            with open(failure_file, 'w') as f:
                f.write(f"Game Failure Report\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"Error: {error_type} - {str(error)}\n")
                f.write(f"Game ID: {self.data_logger.game_id}\n")
                f.write(f"Game Type: {self.__class__.__name__}\n")
                f.write(f"Round: {self.current_round}\n")
                f.write(f"Turn: {self.current_turn}\n\n")

                f.write(f"Player 1 ({self.player_1.public_name}):\n")
                f.write(f"  Last response: {p1_response[:500] if p1_response else 'None'}\n")
                f.write(f"  History length: {len(self.player_1.history)}\n\n")

                f.write(f"Player 2 ({self.player_2.public_name}):\n")
                f.write(f"  Last response: {p2_response[:500] if p2_response else 'None'}\n")
                f.write(f"  History length: {len(self.player_2.history)}\n\n")

                f.write(f"Traceback:\n{traceback.format_exc()}\n")

                                          
            self.data_logger._save_partial_logs()
        except Exception as save_error:
            print(f"[WARNING] Failed to save failure report: {save_error}")

    def set_rules(self, prompt_path, infos, player='p1'):
        if '.txt' in prompt_path:
            with open(prompt_path, 'r') as f:
                prompt = f.read().strip()
        elif '.json' in prompt_path:
            with open(prompt_path, 'r') as f:
                prompts = json.load(f)
            prompt = prompts['seller'] if player == 'p1' else prompts['buyer']

        prompt = create_prompts_from_templates(prompt, infos)
        if player == 'p1':
            self.player_1_rules = prompt
        else:
            self.player_2_rules = prompt
        player = self.player_1 if player == 'p1' else self.player_2
        player.rules = prompt
        player.add_message(prompt, 'system')

    def add_format(self, prompt_path, infos, player='p1'):
        if '.txt' in prompt_path:
            with open(prompt_path, 'r') as f:
                prompt = f.read().strip()
        elif '.json' in prompt_path:
            with open(prompt_path, 'r') as f:
                prompts = json.load(f)
            prompt = prompts['seller'] if player == 'p1' else prompts['buyer']

        prompt = create_prompts_from_templates(prompt, infos)
        player = self.player_1 if player == 'p1' else self.player_2
        player.req_offer_text = prompt

    def get_other_player(self, base='p1'):
        base_player = self.player_1 if base == 'p1' else self.player_2
        other_player = self.player_2 if base == 'p1' else self.player_1
        return base_player, other_player

    @abstractmethod
    def game(self):
        pass
