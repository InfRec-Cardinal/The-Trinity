import argparse
import json
import os
import uuid
import main

WORK_WITH_WANDB = True
if WORK_WITH_WANDB:
    import wandb
    wandb.init(project="ManyGames")


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


                    
API_MODELS = ["openai", "claude"]

VERTEXAI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "publishers/meta/models/llama3-405b-instruct-maas"]

conv_templates = {"qwen": "qwen"}

                       
parser = argparse.ArgumentParser(description='Build JSON for game configuration')

                                   
parser.add_argument('--player_1_type', type=str, help='Type of player 1')
parser.add_argument('--player_2_type', type=str, help='Type of player 2')
parser.add_argument('--player_1_args_public_name', type=str, default='Alice', help='Public name of player 1')
parser.add_argument('--player_2_args_public_name', type=str, default='Bob', help='Public name of player 2')
parser.add_argument('--player_1_args_player_id', type=int, help='Player ID of player 1')
parser.add_argument('--player_2_args_player_id', type=int, help='Player ID of player 2', default=3)
parser.add_argument('--player_1_args_delta', type=float, help='Delta value for player 1', default=1.0)
parser.add_argument('--player_2_args_delta', type=float, help='Delta value for player 2', default=1.0)
parser.add_argument('--player_1_args_model_name', type=str, help='Model name for player 1')
parser.add_argument('--player_2_args_model_name', type=str, help='Model name for player 2')
parser.add_argument('--player_1_args_model_kwargs_num_gpus', type=int, help='Number of GPUs for player 1')
parser.add_argument('--player_2_args_model_kwargs_num_gpus', type=int, help='Number of GPUs for player 2')
parser.add_argument('--game_type', type=str, help='Type of the game',
                    choices=['persuasion', 'bargaining', 'negotiation'])

                 
parser.add_argument('--game_args_is_myopic', type=str2bool, help='Is the game myopic')
parser.add_argument('--game_args_product_price', type=int, help='Product price')
parser.add_argument('--game_args_p', type=float, help='Probability p')
parser.add_argument('--game_args_c', type=float, help='Cost c')
parser.add_argument('--game_args_v', type=float, help='Value v')
parser.add_argument('--game_args_total_rounds', type=int, help='Total rounds in the game')
parser.add_argument('--game_args_is_seller_know_cv', type=str2bool, help='Does the seller know cv')
parser.add_argument('--game_args_is_buyer_know_p', type=str2bool, help='Does the buyer know p')
parser.add_argument('--game_args_seller_message_type', type=str, help='Type of seller message')
parser.add_argument('--game_args_allow_buyer_message', type=str2bool, help='Allow buyer message')

                 
parser.add_argument('--game_args_complete_information', type=str2bool, help='Is the game complete information')
parser.add_argument('--game_args_messages_allowed', type=str2bool, help='Are messages allowed')
parser.add_argument('--game_args_money_to_divide', type=int, help='Money to divide')
parser.add_argument('--game_args_max_rounds', type=int, help='Maximum rounds')
parser.add_argument('--game_args_show_inflation_update', type=str2bool, help='Show inflation update')
parser.add_argument('--game_args_delta_1', type=float, help='Delta value for player 1 (discount factor)')
parser.add_argument('--game_args_delta_2', type=float, help='Delta value for player 2 (discount factor)')

                  
parser.add_argument('--game_args_seller_value', type=float, help='Seller value')
parser.add_argument('--game_args_buyer_value', type=float, help='Buyer value')
parser.add_argument('--game_args_product_price_order', type=float, help='Product price order')


parser.add_argument('-n', '--n_games', type=int, help='Number of games to play', default=1)

args = parser.parse_args()

                             
config = {}

if args.player_1_type:
    config["player_1_type"] = args.player_1_type
if args.player_2_type:
    config["player_2_type"] = args.player_2_type

player_1_args = {}
if args.player_1_args_public_name:
    player_1_args["public_name"] = args.player_1_args_public_name
if args.player_1_args_player_id:
    player_1_args["player_id"] = args.player_1_args_player_id
if args.player_1_args_delta:
    player_1_args["delta"] = args.player_1_args_delta
