import random

import numpy as np
from scipy.stats import norm, halfnorm, expon
import pymc as pm
import matplotlib.pyplot as plt

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

PRIOR = """A person has to choose between a delayed reward dR dollars in x days and an immediate reward iR dollars today."""
NO_PRIOR = """You are observing a binary response for a tuple of three positive integer values (integer, integer, integer)."""

class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu = 0.5
        self.norm_sigma = 0.4692829610160591

    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = """Your goal is to be able to predict the choice of a person between a delayed reward and an immediate reward.
Remember, the decisions are not deterministic."""
        else:
            goal_description = "Your goal is to be able to predict the binary response of the environment to a given set of parameters."
        
        self.goal_description = goal_description
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        print(f"eval_pointer: {self.eval_pointer}")
        if self.eval_pointer+1 > len(self.eval_points):
            print("Generating new eval point")
                                                                                   
            num_ones = sum([1 for _, _, _, choice in self.eval_points if choice == 1])
            num_zeros = sum([1 for _, _, _, choice in self.eval_points if choice == 0])
            if num_ones > num_zeros:
                target = 0
            else:
                target = 1
            while True:
                ir = int(np.random.uniform(1, 300))
                dr = int(np.random.uniform(ir + 1, 300))
                days = int(np.random.randint(1, 365))
                choice = self.env.step(ir, dr, days)
                if choice == target:
                    break
            self.eval_points.append((ir, dr, days, choice))
        else:
                            
            ir, dr, days, choice = self.eval_points[self.eval_pointer]
        print(f"eval_point: {ir}, {dr}, {days}, {choice}")
        self.eval_pointer += 1
        if include_prior:
            question = f"Given the immediate reward iR = {ir}, delayed reward dR = {dr}, and delay in days D = {days}, what is the person's choice?"
        else:
            question = f"Predict the binary response for the parameters: {ir}, {dr}, {days}."
        question += " Respond using a binary value 0 or 1."
        return question, choice 
    
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
        print(f"query_point: {query_point}")
        ir, dr, days = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_param_cache:
                                                   
            print("updating parameters")
            with pm.Model() as model:
                log_k = pm.Normal('log_k', mu=self.env.k_mean, sigma=self.env.k_std)
                k = pm.Deterministic('k', pm.math.exp(log_k))
                alpha = pm.HalfNormal('alpha', sigma=self.env.alpha_scale)

                                                
                def likelihood(iR, dR, Days, choice):
                    V0, V1 = self.env._calculate_values(iR, dR, Days, k)
                    z = (V1 - V0) / alpha
                    phi = pm.math.erf(z / pm.math.sqrt(2)) / 2 + 0.5
                    probability = self.env.epsilon + (1 - 2 * self.env.epsilon) * phi
                    return pm.Bernoulli('choice', p=probability, observed=choice)

                iR_obs = pm.Data('iR_obs', [d[0] for d in existing_data])
                dR_obs = pm.Data('dR_obs', [d[1] for d in existing_data])
                Days_obs = pm.Data('Days_obs', [d[2] for d in existing_data])
                choice_obs = pm.Data('choice_obs', [d[3] for d in existing_data])                        
                likelihood(iR_obs, dR_obs, Days_obs, choice_obs)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, cores=1, tune=1000, return_inferencedata=False)
            ks = trace['k']
            alphas = trace['alpha']
            shuffling = list(zip(ks, alphas))
            random.shuffle(shuffling)
            ks, alphas = zip(*shuffling)
            updated_k_samples = ks[:num_outer_samples]
            updated_alpha_samples = alphas[:num_outer_samples]
            print(len(trace['k']))
            print("updated parameters", len(updated_k_samples), len(updated_alpha_samples))
            print(f"inferred k: {np.mean(updated_k_samples)}, alpha: {np.mean(updated_alpha_samples)}")
            self.update_param_cache[tuple(existing_data)] = (updated_k_samples, updated_alpha_samples, ks[num_outer_samples:], alphas[num_outer_samples:])
        else:
            updated_k_samples, updated_alpha_samples, ks, alphas = self.update_param_cache[tuple(existing_data)]
        log_likelihoods = []

        for n, (outer_k, outer_alpha) in enumerate(zip(updated_k_samples, updated_alpha_samples)):
                                                                       
            v0, v1 = self.env._calculate_values(ir, dr, days, outer_k)
            z = (v1 - v0) / outer_alpha
            prob = self.env.epsilon + (1 - 2 * self.env.epsilon) * norm.cdf(z)
                                                                                                         

            inner_k_samples = ks[n*num_inner_samples:(n+1)*num_inner_samples]
            inner_alpha_samples = alphas[n*num_inner_samples:(n+1)*num_inner_samples]
            sampled_choice = np.random.binomial(n=1, p=prob)
            log_likelihood = np.log(prob) if sampled_choice == 1 else np.log(1 - prob)

                                                                                
            marginal_log_likelihoods = []
            for inner_k, inner_alpha in zip(inner_k_samples, inner_alpha_samples):
                v0, v1 = self.env._calculate_values(ir, dr, days, inner_k)
                z = (v1 - v0) / inner_alpha
                prob = self.env.epsilon + (1 - 2 * self.env.epsilon) * norm.cdf(z)
                prob = prob if sampled_choice == 1 else 1 - prob
                marginal_log_likelihood = np.log(prob)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            naive_mean = np.log(np.mean(np.exp(marginal_log_likelihoods)))
                                                                                                                   
                                                                                                          
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)

                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 100000
        predictions = []
        measurements = []
        for _ in range(N):
            self.env.reset()
            iR, dR, days = self.env.sample_random_input()
            choice = self.env.step(iR, dR, days)
            predictions.append(choice)
            measurements.append(choice)
        pred = np.mean(predictions)
        pred = 0 if pred < 0.5 else 1
        avg_preds =  [str(pred) for _ in range(N)]
        mean_error, std = self.evaluate_predictions(avg_preds, measurements)
        return mean_error, std

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to be able to predict the choice of a person between a delayed reward and an immediate reward."
        else:
            goal_description += "The goal of the user is to be able to predict the binary response of the environment to a given set of parameters."

        self.goal_description = goal_description
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict the choice of a person between a delayed reward and an immediate reward."
        else:
            goal_description = "Your goal is to predict the binary response of the environment to a given set of parameters."
        format_instructions = """You will be provided an input to this environment and will be tasked with predicting the output for each input.
You must respond with a binary value. You may also think before providing your predictions.
Here is an example:
<thought>your thought</thought>
<answer>1</answer>"""
        description = goal_description + '\n' + format_instructions
        description = "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog="", params_summary_str=""):
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

class DiscountGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu = 0.25
        self.norm_sigma = 4.3
    
    def get_system_message(self, include_prior):
        if not include_prior:
            raise ValueError("DiscountGoal requires prior knowledge.")
        goal_description = """Your goal is to predict the discount factor k that characterizes a person\'s perception of future reward in decision making. 
Remember, the decisions are not deterministic.
This is how the discount factor is applied in the environment:
V0 = iR
V1 = dR / (1 + k * Days)"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        assert include_prior, "DiscountGoal requires prior knowledge."
        (k, _) = self.env.truth
        question = "What is the discount factor k that characterizes the person's behavior?"
        question += " Respond with the float value for k."
        return question, k
    
    def evaluate_predictions(self, predictions, measurements):
        assert len(predictions) == len(measurements), "Predictions and measurements must have the same length."
        predictions = [float(p) for p in predictions]
        predictions = np.array(predictions)
        measurements = np.array(measurements)
        se = (predictions - measurements) ** 2
        return (np.mean(se), np.std(se))
    
    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        ir, dr, days = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_param_cache:
                                                   
            print("updating parameters")
            with pm.Model() as model:
                log_k = pm.Normal('log_k', mu=self.env.k_mean, sigma=self.env.k_std)
                k = pm.Deterministic('k', pm.math.exp(log_k))
                alpha = pm.HalfNormal('alpha', sigma=self.env.alpha_scale)

                                                
                def likelihood(iR, dR, Days, choice):
                    V0, V1 = self.env._calculate_values(iR, dR, Days, k)
                    z = (V1 - V0) / alpha
                    phi = pm.math.erf(z / pm.math.sqrt(2)) / 2 + 0.5
                    probability = self.env.epsilon + (1 - 2 * self.env.epsilon) * phi
                    return pm.Bernoulli('choice', p=probability, observed=choice)

                iR_obs = pm.Data('iR_obs', [d[0] for d in existing_data])
                dR_obs = pm.Data('dR_obs', [d[1] for d in existing_data])
                Days_obs = pm.Data('Days_obs', [d[2] for d in existing_data])
                choice_obs = pm.Data('choice_obs', [d[3] for d in existing_data])                        
                likelihood(iR_obs, dR_obs, Days_obs, choice_obs)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, tune=1000, cores=1, return_inferencedata=False)

            ks = trace['k']
            alphas = trace['alpha']
            shuffling = list(zip(ks, alphas))
            random.shuffle(shuffling)
            ks, alphas = zip(*shuffling)
            updated_k_samples = ks[:num_outer_samples]
            updated_alpha_samples = alphas[:num_outer_samples]
            print(len(trace['k']))
            print("updated parameters", len(updated_k_samples), len(updated_alpha_samples))
            print(f"inferred k: {np.mean(updated_k_samples)}, alpha: {np.mean(updated_alpha_samples)}")
            self.update_param_cache[tuple(existing_data)] = (updated_k_samples, updated_alpha_samples, ks[num_outer_samples:], alphas[num_outer_samples:])
        else:
            updated_k_samples, updated_alpha_samples, ks, alphas = self.update_param_cache[tuple(existing_data)]
        log_likelihoods = []

        for n, (outer_k, outer_alpha) in enumerate(zip(updated_k_samples, updated_alpha_samples)):
            inner_k_samples = ks[n*num_inner_samples:(n+1)*num_inner_samples]
            inner_alpha_samples = alphas[n*num_inner_samples:(n+1)*num_inner_samples]
                                                                       
                                                      
            sampled_choices = []
            numerator_log_likelihoods = []
            for inner_alpha in inner_alpha_samples:
                v0, v1 = self.env._calculate_values(ir, dr, days, outer_k)
                z = (v1 - v0) / inner_alpha
                prob = self.env.epsilon + (1 - 2 * self.env.epsilon) * norm.cdf(z)
                                                                                                             

                sampled_choice = np.random.binomial(n=1, p=prob)
                log_likelihood = np.log(prob) if sampled_choice == 1 else np.log(1 - prob)
                sampled_choices.append(sampled_choice)
                numerator_log_likelihoods.append(log_likelihood)
            log_likelihood = np.mean(numerator_log_likelihoods)
                                                                                
            marginal_log_likelihoods = []
            for idx, (inner_k, inner_alpha) in enumerate(zip(inner_k_samples, inner_alpha_samples)):
                v0, v1 = self.env._calculate_values(ir, dr, days, inner_k)
                z = (v1 - v0) / inner_alpha
                prob = self.env.epsilon + (1 - 2 * self.env.epsilon) * norm.cdf(z)
                sampled_choice = sampled_choices[idx]
                prob = prob if sampled_choice == 1 else 1 - prob
                marginal_log_likelihood = np.log(prob)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            naive_mean = np.log(np.mean(np.exp(marginal_log_likelihoods)))
                                                                                                                   
                                                                                                          
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)
                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 100000
        errs = []
        for _ in range(N):
            self.env.reset()
            k_truth = env.truth[0]
            k_pred = np.random.normal(env.k_mean, env.k_std)
            err = (k_truth - k_pred) ** 2
            errs.append(err)
        stderr = np.std(errs)
        meanerr = env.k_std**2
        return meanerr, stderr

class TemporalDiscount:
    def __init__(self, epsilon=0.01, k_mean=-4.25, k_std=0.5, alpha_scale=2):
                              
        self.epsilon = epsilon
        self.k_mean = k_mean
        self.k_std = k_std
        self.alpha_scale = alpha_scale
        self.reset()
        self.env_name = "temporal_discount"

    def reset(self):
        def sample_k_alpha():
                                                   
            log_k = np.random.normal(self.k_mean, self.k_std)
            k = np.exp(log_k)

                                                        
            alpha = halfnorm.rvs(scale=self.alpha_scale)
            return (k, alpha)

        self.truth = sample_k_alpha() 
        self.observed_data = []

    def generate_system_message(self, include_prior=True, goal=None): 
        assert goal is not None
        if include_prior:
                message = f"""{PRIOR}
{goal}
Make observations by specifying the three parameters iR, dR, D to query the person's choices, where D is a positive integer specifying
the number of days delayed. 
1 means the person selects the delayed reward and 0 means the person selects the immediate reward.
Assume the delayed reward dR is a strictly larger positive number compared to the positive immediate reward iR. 
Please specify the three integer parameters in a list [iR, dR, D].

