import os

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from itertools import product
from tqdm import tqdm
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import joblib
import patsy

llm_short_names = {
    "human": "Human",
    "Qwen/Qwen2-7B-Instruct": "Qwen-2",
    "meta-llama/Meta-Llama-3-8B-Instruct": "Lam-3",
    "meta-llama/Meta-Llama-3.1-8B-Instruct": "Lam-3.1",
    "gemini-1.5-flash": "Gem-F",
                                
}

class Metrics:
    def __init__(self, config_with_statistics_path, family_name, player_1_name, player_2_name, drop_unknown_llms=True):
                            
        data_columns = pd.read_csv(config_with_statistics_path, index_col=0, nrows=0).columns
        skip_columns = ['name_0', 'display_name_0', 'title_0', 'description_0', 'qualification_id_0', 'qualification_base_0', 'date_0', 'game_args_show_inflation_update']
        use_columns = [c for c in data_columns if c not in skip_columns]
        
        self.data = pd.read_csv(config_with_statistics_path, usecols=use_columns)       
        self.game_name = family_name
        self.player_1_name = player_1_name
        self.player_2_name = player_2_name
        self.modes = [player_1_name, player_2_name]
        self.metrics = {m: [] for m in self.modes}
        self.metrics_range = {}
        self.undefined_metrics = []                                   

        self.config_params_to_drop = []
        self.interaction_features_couples = []

        commit_col = [c for c in self.data.columns if "commit" in c][0]
        columns_to_drop = ["player_1_args_model_kwargs", "player_2_args_model_kwargs", commit_col, "player_2_args_player_id"]
        self.data = self.data.drop(columns=[c for c in columns_to_drop if c in self.data.columns])

        if drop_unknown_llms:
            self.drop_other_llm(eligible_llms=llm_short_names.keys())
        self.calculate_metrics()
        self.grouped_data = {}


    def add_to_drop(self, param):
        assert not self.grouped_data                                               
        self.config_params_to_drop.append(param)

    def set_modes(self, modes):
        self.modes = modes

    def drop_other_llm(self, eligible_llms):
                                                      
        print("Dropping the following LLMs:", end=" ")
        print((set(self.data["player_1_args_model_name"].unique()) | set(self.data["player_2_args_model_name"].unique()) )- set(eligible_llms))
        self.data = self.data[(self.data["player_1_args_model_name"].isin(eligible_llms)) & (self.data["player_2_args_model_name"].isin(eligible_llms))]

    def get_all_tables(self):
        assert self.modes is not None
        return [self.get_statistics(m) for m in self.modes]

    def calculate_metrics(self):
        raise NotImplementedError

    def get_llms(self, player="all"):
        assert player in [1, 2, "all"]
        player_1_llms = self.data["player_1_args_model_name"].dropna().unique()
        player_2_llms = self.data["player_2_args_model_name"].dropna().unique()
        if player == 1:
            return list(set(player_1_llms))
        elif player == 2:
            return list(set(player_2_llms))
        else:
            return list(set(player_1_llms) | set(player_2_llms))

    def drop_metrics(self, mode, metrics):
        assert mode in self.modes
        for metric in metrics:
            self.metrics[mode].remove(metric)

    def calc_grouped_data(self, mode):
        assert mode in self.modes
        metrics = list(self.metrics[mode].keys())
        grouped_data = self.complete_missing_groups(self.data, metrics, mode)
        self.grouped_data[mode] = grouped_data

    def get_statistics(self, mode, group_by=None):
        if group_by is None:
            group_by = []
        if mode not in self.grouped_data:
            self.calc_grouped_data(mode)

        group_by = [group_by] if isinstance(group_by, str) else group_by

        grouped_data = self.grouped_data[mode]
        player_param = "player_1_args_model_name" if mode == self.player_1_name else "player_2_args_model_name"
        metrics = list(self.metrics[mode].keys())
        rename_dict = self.metrics[mode]
                                                                                    
        return grouped_data.groupby([player_param] + group_by)[metrics].mean().rename(columns=rename_dict).T

    def plot_graphs(self, mode, group_by=None, metrics_to_plot="all"):
        os.makedirs(f"output/plots/game_params/{self.game_name}/{mode}", exist_ok=True)
        if group_by is None:
            group_by = []
        if isinstance(group_by, str):
            group_by = [group_by]
        assert any([arg in self.get_game_args() for arg in group_by])
        if mode not in self.grouped_data:
            self.calc_grouped_data(mode)

        stats = self.get_statistics(mode, group_by).T

        if metrics_to_plot == "all":
            metrics = list(self.metrics[mode].values())
        else:
            metrics = [m for m in self.metrics[mode].values() if m in metrics_to_plot]
        gb_text = "_".join(sorted([gb.capitalize() for gb in group_by]))

        def plot_subgraph(ax, data, metric):
            data_kind = 'line' if data.index.dtype == np.float64 and "price_order" not in data.index.name else 'bar'
            if data_kind == 'bar':
                data = data.T
            data.plot(kind=data_kind, ax=ax)
            ax.set_xlabel(gb_text)
            if data_kind == 'line':
                ax.set_xticks(data.index)
            ax.set_ylabel(metric)
                                                                        
            ax.set_ylim([data.min().min() * (0.9 if data.min().min() > 0 else 1.1), data.max().max() * (1.1 if data.max().max() > 0 else 0.9)])

                                                 
        fig, axs = plt.subplots(len(self.modes), len(metrics), figsize=(len(metrics) * 6, len(self.modes)*6))
        for i, mode in enumerate(self.modes):
            stats = self.get_statistics(mode, group_by).T
            for j, metric in enumerate(metrics):
                plot_subgraph(axs[i, j], stats[metric].unstack(level=0), metric)
            fig.text(0.04, 0.5 - i / len(self.modes), mode, va='center', ha='center', rotation='vertical')
        fig.suptitle(f"{self.game_name} for different {gb_text}")
        os.makedirs(f"output/plots/game_params/{self.game_name}/all_modes", exist_ok=True)
        plt.savefig(f"output/plots/game_params/{self.game_name}/all_modes/afa_{gb_text}.png")
        plt.close()

    def get_game_args(self):
        return [c for c in self.data.columns if
                ("game_arg" in c and "show_inflation_update" not in c) or
                ("delta" in c and "delta_diff" not in c)]

    def complete_missing_groups(self, data, metrics, mode):
        game_args = self.get_game_args()
        player_args = ["player_1_args_model_name", "player_2_args_model_name"]
        columns = game_args + player_args

        data = data.dropna(subset=columns + player_args)

        print({c: data[c].nunique() for c in data.columns})
        for col in columns:
            data[col] = data[col].astype('category')

        unique_values = {col: data[col].unique() for col in columns}
        all_combinations = list(product(*(unique_values[col] for col in columns)))
        all_combinations_df = pd.DataFrame(all_combinations, columns=columns).astype('category')

        data = data[columns + metrics]
        missing_combinations = all_combinations_df.merge(data[columns], on=columns, how='left', indicator=True)
        missing_combinations = missing_combinations[missing_combinations['_merge'] == 'left_only']

        print("Missing combinations", len(missing_combinations), "of", len(all_combinations), len(all_combinations_df))
        features = columns

        for metric in tqdm(metrics):
            interaction_terms = []
            interaction_terms += [f"{f} : {player_args[0]}" for f in features]
            interaction_terms += [f"{f} : {player_args[1]}" for f in features]
            interaction_terms += [f"({f} : {f2})" for f in features for f2 in features if f != f2]
            interaction_terms += [f"({f} : {f2}) : {player_args[0]}" for f in features for f2 in features if f != f2]
            interaction_terms += [f"({f} : {f2}) : {player_args[1]}" for f in features for f2 in features if f != f2]
            interaction_terms += [f"{player_args[0]} : {player_args[1]}"]
            interaction_terms += [f"{player_args[0]}", f"{player_args[1]}"]
            interaction_terms += [f"{f}" for f in features]
            interaction_terms = ' + '.join(interaction_terms)
            other_features_formula = ' + '.join([f for f in features])
            formula = f'{metric} ~ {interaction_terms} + {other_features_formula}'

            y, X = patsy.dmatrices(formula, data, return_type='dataframe')

            def term_complexity(term):
                return term.count(':') + term.count('*') + term.count('(') + term.count(')')

            X_T = X.T
            X_T['complexity'] = X_T.index.map(term_complexity)

            X_T_sorted = X_T.sort_values(by='complexity', ascending=False)

            X_T_no_complexity = X_T_sorted.drop(columns='complexity')

            X_T_sorted_dedup = X_T_no_complexity.drop_duplicates(keep='last')

            X_reduced = X_T_sorted_dedup.T

                                                 
            model = sm.OLS(y, X_reduced).fit()

            print("\nMetric:", metric, "Mode:", mode,
                  "Number of parameters:", len(model.params), "Adj R2:", model.rsquared_adj, "AIC:", model.aic, "BIC:", model.bic)

            feature_formula = "1 ~ " + formula.split("~")[1].strip()

            _, all_combinations_transformed = patsy.dmatrices(feature_formula, all_combinations_df,
                                                              return_type='dataframe')

            all_combinations_transformed = all_combinations_transformed[X_reduced.columns]

            predicted_metrics = model.predict(all_combinations_transformed)
            predicted_metrics = np.clip(predicted_metrics, *self.metrics_range[metric])

                                                                         
            os.makedirs(f"output/model_summary/{self.game_name}/{mode}_{self.metrics[mode][metric]}", exist_ok=True)
            with open(f"output/model_summary/{self.game_name}/{mode}_{self.metrics[mode][metric]}/model_summary.txt", "w") as f:
                f.write(model.summary().as_text())

                                                                      
            model_dir = f"output/model/{self.game_name}/{mode}_{self.metrics[mode][metric]}"
            os.makedirs(model_dir, exist_ok=True)
                                                   
            if os.path.exists(f'{model_dir}/model.joblib'):
                os.remove(f'{model_dir}/model.joblib')
            joblib.dump(model, f'{model_dir}/model.joblib')
                                                                                      
            if os.path.exists(f'{model_dir}/features.joblib'):
                os.remove(f'{model_dir}/features.joblib')
            joblib.dump(X_reduced.columns, f'{model_dir}/features.joblib')
                                                                                      
            if os.path.exists(f'{model_dir}/all_combinations.joblib'):
                os.remove(f'{model_dir}/all_combinations.joblib')
            joblib.dump(all_combinations_df, f'{model_dir}/all_combinations.joblib')

            all_combinations_df[metric] = predicted_metrics

        if any(["delta" in c for c in all_combinations_df.columns]):
                                                                                             
            delta_1_col = "game_args_delta_1" if "game_args_delta_1" in all_combinations_df.columns else "player_1_args_delta"
            delta_2_col = "game_args_delta_2" if "game_args_delta_2" in all_combinations_df.columns else "player_2_args_delta"
            all_combinations_df["delta_diff"] = all_combinations_df[delta_1_col].astype(float) - all_combinations_df[delta_2_col].astype(float)
            all_combinations_df["delta_diff"] = all_combinations_df["delta_diff"].apply(lambda x: float(f"{float(x):.2f}"))
            columns += ["delta_diff"]

        return all_combinations_df[columns + metrics]