if args.player_1_args_model_name:
    player_1_args["model_name"] = args.player_1_args_model_name
    if args.player_1_args_model_name not in API_MODELS and args.player_1_args_model_name not in VERTEXAI_MODELS:
        player_1_args["model_kwargs"] = {}
        if args.player_1_args_model_kwargs_num_gpus:
            player_1_args["model_kwargs"]["num_gpus"] = args.player_1_args_model_kwargs_num_gpus
        config["player_1_type"] = "hf"
        if args.player_1_args_model_name in conv_templates.keys():
            player_1_args["model_conv_template"] = conv_templates[args.player_1_args_model_name]
    else:
        if args.player_1_args_model_name in VERTEXAI_MODELS:
            config["player_1_type"] = "vertexai"
        else:
            config["player_1_type"] = args.player_1_args_model_name


if player_1_args:
    config["player_1_args"] = player_1_args

player_2_args = {}
if args.player_2_args_public_name:
    player_2_args["public_name"] = args.player_2_args_public_name
if args.player_2_args_player_id:
    player_2_args["player_id"] = args.player_2_args_player_id
if args.player_2_args_delta:
    player_2_args["delta"] = args.player_2_args_delta
if args.player_2_args_model_name:
    player_2_args["model_name"] = args.player_2_args_model_name
    if args.player_2_args_model_name not in API_MODELS and args.player_2_args_model_name not in VERTEXAI_MODELS:
        player_2_args["model_kwargs"] = {}
        if args.player_2_args_model_kwargs_num_gpus:
            player_2_args["model_kwargs"]["num_gpus"] = args.player_2_args_model_kwargs_num_gpus
        config["player_2_type"] = "hf"
        if args.player_2_args_model_name in conv_templates.keys():
            player_2_args["model_conv_template"] = conv_templates[args.player_2_args_model_name]
    else:
        if args.player_2_args_model_name in VERTEXAI_MODELS:
            config["player_2_type"] = "vertexai"
        else:
            config["player_2_type"] = args.player_2_args_model_name

if player_2_args:
    config["player_2_args"] = player_2_args

game_args = {}
if args.game_type:
    config["game_type"] = args.game_type

                 
if args.game_args_is_myopic is not None:
    game_args["is_myopic"] = args.game_args_is_myopic
if args.game_args_product_price is not None:
    game_args["product_price"] = args.game_args_product_price
if args.game_args_p is not None:
    game_args["p"] = args.game_args_p
if args.game_args_c is not None:
    game_args["c"] = args.game_args_c
if args.game_args_v is not None:
    game_args["v"] = args.game_args_v
if args.game_args_total_rounds is not None:
    game_args["total_rounds"] = args.game_args_total_rounds
if args.game_args_is_seller_know_cv is not None:
    game_args["is_seller_know_cv"] = args.game_args_is_seller_know_cv
if args.game_args_is_buyer_know_p is not None:
    game_args["is_buyer_know_p"] = args.game_args_is_buyer_know_p
if args.game_args_seller_message_type:
    game_args["seller_message_type"] = args.game_args_seller_message_type
if args.game_args_allow_buyer_message is not None:
    game_args["allow_buyer_message"] = args.game_args_allow_buyer_message

                 
if args.game_args_complete_information is not None:
    game_args["complete_information"] = args.game_args_complete_information
if args.game_args_messages_allowed is not None:
    game_args["messages_allowed"] = args.game_args_messages_allowed
if args.game_args_money_to_divide is not None:
    game_args["money_to_divide"] = args.game_args_money_to_divide
if args.game_args_max_rounds is not None:
    game_args["max_rounds"] = args.game_args_max_rounds
if args.game_args_show_inflation_update is not None:
    game_args["show_inflation_update"] = args.game_args_show_inflation_update
if args.game_args_delta_1 is not None:
    game_args["delta_1"] = args.game_args_delta_1
if args.game_args_delta_2 is not None:
    game_args["delta_2"] = args.game_args_delta_2

                  
if args.game_args_seller_value is not None:
    game_args["seller_value"] = args.game_args_seller_value
if args.game_args_buyer_value is not None:
    game_args["buyer_value"] = args.game_args_buyer_value
if args.game_args_product_price_order is not None:
    game_args["product_price_order"] = args.game_args_product_price_order


if game_args:
    config["game_args"] = game_args

                          
print(json.dumps(config, indent=2))

                                                                                      
os.makedirs("tmp_config", exist_ok=True)

filename = f"tmp_config/{uuid.uuid4()}.json"
with open(filename, 'w') as f:
    f.write(json.dumps(config, indent=2))
print(f"Config saved to {filename}")

main.main(config_path=filename, n_games=args.n_games)
os.remove(filename)
