import random

import numpy as np
import pymc as pm
from scipy.stats import distributions

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe


class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_parameters_cache = {}
        self.norm_mu, self.norm_sigma = 10991.5464, 15725.115658658306
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = """Your goal is to be able to predict the population count of peregrines given the time. Conduct experiments to learn about the environment and make predictions based on your observations."""
        else:
            goal_description = "Your goal is to be able to predict the integer response of the environment to a given input. Conduct experiments to learn about the environment and make predictions based on your observations."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
            ti = np.round((np.random.beta(2, 5) * 4), 1)
            pop = self.env.step(ti)
            self.eval_points.append((ti, pop))
        else:
            ti, pop = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1

        if include_prior:
            question = f"""Predict the population count (integer) of peregrines at time: {ti}. 
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>"""

        else:
            question = f"""Predict the integer-valued response to the following input: {ti}.
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>"""
        return question, pop
    
    def evaluate_predictions(self, predictions, measurements):
        assert len(predictions) == len(measurements), "Predictions and measurements must have the same length."
        predictions = [int(float(x)) for x in predictions]
        se = (np.array(predictions) - np.array(measurements)) ** 2
        mse = np.mean(se)
        std_mse = np.std(se)
        return mse, std_mse
    
    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        t_query = query_point
        existing_data = self.env.observation_data
        if tuple(existing_data) not in self.update_parameters_cache:
            print("Updating parameters cache")
            with pm.Model() as model:
                alpha = np.array([4.5])
                beta1 = np.array([1.2])
                beta2 = np.array([0.07])
                beta3 = np.array([-0.24])
                alpha_prior = pm.Normal('alphai', mu=alpha, sigma=0.1)
                beta1_prior = pm.Normal('beta1i', mu=beta1, sigma=0.1)
                beta2_prior = pm.Normal('beta2i', mu=beta2, sigma=0.01)
                beta3_prior = pm.Normal('beta3i', mu=beta3, sigma=0.05)

                def likelihood(ti, popi):
                    year_squared = np.square(ti)
                    year_cubed = year_squared * ti
                    log_lambda = alpha_prior + beta1_prior * ti + beta2_prior * year_squared + beta3_prior * year_cubed
                    return pm.Poisson("C_obs", mu=np.exp(log_lambda), observed=popi)
                
                ti_obs = pm.Data('ti_obs', [x[0] for x in existing_data])
                popi_obs = pm.Data('popi_obs', [x[1] for x in existing_data])
                likelihood(ti_obs, popi_obs)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, tune=1000, return_inferencedata=False, chains=2, cores=2, target_accept=0.95)
            alphas = trace['alphai']
            beta1s = trace['beta1i']
            beta2s = trace['beta2i']
            beta3s = trace['beta3i']
            shuffling = list(zip(alphas, beta1s, beta2s, beta3s))
            random.shuffle(shuffling)
            alphas, beta1s, beta2s, beta3s = zip(*shuffling)
            self.update_parameters_cache[tuple(existing_data)] = (alphas, beta1s, beta2s, beta3s)
        else:
            alphas, beta1s, beta2s, beta3s = self.update_parameters_cache[tuple(existing_data)]
        
        outer_alphas = alphas[:num_outer_samples]
        outer_beta1s = beta1s[:num_outer_samples]
        outer_beta2s = beta2s[:num_outer_samples]
        outer_beta3s = beta3s[:num_outer_samples]
        
        log_likelihoods = []
        for n, (alphai, beta1i, beta2i, beta3i) in enumerate(zip(outer_alphas, outer_beta1s, outer_beta2s, outer_beta3s)):
                                                                              
            with pm.Model() as model:
                year_squared = np.square(t_query)
                year_cubed = year_squared * t_query

                log_lambda = alphai + beta1i * t_query + beta2i * year_squared + beta3i * year_cubed
                                  
                C = np.random.poisson(np.exp(log_lambda))
                               
                
                prob = distributions.poisson.pmf(C, np.exp(log_lambda))
                log_likelihood = np.log(prob+0.0001)

                inner_alphas = alphas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_beta1s = beta1s[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_beta2s = beta2s[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_beta3s = beta3s[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                marginal_log_likelihoods = []
                for inner_alphai, inner_beta1i, inner_beta2i, inner_beta3i in zip(inner_alphas, inner_beta1s, inner_beta2s, inner_beta3s):
                    year_squared = np.square(t_query)
                    year_cubed = year_squared * t_query
                    log_lambda = inner_alphai + inner_beta1i * t_query + inner_beta2i * year_squared + inner_beta3i * year_cubed
                    prob = distributions.poisson.pmf(C, np.exp(log_lambda))
                    marginal_log_likelihoods.append(np.log(prob+0.0001))
                
                max_log = np.max(marginal_log_likelihoods)    
                log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
                log_likelihoods.append(log_likelihood - log_marginal_likelihood)
        eig_value = np.mean(log_likelihoods)
        return eig_value

    def get_norm_factors(self):
        N = 100   
        errs = []
        measurements = []
        import logging
        import tqdm
        logger = logging.getLogger("pymc")
        logger.setLevel(logging.WARNING)
        for i in tqdm.tqdm(range(N)):
            if i % 10 == 0:
                self.env.reset()
            inp = self.env.sample_random_input()
            out = self.env.step(inp)
            print(inp, out)
            measurements.append(out)
        mu = np.mean(measurements)
        print(mu)
        pred = [str(mu)] * N
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to be able to predict the population count (integer) of peregrines at a specific time."
        else:
            goal_description += "The goal of the user is to be able to predict the integer response of the environment to a given input."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict the population count of peregrines given the time."
        else:
            goal_description = "Your goal is to predict the integer response of the environment to a given input."
        format_instructions = """You will be provided an input to this environment and will be tasked with predicting the output for each input.
You must respond with an integer number. You may also think before providing your predictions.
Here is an example:
<thought>your thought</thought>
<answer>1</answer>"""
        description = goal_description + '\n' + format_instructions
        description += "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog=None, params_summary_str=None):
        description = f"""Assume that the user has no prior knowledge, and will not be able to run any experiments before making predictions. 
They will make predictions based solely on your explanation, so provide as much detail as possible. You CANNOT provide your own experiments or observations.
Limit your explanation to {com_limit} words"""
        if use_ppl:
            description += f"To make your explanation clearer and more informative, look at the statistical model (written in pymc) designed by a colleague for the experimental data and the inferred parameters. \n"
            description += f"Here is the statistical model. \n {str_prob_prog} \n"
            description += f"Here are the inferred params. \n {params_summary_str} \n"
            description += f"Don't literally describe the model verbatim but use it to conceptually motivate your explanation."
            description += f"The agent will not be able to use the model explicitly but having a conceptual understanding will be beneficial."
        return description
    
class Peregrines:
    def __init__(self, lower_limit=0, upper_limit=5, alpha=4.5, beta1=1.2, beta2=0.07, beta3=-0.24):
        self.alpha_mu = alpha
        self.beta1_mu = beta1
        self.beta2_mu = beta2
        self.beta3_mu = beta3
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.reset()
        self.env_name = "peregrines"

    def reset(self):
        self.observation_data = []
        
        with pm.Model() as model:   
            alpha_prior = pm.Normal('alpha', mu=self.alpha_mu, sigma=0.1)
            beta1_prior = pm.Normal('beta1', mu=self.beta1_mu, sigma=0.1)
            beta2_prior = pm.Normal('beta2', mu=self.beta2_mu, sigma=0.01)
            beta3_prior = pm.Normal('beta3', mu=self.beta3_mu, sigma=0.05)
            self.alpha = pm.draw(alpha_prior)
            self.beta1 = pm.draw(beta1_prior)
            self.beta2 = pm.draw(beta2_prior)
            self.beta3 = pm.draw(beta3_prior)

    def generate_system_message(self, include_prior=True, goal=None): 
        assert goal is not None
        if include_prior:
                message = f"""The population count of peregrine falcons varies at different times.
{goal}
Make observations by specifying a single time you want to observe with a float number. The environment will return the population count of peregrine falcons at that time.
The time values are between {self.lower_limit} and {self.upper_limit}.

Here is an example:
<thought> your thought </thought>
<observe>2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            message = f"""You are observing an integer-valued response to a float-valued input.
{goal}
You may observe the value of the function one input value at a time. Make observations by specifying a single value you want to observe with a float number.
The environment will return the integer response of the function at that input.
The input values are between {self.lower_limit} and {self.upper_limit}.

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
                                                   
        ti = np.random.uniform(self.lower_limit, self.upper_limit)
        return ti
    
    def step(self, ti):
        with pm.Model() as model:
            alpha = self.alpha
            beta1 = self.beta1
            beta2 = self.beta2
            beta3 = self.beta3
            
            year_squared = np.square(ti)
            year_cubed = year_squared * ti

            log_lambda = alpha + beta1 * ti + beta2 * year_squared + beta3 * year_cubed
            C_obs = pm.Poisson("C_obs", mu=np.exp(log_lambda))
            
            prior = pm.sample_prior_predictive(samples=1, return_inferencedata=False)
        obs = prior["C_obs"][0]
                              
        return int(obs)

    def validate_input(self, input_string):
                                                 
        try:
            query = float(input_string.strip())
        except:
            return "Input must be a float."
        if query < self.lower_limit or query > self.upper_limit:
            return f"Input must be between {self.lower_limit} and {self.upper_limit}."
                                                                  
                                                                                     
                               
                                                                         
        return query
    
    def run_experiment(self, input_string):
        ti = self.validate_input(input_string)
        if isinstance(ti, str):
            return ti, False
        result = self.step(ti)
        self.observation_data.append((ti, result))
        return result, True

    def get_data(self):
        return self.observation_data

    def get_df(self):
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f""""
The trajectory of the peregrine population breeding in the french jura from 1964 to 2003'
"""
        else:
            return f""""
x1 is the input and y is the output
"""

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["year", "C"]
        else:
            return ["x1", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def describe_data_columns(self):
        return self.format_column_description()

    def format_column_description(self):
        if self.include_prior:
            return (f"The observations are: \n -C: Population counts of Peregrines \n"
                f"The input values are \n -year: year \n"
                f"Use the values of the input values to help you model the observations. ")
        else:
            return ""


if __name__ == "__main__":
    env = Peregrines()
                                       
                  
                        
                                
                                
                    
                                     
                               
                
    goal = DirectGoal(env)
    print(goal.get_norm_factors())
                          
                                                        
                            
                                 
                          
                                                        
                            
                                 
                        
                                                        
                            

                                             
                             
                      
                        
                      
                       
                                   
                           
       

                                     
                      
                      
                                                        
                      
                                        

    

                                 
                     
                                     
                      
                                                   
                                
                         
                                     
                                
                

    