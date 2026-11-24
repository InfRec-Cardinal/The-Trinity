import json
import random
import re

import numpy as np
import pymc as pm
from scipy.stats import norm

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe


PRIOR = """Sea cows are different lengths at different ages."""
NO_PRIOR = """You are observing a float response to a float input."""

class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_params_cache = {}
        self.norm_mu, self.norm_sigma = (0.9058681693402041, 9.234192516908691)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = """Your goal is to be able to predict the length of a sea cow given its age. Conduct experiments to learn about the environment and make predictions based on your observations."""
        else:
            goal_description = "Your goal is to be able to predict the float response of the environment to a given input. Conduct experiments to learn about the environment and make predictions based on your observations."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
            age = (np.random.beta(2, 5) * 4)
            length = self.env.step(age)
            self.eval_points.append((age, length))
        else:
            age, length = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1

        if include_prior:
            question = f"""Predict the length of a sea cow at age: {age}. 
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>"""

        else:
            question = f"""Predict the float response to the following input: {age}.
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>"""
        return question, length
    
    def evaluate_predictions(self, predictions, measurements):
        assert len(predictions) == len(measurements), "Predictions and measurements must have the same length."
        parsed_predictions = []
        for p in predictions:
            p = p.strip()
            if "=" in p:
                p = p.split("=")[1]
            try:
                p = float(p)
            except:
                                                 
                p = re.findall(r"[-+]?\d*\.\d+|\d+", p)[-1]
            parsed_predictions.append(p)
        se = (np.array(parsed_predictions) - np.array(measurements)) ** 2
        mse = np.mean(se)
        std_mse = np.std(se)
        return mse, std_mse

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        age_query = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_params_cache:
            print("Updating cache")
            with pm.Model() as model:
                alphai = pm.Normal("alphai", mu=self.env.alpha, sigma=0.2)
                betai = pm.Normal("betai", mu=self.env.beta, sigma=0.5)
                lambda_i = pm.Normal("lambdai", mu=self.env.lambda_, sigma=0.5)

                def likelihood(obs_age, obs_length):
                    mi = alphai - betai * np.abs(lambda_i) ** obs_age
                    return pm.Normal("obs", mu=mi, sigma=0.25, observed=obs_length)

                if len(existing_data) > 0:
                    obs_age = pm.Data("obs_age", [d[0] for d in existing_data])
                    obs_length = pm.Data("obs_length", [d[1] for d in existing_data])
                    likelihood(obs_age, obs_length)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, tune=1000, return_inferencedata=False)
            
            alphas = trace['alphai']
            betas = trace['betai']
            lambdas = trace['lambdai']
            shuffling = list(zip(alphas, betas, lambdas))
            random.shuffle(shuffling)
            alphas, betas, lambdas = zip(*shuffling)
            self.update_params_cache[tuple(existing_data)] = (alphas, betas, lambdas)
        else:
            alphas, betas, lambdas = self.update_params_cache[tuple(existing_data)]

        outer_alphas = alphas[:num_outer_samples]
        outer_betas = betas[:num_outer_samples]
        outer_lambdas = lambdas[:num_outer_samples]
        log_likelihoods = []
        for n, (alpha, beta, lambda_) in enumerate(zip(outer_alphas, outer_betas, outer_lambdas)):
                                                    
            with pm.Model() as model:
                m = alpha - beta * np.abs(lambda_) ** age_query
                l_sampled = np.random.normal(m, 0.25)
                prob = norm.pdf(l_sampled, m, 0.25)
                log_likelihood = np.log(prob+0.001)
                inner_alphas = alphas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_betas = betas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_lambdas = lambdas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                marginal_log_likelihoods = []
                for inner_alpha, inner_beta, inner_lambda in zip(inner_alphas, inner_betas, inner_lambdas):
                    m = inner_alpha - inner_beta * np.abs(inner_lambda) ** age_query
                    prob_i = norm.pdf(l_sampled, m, 0.25)
                    marginal_log_likelihoods.append(np.log(prob_i+0.001))
                
                max_log = np.max(marginal_log_likelihoods)    
                log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
                log_likelihoods.append(log_likelihood - log_marginal_likelihood)
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 10000    
        errs = []
        measurements = []
        
        for i in range(N):
            if i % 10 == 0:
                self.env.reset()
            age = self.env.sample_random_input()
            out = self.env.step(age)
            measurements.append(out)
        mu = np.mean(measurements)
        pred = [str(mu)] * N
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal. "
        if include_prior:
            goal_description += "The goal of the user is to be able to predict the length of a sea cow given its age."
        else:
            goal_description += "The goal of the user is to be able to predict the float response of the environment to a given input."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict the length of a sea cow given its age."
        else:
            goal_description = "Your goal is to predict the float response of the environment to a given input."
        format_instructions = """You will be provided an input to this environment and will be tasked with predicting the output for each input.
You must respond with a real number. You may also think before providing your predictions.
Here is an example:
<thought>your thought</thought>
<answer>1</answer>"""
        description = goal_description + '\n' + format_instructions
        description += "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog=None, params_summary_str=None):
        description = f"""Assume that the user has no prior knowledge, and will not be able to run any experiments before making predictions. 
They will make predictions based solely on your explanation, so provide as much detail as possible. You CANNOT provide your own experiments or observations.
Limit your explanation to {com_limit} words."""

        if use_ppl:
            description += f"To make your explanation clearer and more informative, look at the statistical model (written in pymc) designed by a colleague for the experimental data and the inferred parameters. \n"
            description += f"Here is the statistical model. \n {str_prob_prog} \n"
            description += f"Here are the inferred params. \n {params_summary_str} \n"
            description += f"Don't literally describe the model verbatim but use it to conceptually motivate your explanation."
            description += f"The agent will not be able to use the model explicitly but having a conceptual understanding will be beneficial."
        return description
    