class NegotiationMetrics(Metrics):
    def __init__(self, config_with_statistics_path,  **args):
        super().__init__(config_with_statistics_path,
                         family_name="Negotiation",
                         player_1_name="Alice",
                         player_2_name="Bob",  **args)
        self.interaction_features_couples = [("game_args_seller_value", "game_args_buyer_value")]

    def calculate_metrics(self):
        self.data["p_f"] = (self.data["game_args_seller_value"] + self.data["game_args_buyer_value"]) / 2
        self.data["trade_is_made"] = self.data["result"] == "AcceptOffer"
        self.data["p_ev"] = self.data["final_price"] / self.data["game_args_product_price_order"]
        self.data["fairness"] = np.where(self.data["trade_is_made"],
                                         1 - 4 * (self.data["p_ev"] - self.data["p_f"]) ** 2,
                                         1)
        self.data["alice_gain"] = np.where(self.data["trade_is_made"],
                                           self.data["p_ev"] - self.data["game_args_seller_value"],
                                           0)
        self.data["bob_gain"] = np.where(self.data["trade_is_made"],
                                         self.data["game_args_buyer_value"] - self.data["p_ev"],
                                         0)
        self.data["efficiency"] = np.where(self.data["game_args_buyer_value"] > self.data["game_args_seller_value"],
                                           self.data["trade_is_made"],
                                           1)
        self.data["efficiency"] = np.where(self.data["game_args_buyer_value"] < self.data["game_args_seller_value"],
                                           ~self.data["trade_is_made"],
                                           self.data["efficiency"])
        
        self.data["alice_self_gain"] = self.data["alice_gain"]
        self.data["bob_self_gain"] = self.data["bob_gain"]
        
        self.metrics = {"Alice": {"alice_gain": "Self Gain", "efficiency": "Efficiency", "fairness": "Fairness"},
                        "Bob": {"bob_gain": "Self Gain", "efficiency": "Efficiency", "fairness": "Fairness"}}
        self.metrics_range = {"alice_gain": (None, None), "bob_gain": (None, None),
                              "efficiency": (0, 1), "fairness": (0, 1)}

