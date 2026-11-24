import random

import numpy as np
import pymc as pm

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

PRIOR = """There are breast cancer patients where, for each patient, an amount of time has passed since they received surgery and their cancer has either metastasized or not."""
NO_PRIOR = """You are observing a binary response for a tuple of two values, one binary and one integer (0 or 1, integer)."""

class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_params_cache = {}
        self.norm_mu, self.norm_sigma = (0.2604, 0.43885286828275377)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = """Your goal is to be able to predict whether a breast cancer patient will survive given the time since they received surgery and whether their cancer has metastasized."""
        else:
            goal_description = "Your goal is to be able to predict the binary response of the environment to a given set of parameters."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
                                                                                   
            num_ones = sum([1 for _, _, outcome in self.eval_points if outcome == 1])
            num_zeros = sum([1 for _, _, outcome in self.eval_points if outcome == 0])
            if num_ones > num_zeros:
                target = 0
            else:
                target = 1
            while True:
                metastasized = np.random.randint(0, 2)
                time_since_surgery = np.random.uniform(0, self.env.time_upper_bound)
                outcome = self.env._simulate_patient(metastasized, time_since_surgery)
                if outcome == target:
                    break
            self.eval_points.append((metastasized, time_since_surgery, outcome))
        else:
            metastasized, time_since_surgery, outcome = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1
        if include_prior:
            question = f"Given the metastasized status = {metastasized} and the time since surgery = {time_since_surgery}, is the patient alive or dead?"
        else:
            question = f"Predict the binary response for the parameters: {metastasized}, {time_since_surgery}."
        question += " Respond using a binary value 0 or 1."
        return question, outcome 
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for p in predictions:
            if "1" in p:
                parsed_predictions.append(1)
            elif "0" in p:
                parsed_predictions.append(0)
            else:
                print("prediction not parsed")
                parsed_predictions.append(None)
        correctness = [parsed_predictions[i]==measurements[i] for i in range(len(predictions))]
        accuracy = sum(correctness) / len(correctness)
        std = np.std(np.array(correctness))
        return (accuracy, std)

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        print("EIG for query point", query_point)
        print(self.update_params_cache.keys())
        patientID = query_point
        _, time_since_surgery, metastasized = self.env.outcomes[patientID]
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_params_cache:
            with pm.Model() as model:
                        
                lambda0 = pm.Gamma("lambda0i", 0.1, 0.1)
                beta = pm.HalfNormal("beta_absi", sigma=10)
                                      
                def likelihood(obs_t, obs_m, obs_outcome):
                    ilambda_ = np.exp(beta * obs_m) * lambda0
                    imu = obs_t * ilambda_
                    death_prob = pm.math.invlogit(imu)
                    return pm.Bernoulli("death_outcomei", p=death_prob, observed=obs_outcome)
                
                if len(existing_data) > 0:
                    print(f"obs_times = {[self.env.outcomes[d[0]][1] for d in existing_data]}")
                    print(f"obs_metastasized = {[self.env.outcomes[d[0]][2] for d in existing_data]}")
                    print(f"obs_outcome = {[self.env.outcomes[d[0]][0] for d in existing_data]}")
                    obs_t = pm.Data("obs_t", [self.env.outcomes[d[0]][1] for d in existing_data])
                    obs_m = pm.Data("obs_m", [self.env.outcomes[d[0]][2] for d in existing_data])
                    obs_outcome = pm.Data("obs_outcome", [self.env.outcomes[d[0]][0] for d in existing_data])
                    likelihood(obs_t, obs_m, obs_outcome)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, tune=1000, return_inferencedata=False)
            lambda0s = trace["lambda0i"]
            betas = trace["beta_absi"]
            shuffling= list(zip(lambda0s, betas))
            random.shuffle(shuffling)
            lambda0s, betas = zip(*shuffling)
            self.update_params_cache[tuple(existing_data)] = (lambda0s, betas)
        else:
            lambda0s, betas = self.update_params_cache[tuple(existing_data)]
        outer_betas = betas[:num_outer_samples]
        outer_lambda0s = lambda0s[:num_outer_samples]
        log_likelihoods = []        
        for n, (outer_beta, outer_lambda0) in enumerate(zip(outer_betas, outer_lambda0s)):
                                             
            lambda_ = np.exp(outer_beta * metastasized) * outer_lambda0
            mu = time_since_surgery * lambda_
            prob = 1 / (1 + np.exp(-mu))
            sampled_choice = np.random.binomial(n=1, p=prob)
            log_likelihood = np.log(prob) if sampled_choice == 1 else np.log(1 - prob)

            inner_betas = betas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
            inner_lambda0s = lambda0s[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
            marginal_log_likelihoods = []
            for inner_beta, inner_lambda0 in zip(inner_betas, inner_lambda0s):
                lambda_ = np.exp(inner_beta * metastasized) * inner_lambda0
                mu = time_since_surgery * lambda_
                prob = 1 / (1 + np.exp(-mu))
                inner_log_likelihood = np.log(prob+0.0001) if sampled_choice == 1 else np.log(1 - prob+0.0001)
                marginal_log_likelihoods.append(inner_log_likelihood)
            
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood-log_marginal_likelihood)
        
        eig = np.mean(log_likelihoods)
        return eig

    def get_norm_factors(self):
        N = 10000    
        errs = []
        measurements = []
        import logging
        import tqdm
        logger = logging.getLogger("pymc")
        logger.setLevel(logging.WARNING)
        for i in tqdm.tqdm(range(N)):
            if i % 100 == 0:
                self.env.reset()
            inp = self.env.sample_random_input()
            out = self.env.step(inp)
            measurements.append(out)
        mu = np.mean(measurements)
        pred = [str(mu)] * N
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

    def get_norm_factors(self):
        N = 10000    
        errs = []
        measurements = []
        import logging
        import tqdm
        logger = logging.getLogger("pymc")
        logger.setLevel(logging.WARNING)
        for i in tqdm.tqdm(range(N)):
            if i % 100 == 0:
                self.env.reset()
            inp = self.env.sample_random_input()
            out = self.env.step(inp)
            measurements.append(out)
        mu = np.mean(measurements)
        pred = [str(mu)] * N
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user."

        if include_prior:
            goal_description += """The goal of the user is to be able to predict whether a breast cancer patient will survive given the time since they
received surgery and whether their cancer has metastasized."""
        else:
            goal_description += "The goal of the user is to be able to predict the binary response of the environment to a given set of parameters."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = """Your goal is to predict whether a breast cancer patient will survive given the time since they received surgery and whether their cancer has metastasized."""
        else:
            goal_description = "Your goal is to predict the binary response of the environment to a given set of parameters."
        format_instructions = """Respond with a binary value 0 or 1. Make assumptions about the environment and provide your best guess.
Here is an example:
<thought> your thought </thought>
<answer>1</answer>"""
        description = goal_description + '\n' + format_instructions
        description += "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog=None, params_summary_str=None):    
        description = f"""Assume that the user has no prior knowledge, and will not be able to run any experiments before making predictions. 
They will make predictions based solely on your explanation, so provide as much detail as possible. You cannot provide your own experiments or observations.
Limit your explanation to {com_limit} words."""

        if use_ppl:
            description += f"To make your explanation clearer and more informative, look at the statistical model (written in pymc) designed by a colleague for the experimental data and the inferred parameters. \n"
            description += f"Here is the statistical model. \n {str_prob_prog} \n"
            description += f"Here are the inferred params. \n {params_summary_str} \n"
            description += f"Don't literally describe the model verbatim but use it to conceptually motivate your explanation."
            description += f"The agent will not be able to use the model explicitly but having a conceptual understanding will be beneficial."
        return description

