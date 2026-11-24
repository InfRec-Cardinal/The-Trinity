import random

import numpy as np
import pymc as pm
from scipy.stats import truncnorm, binom

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

class DirectDeath(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu, self.norm_sigma = (222.2998, 189.76853880440774)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to reliably predict the number of infected individuals at specific times. Conduct experiments to learn about the environment and make predictions based on your observations."
        else:
            goal_description = "Your goal is to be able to reliably predict the positive integer output of the environment for different float inputs. Conduct experiments to learn about the environment and make predictions based on your observations."
        description = self.env.get_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
                                                                            
            time = np.random.uniform(self.env.lower_bound+0.001, self.env.upper_bound)
            infected_num = self.env.step(time)
            self.eval_points.append((time, infected_num))
        else:
            time, infected_num = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1

        if include_prior:
            question = f"What is the number of infected individuals at time {time}?"
        else:
            question = f"What is the output of the environment at input {time}?"
        question = " Respond with a positive integer."
        return question, infected_num
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            parsed_predictions.append(int(float(pred)))
        mse = np.mean((np.array(parsed_predictions) - np.array(measurements)) ** 2)
        std = np.std((np.array(parsed_predictions) - np.array(measurements)) ** 2)
        return (mse, std)

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        xi = query_point
        existing_data = self.env.observation_data
        if tuple(existing_data) not in self.update_param_cache:
                                                   
            with pm.Model() as model:
                theta = pm.TruncatedNormal('theta', mu=self.env.mu, sigma=self.env.sigma,
                                        lower=self.env.lower_bound, upper=self.env.upper_bound)

                                                
                def likelihood(xi, infected_num):
                    eta = 1 - pm.math.exp(-theta * xi)
                    return pm.Binomial('infected_num', n=self.env.N, p=eta, observed=infected_num)

                xi_obs = pm.Data('xi_obs', [d[0] for d in existing_data])
                infected_num_obs = pm.Data('infected_num_obs', [d[1] for d in existing_data])
                likelihood(xi_obs, infected_num_obs)
                trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False)
            
            thetas = trace['theta']
            random.shuffle(thetas)
            updated_theta_samples = thetas[:num_outer_samples]
            print(len(trace['theta']))
            print("Updated parameters", len(updated_theta_samples))
            print(f"Inferred theta: {np.mean(updated_theta_samples)}")
            self.update_param_cache[tuple(existing_data)] = (updated_theta_samples, thetas[num_outer_samples:])
        else:
            updated_theta_samples, thetas = self.update_param_cache[tuple(existing_data)]
        
        log_likelihoods = []

        for n, outer_theta in enumerate(updated_theta_samples):
                                                                       
            eta = 1 - np.exp(-outer_theta * xi)
            inner_theta_samples = thetas[n*num_inner_samples:(n+1)*num_inner_samples]
            sampled_infected_num = np.random.binomial(self.env.N, eta)
            preds = [1 for _ in range(sampled_infected_num)] + [0 for _ in range(self.env.N - sampled_infected_num)]
            log_liks = [np.log(eta) if pred == 1 else np.log(1 - eta) for pred in preds]
            log_likelihood = np.mean(log_liks)
                                                                                
            marginal_log_likelihoods = []
            for inner_theta in inner_theta_samples:
                eta = 1 - np.exp(-inner_theta * xi)
                marginal_log_likelihood = [np.log(eta) if pred == 1 else np.log(1 - eta) for pred in preds]
                marginal_log_likelihood = np.mean(marginal_log_likelihood)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)

                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 10000
        errs = []
        outs = []
        measurements = []
        for _ in range(N):
            self.env.reset()
            sampled_input = self.env.sample_random_input()
            out = self.env.step(sampled_input)
            outs.append(out)
        mu = np.mean(outs)
        predicitons = [str(mu) for _ in range(N)]
        mean_err, std_err = self.evaluate_predictions(predicitons, outs)
        return mean_err, std_err