class BargainingMetrics(Metrics):
    def __init__(self, config_with_statistics_path, **args):
                                                                                    
                                                                                
        data_columns = pd.read_csv(config_with_statistics_path, index_col=0, nrows=0).columns
        if "game_args_delta_1" in data_columns and "game_args_delta_2" in data_columns:
            self.interaction_features_couples = [("game_args_delta_1", "game_args_delta_2")]
            self.delta_1_col = "game_args_delta_1"
            self.delta_2_col = "game_args_delta_2"
        else:
            self.interaction_features_couples = [("player_1_args_delta", "player_2_args_delta")]
            self.delta_1_col = "player_1_args_delta"
            self.delta_2_col = "player_2_args_delta"

        super().__init__(config_with_statistics_path,
                         family_name="Bargaining",
                         player_1_name="Alice",
                         player_2_name="Bob", **args)
        self.add_to_drop("delta_diff")


    def calculate_metrics(self):
                                                                     
                                                                                
        self.data["p_ev"] = self.data["alice_gain"] / self.data["game_args_money_to_divide"]
        assert (self.data["alice_gain"] + self.data["bob_gain"] == self.data["game_args_money_to_divide"]).any()
        self.data["alice_final_share"] = (self.data["p_ev"] *
                                          self.data[self.delta_1_col] ** (self.data["rounds_played"] - 1))
        self.data["bob_final_share"] = ((1 - self.data["p_ev"]) *
                                        self.data[self.delta_2_col] ** (self.data["rounds_played"] - 1))
        self.data["efficiency"] = self.data["alice_final_share"] + self.data["bob_final_share"]
        self.data["fairness"] = 1 - 4 * (self.data["p_ev"] - 0.5) ** 2
        
        self.data["alice_self_gain"] = self.data["alice_final_share"]
        self.data["bob_self_gain"] = self.data["bob_final_share"]
        
        self.metrics = {"Alice": {"alice_final_share": "Self Gain", "efficiency": "Efficiency",
                                         "fairness": "Fairness",                              
                                         },
                        "Bob": {"bob_final_share": "Self Gain", "efficiency": "Efficiency",
                                          "fairness": "Fairness",                              
                                          }}
        self.metrics_range = {"alice_final_share": (0, 1), "bob_final_share": (0, 1),
                              "efficiency": (0, 1), "fairness": (0, 1),                       
                                }