class Dugongs:
    def __init__(self, alpha=2, beta=1.5, lambda_=0.4, lower_limit=0, upper_limit=5):
        self.alpha = alpha
        self.beta = beta
        self.lambda_ = lambda_
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.model = self._build_model()
        self.reset()
        self.env_name = "dugongs"

    def _build_model(self):
        alpha, beta, lambda_ = self.alpha, self.beta, self.lambda_
        with pm.Model() as model:  
            alpha = pm.Normal("alpha", mu=alpha, sigma=0.2)
            beta = pm.Normal("beta", mu=beta, sigma=0.5)
            lambda_ = pm.Normal("lambda", mu=lambda_, sigma=0.5)
        return model

    def reset(self):
        with self.model:
            self.a = pm.draw(self.model['alpha']) 
            self.b = pm.draw(self.model['beta'])
            self.l = pm.draw(self.model['lambda'])
        self.observed_data = []

    def generate_system_message(self, include_prior=True, goal=None): 
        assert goal is not None
        if include_prior:
                message = f"""{PRIOR}
{goal}
Make observations by specifying a single age you want to observe with a real number.
The environment will return the length of a dugong at that age.
The age values are between {self.lower_limit} and {self.upper_limit}.
You may also think before providing your predictions.

Here is an example:
<thought> your thought </thought>
<observe>2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            message = f"""{NO_PRIOR}
{goal}
You may observe the value of the function one input value at a time. Make observations by specifying a single value you want to observe with a float.
The environment will return the float response of the function at that input.
The input values are between {self.lower_limit} and {self.upper_limit}.
You may also think before providing your predictions.

Here is an example:
<thought> your thought </thought>
<observe>2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>
"""
        return message
    
    def sample_random_input(self):
        return np.random.uniform(self.lower_limit, self.upper_limit)

    def step(self, age):
        with pm.Model() as model:
            m = self.a - self.b * np.abs(self.l) ** age
            y_obs = pm.Normal("y_obs", mu=m, sigma=0.25)
            prior = pm.sample_prior_predictive(samples=1, return_inferencedata=False)

        obs = prior['y_obs'][0]
        return float(abs(obs)) 

    def validate_input(self, input_string):
                                                 
        try:
            query = input_string.strip()
            age = float(query)
        except:
            return "Input must be a float."
        if age < self.lower_limit or age > self.upper_limit:
            return f"Input must be between {self.lower_limit} and {self.upper_limit}."
        
        return age
    
    def run_experiment(self, input_string):
        age = self.validate_input(input_string)
        if type(age) == str:
            return age, False
        length = self.step(age)
        self.observed_data.append((age, length))
        return length, True

    def get_data(self):
        return self.observed_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""The ages and lengths of 27 captured dugongs (sea cows)"""
        else:
            return "x and Y are the input and output values of the environment."

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["x", "Y"]
        else:
            return ["x", "Y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        if self.include_prior:
            return (f"The observations are: \n -Y: length of dugong (sea cows) \n"
                f"The input values are \n -x: age of dugong (sea cows). \n"
                f"Use the input values to help you model the observations. ")
        else:
            return ""

if __name__ == "__main__":
    env = Dugongs()
    goal = DirectGoal(env)
    import logging
    logger = logging.getLogger("pm")
    logger.propagate = False
    print(goal.get_norm_factors())
    
                        
                                             
    
                        
                                             

                
                                            
               
                           
                                                 
                          
                       
                                     
                                 
                
    
