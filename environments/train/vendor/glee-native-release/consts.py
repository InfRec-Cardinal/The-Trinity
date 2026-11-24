import os

NATURE_NAME = "Nature"
HUMAN = "human"
BOT = "bot"
PROPOSER = "proposer"
RECEIVER = "receiver"
RESPONSE = "response"

OUTPUT_DIR = "Data"
DataStore = "DataStore"
HUMAN_DIR = os.path.join(DataStore, HUMAN)
VECTORS_DIR = os.path.join(DataStore, "vectors")

os.makedirs(OUTPUT_DIR, exist_ok=True)

OTREE_CONFIGS_PATH = "otree_game/configs"
OTREE_PAGES = "otree_game/pages"
OTREE_MAX_ROUNDS = 99