class PersuasionMetrics(Metrics):
    def __init__(self, config_with_statistics_path,  **args):
        super().__init__(config_with_statistics_path,
                         family_name="Persuasion",
                         player_1_name="Alice",
                         player_2_name="Bob",  **args)
        self.interaction_features_couples = [("game_args_p", "game_args_c")]

    def calculate_metrics(self):
        quality_cols = [c for c in self.data.columns if "quality" in c]
        deal_cols = [c for c in self.data.columns if "deal" in c]
                                             
        self.data["game_args_c"] = 0
        self.data["game_args_total_rounds"] = 20
        self.data["game_args_is_buyer_know_p"] = True
        self.data["game_args_allow_buyer_message"] = False

        self.data["n_ev"] = self.data[quality_cols].sum(axis=1)
        self.data["k_ev"] = (self.data[quality_cols].to_numpy() * self.data[deal_cols].to_numpy()).sum(axis=1)
        self.data["r_ev"] = (~self.data[quality_cols].to_numpy() * ~self.data[deal_cols].to_numpy()).sum(axis=1)
        self.data["efficiency"] = self.data["k_ev"] / self.data["n_ev"]
        self.data["fairness"] = np.where(self.data["n_ev"] < 20, self.data["r_ev"] / (20 - self.data["n_ev"]), np.nan)

        self.data["alice_final_share"] = self.data[deal_cols].sum(axis=1) / 20
        self.data["bob_final_share"] = ( self.data["k_ev"] * (self.data["game_args_v"] - 1) + \
                                         self.data["r_ev"] * (self.data["game_args_c"] - 1) ) /20
        
        self.data["alice_self_gain"] = self.data["alice_final_share"]
        self.data["bob_self_gain"] = self.data["bob_final_share"]

        self.metrics = {"Alice": {"alice_final_share": "Self Gain", "efficiency": "Efficiency", "fairness": "Fairness"},
                        "Bob": {"bob_final_share": "Self Gain", "efficiency": "Efficiency", "fairness": "Fairness",}}
        self.metrics_range = {"alice_final_share": (0, 1), "bob_final_share": (-1, None),
                                "efficiency": (0, 1), "fairness": (0, 1)}

