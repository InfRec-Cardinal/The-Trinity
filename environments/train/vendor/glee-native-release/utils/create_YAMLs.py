from collections import defaultdict
import math

llms_and_gpus = {
    "meta-llama/Meta-Llama-3.1-8B-Instruct": 0.5,
    "meta-llama/Meta-Llama-3-8B-Instruct": 0.5,
    "microsoft/Phi-3.5-mini-instruct": 0.25,
    "publishers/meta/models/llama3-405b-instruct-maas": 0,
    "Qwen/Qwen2-7B-Instruct": 0.5,
    "gemini-1.5-flash": 0,
    "gemini-1.5-pro": 0}
assert sum([g > 0.5 for g in llms_and_gpus.values()]) <= 1

gpu_runs = defaultdict(lambda: defaultdict(set))
for llm_1 in llms_and_gpus.keys():
    for llm_2 in llms_and_gpus.keys():
        needs = llms_and_gpus[llm_1]
        if llm_1 != llm_2:
            needs = (needs, llms_and_gpus[llm_2])
        gpu_runs[needs]["alice"].add(llm_1)
        gpu_runs[needs]["bob"].add(llm_2)

bargaining_yaml = """# sweep_config.yaml
program: utils/create_config_and_run.py
method: grid
project: ManyGamesData
name: Bargaining Sweep - {n_gpu} GPUs - Sweep {N}
parameters:
  game_type:
    values: ["bargaining"]
  player_1_args_model_name:
    values: {alice_list}
  player_2_args_model_name:
    values: {bob_list}
  player_1_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_2_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_1_args_delta:
    values: [1, 0.95, 0.9, 0.8]
  player_2_args_delta:
    values: [1, 0.95, 0.9, 0.8]
  game_args_money_to_divide:
    values: [100, 10_000, 1_000_000]
  game_args_max_rounds:
    values: [99, 12]
  game_args_complete_information:
    values: [True, False]
  game_args_messages_allowed:
    values: [True, False]
  n_games:
    values: [30]
  game_args_show_inflation_update:
    values: [True]"""

persuasion_yaml = """# sweep_config.yaml
program: utils/create_config_and_run.py
method: grid
project: ManyGamesData
name: Persuasion Sweep - {n_gpu} GPUs - Sweep {N}
parameters:
  game_type:
    values: ["persuasion"]
  player_1_args_model_name:
    values: {alice_list}
  player_2_args_model_name:
    values: {bob_list}
  player_1_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_2_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_1_args_delta:
    values: [1]
  player_2_args_delta:
    values: [1]
  game_args_p:
    values: [1/3, 0.5, 0.8]
  game_args_c:
    values: [0]
  game_args_v:
    values: [1.2, 1.25, 2, 3, 4]
  product_price:
    values: [100, 10_000, 1_000_000]
  game_args_total_rounds:
    values: [25]
  game_args_is_seller_know_cv:
    values: [True, False]
  game_args_is_buyer_know_p:
    values: [True]
  game_args_seller_message_type:
    values: ["text", "binary"]
  game_args_is_myopic:
    values: [True, False]
  n_games:
    values: [30]
  game_args_allow_buyer_message:
    values: [True]"""

negotiation_yaml = """# sweep_config.yaml
program: utils/create_config_and_run.py
method: grid
project: ManyGamesData
name: Negotiation Sweep - {n_gpu} GPUs - Sweep {N}
parameters:
  game_type:
    values: ["negotiation"]
  player_1_args_model_name:
    values: {alice_list}
  player_2_args_model_name:
    values: {bob_list}
  player_1_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_2_args_model_kwargs_num_gpus:
    values: [{n_gpu}]
  player_1_args_delta:
    values: [1]
  player_2_args_delta:
    values: [1]
  game_args_seller_value:
    values: [0.8, 1, 1.2, 1.5]
  game_args_buyer_value:
    values: [0.8, 1, 1.2, 1.5]
  game_args_v:
    values: [0]
  game_args_product_price_order:
    values: [100, 10_000, 1_000_000]
  game_args_max_rounds:
    values: [1, 10, 30]
  game_args_messages_allowed:
    values: [True, False]
  game_args_complete_information:
    values: [True, False]
  n_games:
    values: [30]
  game_args_allow_buyer_message:
    values: [True]"""

gpu_runs = defaultdict(lambda: {"alice": set(), "bob": set()})


assert sum([g > 0.5 for g in llms_and_gpus.values()]) <= 1


def how_many_gpus(llm1, llm2):
    cur_needs = llms_and_gpus[llm1]
    if llm1 != llm2:
        cur_needs = cur_needs + llms_and_gpus[llm_2]
    cur_needs = math.ceil(cur_needs)
    return cur_needs


gpus_groups = defaultdict(set)
for llm, gpus in llms_and_gpus.items():
    gpus_groups[gpus].add(llm)


def create_run(game_type, yaml_text, cur_N=0, cur_n_gpu=0, alice_list=None, bob_list=None):
    assert game_type.lower() in yaml_text.lower()
    alice_list = alice_list if alice_list else []
    bob_list = bob_list if bob_list else []
    yaml_text = yaml_text.format(N=cur_N, n_gpu=cur_n_gpu, alice_list=alice_list, bob_list=bob_list)
    with open(f"My_YAML/{cur_N}_{cur_n_gpu}GPU.yaml", "w") as f:
        f.write(yaml_text)
    print(yaml_text)
    suffix = f"_{cur_n_gpu}GPU" if cur_n_gpu else ""
    print(f"Run {cur_N}: sbatch run_sweep_DGX{suffix}.sh --GPUS={cur_n_gpu} --max-runs=5000 --agent-id=")


N = 0
total_comb = 0
combs = []

for n_gpu_A, models_A in gpus_groups.items():
    for n_gpu_B, models_B in gpus_groups.items():
        n_gpu = n_gpu_A + n_gpu_B if n_gpu_A != n_gpu_B else n_gpu_B
        n_gpu = math.ceil(n_gpu)
        for game_name, game_yaml in [("bargaining", bargaining_yaml), ("persuasion", persuasion_yaml),
                                     ("negotiation", negotiation_yaml)]:
            create_run(game_name, game_yaml, N, cur_n_gpu=math.ceil(n_gpu), alice_list=list(models_A),
                       bob_list=list(models_B))
            N += 1
        total_comb += len(models_A) * len(models_B)