Here is an example:
<thought> your thought </thought>
<observe>[1, 2, 3] (trivial example)</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
<thought> your thought</thought>
<answer> your answer </answer>
"""
        else:
            message = f"""{NO_PRIOR}
{goal}
In each list, the first element is smaller than the second element, and the third element is an integer.
Make observations by specifying where you want to observe in list of 3 positive numbers (integer,integer,integer).

Here is an example:
<thought> your thought </thought>
<observe>[10, 20, 1]</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>
"""
        return message
    
    def sample_random_input(self):
        iR = np.random.randint(1, 200)
        dR = np.random.randint(iR + 1, 300)
        days = np.random.randint(1, 365)
        return iR, dR, days
        
    def _calculate_values(self, iR, dR, Days, k):
                                                      
                                             
                                               
        V0 = iR
        V1 = dR / (1 + k * Days)
        return V0, V1

    def _select_delay(self, V0, V1, alpha):
                                                                      
        z = (V1 - V0) / alpha
        phi = norm.cdf(z)
        probability = self.epsilon + (1 - 2 * self.epsilon) * phi
        choice = np.random.binomial(n=1, p=probability)                                                   
        return choice
    
    def step(self, iR, dR, Days):
        k, alpha = self.truth
        V0, V1 = self._calculate_values(iR, dR, Days, k)
        choice = self._select_delay(V0, V1, alpha)
        return choice

    def validate_input(self, input_string):
                                                 
        list_string = input_string.strip("[]")
                                                                               
        items = [item.strip() for item in list_string.split(",")]
        items = [int(float(item)) for item in items]
        if len(items) != 3: return f"Item len not 3 {input_string}"
        if items[0] > items[1]: return f"item 0 not less than item 1, {input_string}"
        if items[2] <= 0: return f"item 2 not greater than 0, {input_string}"
        return np.array(items)

    def run_experiment(self, input_string):
        designs = self.validate_input(input_string)
        if isinstance(designs, str):
            return designs, False
        iR, dR, Days = designs
        choice = self.step(iR, dR, Days)
        self.observed_data.append((iR, dR, Days, choice))
        return choice, True

    def get_data(self):
        return self.observed_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return "The environment models a person's choice between a delayed reward of a certain number of days and an immediate reward."
        else:
            return "The environment models a binary response to a tuple of three positive integer values."

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["ir", "dr", "days", "Choice"]
        else:
            return ["x1", "x2", "x3", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        pass                                                                                             
           
        if self.include_prior:
            return (f"The observations are: \n -Choice: Person's choice between delayed or immediate reward. \n"
                    f"The input values are \n -ir: reward you get immediately \n -dr: reward you get after certain number of days \n -days: number of days you have to wait for the delayed reward \n"
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return ""

if __name__ == "__main__":
    predictions = []
    measurements = []
    env = TemporalDiscount()
    goal = DirectGoal(env)
                                     
    mean_error, std = goal.get_norm_factors()
    print(mean_error, std)
    goal = DiscountGoal(env)
    mean_error, std = goal.get_norm_factors()
    print(mean_error, std)
    
                                  
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             
                                   
                                                 
                             

                                    
                                                 
                             

                                   
                                   
                                                 
                             
             
             
                                       
               
                   

                             
                                                                          
        
                                                                        
                                                                  
        
                            
                                  
        
                                
                                      
    
                        
                                 
                                                           
                                                                 
                        
                       
                               
                  
                    
                