class DirectDeathNaive(DirectDeath):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to reliably predict the number of infected individuals at specific times. Conduct experiments to learn about the environment."
        else:
            goal_description += "The goal of the user is to reliably predict the positive integer output of the environment for different float inputs. Conduct experiments to learn about the environment."
        description = self.env.get_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict the number of infected individuals at specific times."
        else:
            goal_description = "Your goal is to predict the positive integer output of the environment for different float inputs."
        format_instructions = """You must respond with a positive integer. You may also think before providing your predictions.
Here is an example:
<thought>your thought</thought>
<answer>1</answer
"""
        description = goal_description + "\n" + format_instructions
        description += "Here is what you know about the enivronment:\n"
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
    


class InfectionRate(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu, self.norm_sigma = (0.2902838787350395, 1.756991075450312)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to reliably predict the infection rate of the disease. Conduct experiments to learn about the environment and make predictions based on your observations. The infection rate is a positive real number. It is the rate at which healthy individuals become infected. Specifically, probability of a person being infected is proportional to 1-exp(-theta*x), where theta is the infection rate and x is the time."
        else:
            raise NotImplementedError("This goal is not supported without prior information.")
        description = self.env.get_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if include_prior:
            question = f"What is the infection rate?"
        else:
            raise NotImplementedError("This goal is not supported without prior information.")
        question = " Respond with a positive real number."
        return question, self.env.theta

    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            parsed_predictions.append(float(pred))
        mse = np.mean((np.array(parsed_predictions) - np.array(measurements)) ** 2)
        std = np.std((np.array(parsed_predictions) - np.array(measurements)) ** 2)
        return (mse, std)

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        xi = query_point
        existing_data = self.env.observation_data
        if tuple(existing_data) not in self.update_param_cache:
                                                   
            with pm.Model() as model:
                theta = pm.TruncatedNormal('theta', mu=self.env.mu, sigma=self.env.sigma,
                                        lower=self.env.lower_bound, upper=self.env.upper_bound)

                                                
                def likelihood(xi, infected_num):
                    eta = 1 - pm.math.exp(-theta * xi)
                    return pm.Binomial('infected_num', n=self.env.N, p=eta, observed=infected_num)

                if len(existing_data) == 0:
                    xi_obs = pm.Data('xi_obs', [d[0] for d in existing_data])
                    infected_num_obs = pm.Data('infected_num_obs', [d[1] for d in existing_data])
                    likelihood(xi_obs, infected_num_obs)
                trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False, chains=2, cores=2, target_accept=0.95)
            
            thetas = trace['theta']
            random.shuffle(thetas)
            updated_theta_samples = thetas[:num_outer_samples]
            print(len(trace['theta']))
            print("Updated parameters", len(updated_theta_samples))
            print(f"Inferred theta: {np.mean(updated_theta_samples)}")
            self.update_param_cache[tuple(existing_data)] = (updated_theta_samples, thetas[num_outer_samples:])
        else:
            updated_theta_samples, thetas = self.update_param_cache[tuple(existing_data)]
        
        log_likelihoods = []

        for n, outer_theta in enumerate(updated_theta_samples):
                                                                       
            eta = 1 - np.exp(-outer_theta * xi)
            inner_theta_samples = thetas[n*num_inner_samples:(n+1)*num_inner_samples]
            sampled_infected_num = np.random.binomial(self.env.N, eta)
            preds = [1 for _ in range(sampled_infected_num)] + [0 for _ in range(self.env.N - sampled_infected_num)]
            log_liks = [np.log(eta) if pred == 1 else np.log(1 - eta) for pred in preds]
            log_likelihood = np.mean(log_liks)
                                                                                
            marginal_log_likelihoods = []
            for inner_theta in inner_theta_samples:
                eta = 1 - np.exp(-inner_theta * xi)
                marginal_log_likelihood = [np.log(eta) if pred == 1 else np.log(1 - eta) for pred in preds]
                marginal_log_likelihood = np.mean(marginal_log_likelihood)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)

                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 100000
        errs = []
        preds = []
        measurements = []
        for _ in range(N):
            self.env.reset()
            sampled_infection_rate = np.random.normal(self.env.mu, scale=self.env.sigma)
            true_infection_rate = self.env.theta
            preds.append(sampled_infection_rate)
            errs.append(np.mean((sampled_infection_rate - true_infection_rate)**2))
            measurements.append(true_infection_rate)
        pred_mu = np.mean(preds)
        predicitons = [str(pred_mu) for _ in range(N)]
        mean_err, _ = self.evaluate_predictions(predicitons, measurements)
        stds = np.std(errs)
        return mean_err, stds