def create_table(families, format_function, llm_names, show_arrows=False, metric_goal=None):
    llm_list = list(set([l for family in families for l in family.get_llms()]))
    llm_list = [l for l in llm_names if l in llm_list]
    total_columns = len(llm_list) + 3
    text = f"""\\begin{{table}}[]
\\begin{{tabular}}{{lll|{len(llm_list) * "l"}}}
\\toprule
Family & Rule & Metric &  {f" & ".join([llm_short_names[l] if l in llm_short_names else l for l in llm_list])} \\\\
\\midrule
"""
    def multi_lines_if_needed(x: str):
        if " " in x:
            return "\shortstack{" + x.replace(" ", "\\\\") + "}"
        return x
    for fam_i, family in enumerate(families):
        family_statistics = family.get_all_tables()
        n_rows = [table.shape[0] for table in family_statistics]
        for tab_i, table in enumerate(family_statistics):
            for row_i, (metric_name, row) in enumerate(table.iterrows()):
                row_text = "\\multirow{" + str(sum(n_rows)) + "}{*}{" + family.game_name + "}" if tab_i == 0 and row_i == 0 else ""
                row_text += " & " + ("\\multirow{" + str(n_rows[tab_i]) + "}{*}{" + multi_lines_if_needed(family.modes[tab_i]) + "}" if row_i == 0 else "")
                if show_arrows:
                    row_text += f" & {{\\tiny $\{metric_goal[metric_name]}arrow$}} {metric_name}"
                else:
                    row_text += f" & {metric_name}"
                def get_value_string_formatted(metric_value):
                    metric_string = format_function(metric_value)
                    if metric_string == format_function(row.max()):
                        return "\\textbf{" + metric_string + "}"
                    return metric_string
                for llm in llm_list:
                    row_text += f" & {get_value_string_formatted(row[llm]) if llm in row else '-'}"
                text += row_text + " \\\\"
                if row_i == n_rows[tab_i]-1:
                    if tab_i == len(family_statistics) - 1:
                        if fam_i == len(families) - 1:
                            text += f"""\\bottomrule"""
                        else:
                            text += "\\midrule"
                    else:
                        text += f" \\cmidrule{{2-{total_columns}}}"
                text += "\n"
    text += f"""\\end{{tabular}}
\\caption{{\input{{tables/data_metrics_caption}}}}
\\label{{tab:data_metrics}}
\\end{{table}}"""
    return text


def format_numbers(x):
    return f"{x:.2f}"


def create_table_for_paper():
    metric_goal = {"Efficiency": "up",
                   "Fairness": "up",
                   "Self Gain": "up",
                   "Rationality": "up"}

    nego = NegotiationMetrics("output/configs/negotiation_with_stats.csv")
    pers = PersuasionMetrics("output/configs/persuasion_with_stats.csv")
    rubin = BargainingMetrics("output/configs/bargaining_with_stats.csv")
                   
    data = [rubin, nego, pers]

                         
                                                 
                                       
                                                             
                                           
                                               
                      
                                                                                   

    t = create_table(data, format_numbers, llm_short_names,
                     show_arrows=False, metric_goal=metric_goal)
    return t


          
def calc_metrics():
    t = create_table_for_paper()
    print(t)


if __name__ == "__main__":
    calc_metrics()