class SurvivalAnalysis:
    def __init__(self, num_patients=100, time_upper_bound=10):
        self.num_patients = num_patients
        self.time_upper_bound = time_upper_bound
        self.model = self._build_model()
        self.reset()
        self.env_name = "survival_analysis"

    def _build_model(self):
        with pm.Model() as model:        
                    
            lambda0 = pm.Gamma("lambda0", 0.1, 0.1)
            beta = pm.HalfNormal("beta_abs", sigma=10) 
        return model

    def reset(self):
        with self.model:
            self.lambda0 = pm.draw(self.model["lambda0"]) 
            self.beta = pm.draw(self.model["beta_abs"])
        self.outcomes = self._simulate_multiple_patients(self.num_patients, self.time_upper_bound)
        self.observed_data = []

    def generate_system_message(self, include_prior=True, goal=None): 
        assert goal is not None
        filtered_patients = [[time, metastasized_status] for _, time, metastasized_status in self.outcomes]
        filtered_patients_txt = ""
        for i, patient in enumerate(filtered_patients):
            filtered_patients_txt += f"{i}: {patient[0]:0.2f}, {patient[1]}\n"
        if include_prior:
                message = f"""{PRIOR}
{goal}
There are {self.num_patients}, and the time since surgery and status of metastasization are given
by below. 0 or 1 indicates whether the cancer metastasized. 
{filtered_patients_txt}
You may check whether a patient is alive by providing a patient ID where the ID ranges from 0 to {self.num_patients - 1}. Make observations by specifying a single integer ID. If the patient is alive, the output will be 0, otherwise 1, if the the patient is dead.
You can think before you choose to decide which ID you want to observe.

Here is an example:
<thought> your thought </thought>
<observe>1</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought</thought>
<answer> your answer </answer>
"""
        else:
            message = f"""{NO_PRIOR}
{goal}
You may only observe these inputs to the function.
{filtered_patients_txt}
Check the output of the function at one of the listed inputs by providing the index of the
tuple you want to observe from 0 to {self.num_patients - 1}. Make observations by specifying a single integer index enclosed in double brackets. You can think before you choose to decide which index you want to observe.

Here is an example:
<thought> your thought </thought>
<observe>1</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>
"""
        return message
    
    def _simulate_patient(self, metastasized, time_since_surgery):
                                  
                              
        with pm.Model() as model:
            lambda_ = np.exp(self.beta * metastasized) * self.lambda0
            mu = time_since_surgery * lambda_
            death_prob = pm.math.invlogit(mu)

                                                                                  
            death_outcome = pm.Bernoulli("death_outcome", p=death_prob)
            sim = pm.sample_prior_predictive(samples=1, return_inferencedata=False, model=model)                         
        return int(sim["death_outcome"][0])

    def _simulate_multiple_patients(self, num_patients, time_upper_bound):
        results_list = []                                      
        random_times = np.random.uniform(0, time_upper_bound, num_patients)
        random_metastasized_statuses = np.random.randint(0, 2, num_patients)

        for i in range(num_patients):
            outcome = self._simulate_patient(random_metastasized_statuses[i], random_times[i])
            results_list.append([outcome, random_times[i], random_metastasized_statuses[i]])
        return results_list

    def sample_random_input(self):
        return np.random.randint(0, self.num_patients)

    def step(self, patientID):
        obs = self.outcomes[patientID][0]
        return int(obs) 

    def validate_input(self, input_string):
                                                 
        try:
            patient_id = int(input_string.strip())
        except:
            return "Input must be an integer."
        if patient_id < 0 or patient_id > self.num_patients:
            return f"Input must be between 0 and {self.num_patients - 1}."
        return patient_id
    
    def run_experiment(self, input_string):
        patientID = self.validate_input(input_string)
        if type(patientID) == str:
            return patientID, False
        outcome = self.step(patientID)
        self.observed_data.append((patientID, outcome))
        return outcome, True

    def get_data(self):
        patientid2metadata = {}
        for index, lst in enumerate(self.outcomes):
            patientid2metadata[index] = (lst[1], lst[2]) 

        data_tuples = []
        for patientID, outcome in self.observed_data:
                                                                   
            data_tuples.append(
                (
                    patientid2metadata[patientID][1],
                    patientid2metadata[patientID][0], 
                    outcome, 
                )
            )

        return data_tuples 

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""
There are {self.num_patients} breast cancer patients, and the time since surgery and status of metastasization are given
by below. 0 or 1 indicates whether the cancer metastasized. 
You may check whether a patient is alive by providing a patient ID where the ID ranges from 0 to {self.num_patients - 1}. Make observations by specifying a single integer ID. If the patient is alive, the output will be 0, otherwise 1, if the the patient is dead.
"""
        else:
            return f"""
You only observe inputs to the function.
There is an output of the function at one of the listed inputs which range from 0 to {self.num_patients - 1}. 
"""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["metastasized_status", "time_surgery", "outcome"]
        else:
            return ["x1", "x2", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        if self.include_prior:
            return (f"The observations are: \n -outcome: whether patient died \n"
                    f"The input values are \n -time_surgery: time since surgery \n -metastasized_status: whether the cancer metastasized."
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return (f"The observations are: \n -y: observation \n"
                    f"The input values are \n -x1 \n -x2 "
                    f"Use the values of the input values to help you model the observations. ")
    
if __name__ == "__main__":
    env = SurvivalAnalysis(100, 10)
    goal = DirectGoal(env)
    print(goal.get_norm_factors())
                                          
                        
                                             
                        
                                             
                        
                                             
 
                                 
                                 
               
                    
                                                        
                            
                                     
                          
                
    