class DeathProcess:
    def __init__(self, N=50, mu=1, sigma=1, lower_bound=0):
        self.mu = mu
        self.sigma = sigma
        self.lower_bound = lower_bound
                                                                
        self.upper_bound = 2
        self.N = N
        self.reset()
        self.env_name = "death_process"

    def reset(self):
        a, b = (self.lower_bound - self.mu) / self.sigma, (self.upper_bound - self.mu) / self.sigma
        self.theta = truncnorm(a, b, loc=self.mu, scale=self.sigma).rvs()
        self.observation_data = []

    def get_system_message(self, include_prior=True, goal=None):
        assert goal is not None, "Please provide a goal for the task."
        if include_prior:
            message = f"""There is a disease spreading in a population of {self.N} individuals. 
{goal}
Make observations by querying how many healthy individuals are infected at a specific time (positive real numbers). You cannot query at time 0. Please specify the observation time as real number. The input time must be greater than {self.lower_bound} and less than {self.upper_bound}.

Here is an example:
<thought> your thought </thought>
<observe>0.1(time to observe)</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            message = f"""You are observing a positive integer (with a maximum value of {self.N}) for a positive real input.
{goal}
The input must be greater than {self.lower_bound} and less than {self.upper_bound}.
Here is an example:
<thought> your thought </thought>
<observe>0.1</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        return message

    def sample_random_input(self):
        return np.random.uniform(self.lower_bound, self.upper_bound)

    def step(self, xi):
                                       
                            
        eta = 1 - np.exp(-self.theta * xi)
        infected_num = binom.rvs(self.N, eta)
        return infected_num

    def validate_input(self, input_string):
        try:
            act = float(input_string.strip())
        except ValueError:
            return "Error: The input must be a float."

        if act <= self.lower_bound:
            return f"Error: The input must be greater than {self.lower_bound}."
        
        if act >= self.upper_bound:
            return f"Error: The input must be less than the {self.upper_bound}."
        
                                                           
                          
                                                                      
                             
                                                                                      
                                          
        return act

    def run_experiment(self, input_string):
        xi = self.validate_input(input_string)
        if type(xi) == str:
            return xi, False
                                              
        infected_num = self.step(xi)
        self.observation_data.append((xi, infected_num))
        return infected_num, True

    def get_data(self):
        return self.observation_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""
There is a disease spreading in a population of {self.N} individuals. 
"""
        else:
            return f"""
You are observing a positive integer (with a maximum value of {self.N}) for a positive real input.
"""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["x", "infection_num"]
        else:
            return ["x1", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        pass                                                                                             
           
        if self.include_prior:
            return (f"The observations are: \n -infection_num: number of infected people at time x \n"
                    f"The input values are \n -x: time \n"
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return (f"The observations are: \n -y \n"
                    f"The input values are \n -x1 \n"
                    f"Use the values of the input values to help you model the observations. ")

if __name__ == "__main__":
    env = DeathProcess()
    goal = DirectDeath(env)
    print(goal.get_norm_factors())
                                
                                     
    
                          
                                             
                          
                                               
                            
                                               

                 
                                         
                     
                           
                                                   
                                
                    
                       
            
                                     
                                     
                         
                                             
                                                                 
                
    

    