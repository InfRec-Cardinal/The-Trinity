import argparse
from collections import defaultdict
import json
from copy import deepcopy
from consts import *
import string
import random
import pandas as pd
import subprocess
import shutil
from datetime import datetime


def create_prompts_from_templates(template, info):
    new_prompt = deepcopy(template)
    for key in info:
        new_prompt = new_prompt.replace(key, f"{info[key]}")
    return new_prompt


def read_as_defaultdict(path, default_value=None):
    pass                                       
       
    with open(path, 'r') as f:
        data = json.load(f)

    def_dic = defaultdict(lambda: default_value)
    for key in data:
        def_dic[key] = data[key]
    return def_dic


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def pretty_number(x):
    x = f"{x:,.2f}"
    x = x.rstrip('0').rstrip('.')
    return x


class DataLogger:
    def __init__(self, player_1, player_2, **args):
        self.player_1 = player_1
        self.player_2 = player_2
        self.actions = []
        self.game_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        self.args = args
        self.partial_save_enabled = True                                   
        self._partial_save_counter = 0
        self._output_path = None

    def _get_output_path(self):
        pass                                             
        if self._output_path is None:
            sub_folders = "/".join(self.game_id[:3])
            exp_name_path = self.args.get('experiment_name', 'default')
            self._output_path = f"{OUTPUT_DIR}/{exp_name_path}/{self.args['game_type']}/{sub_folders}/{self.game_id}"
        return self._output_path

    def add_action(self, **kwargs):
        player_name, data, round_number = kwargs['player_name'], kwargs['data'], kwargs['round_number']
        data["player"] = player_name
        data["round"] = round_number
        self.actions.append(data)

                                                
        self._partial_save_counter += 1
        if self.partial_save_enabled and self._partial_save_counter % 5 == 0:
            self._save_partial_logs()

    def _save_partial_logs(self):
        pass                                                 
        try:
            output_path = self._get_output_path()
            partial_dir = os.path.join(output_path, ".partial")
            os.umask(0o002)
            os.makedirs(partial_dir, exist_ok=True)

                              
            for player_id, player in [(1, self.player_1), (2, self.player_2)]:
                if player.history:
                    filename = os.path.join(partial_dir, f"log_player_{player_id}.csv")
                    df = pd.DataFrame(player.history, columns=['prompt', 'response'])
                    df.to_csv(filename, index=False)

                                 
            if self.actions:
                actions_df = pd.DataFrame(self.actions)
                actions_df.to_csv(os.path.join(partial_dir, "game.csv"), index=False)

                         
            config = dict(self.args)
            config['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config['commit'] = get_commit_hash()
            config['partial'] = True                        
            with open(os.path.join(partial_dir, "config.json"), 'w') as f:
                json.dump(config, f)

        except Exception as e:
            print(f"[WARNING] Failed to save partial logs: {e}")

    def save(self):
        output_path = self._get_output_path()
        os.umask(0o002)
        os.makedirs(output_path, exist_ok=True)

                                                                                  
        partial_dir = os.path.join(output_path, ".partial")
        if os.path.exists(partial_dir):
            try:
                shutil.rmtree(partial_dir)
            except Exception as e:
                print(f"[WARNING] Failed to remove partial logs: {e}")

        with open(f"{output_path}/config.json", 'w') as f:
                                                                                      
            self.args['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                                                          
            self.args['commit'] = get_commit_hash()
            json.dump(self.args, f)

        player_1_log = pd.DataFrame(self.player_1.history, columns=['prompt', 'response'])
        player_2_log = pd.DataFrame(self.player_2.history, columns=['prompt', 'response'])
        player_1_log.to_csv(f"{output_path}/log_player_1.csv", index=False)
        player_2_log.to_csv(f"{output_path}/log_player_2.csv", index=False)
        actions_df = pd.DataFrame(self.actions)
        actions_df.to_csv(f"{output_path}/game.csv", index=False)


def get_commit_hash():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).strip().decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def add_ordinal_suffix(n):
                                 
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
                                                      
        last_digit = n % 10
        if last_digit == 1:
            suffix = "st"
        elif last_digit == 2:
            suffix = "nd"
        elif last_digit == 3:
            suffix = "rd"
        else:
            suffix = "th"
    return f"{n}{suffix}"
