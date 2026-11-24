import numpy as np
import random
from itertools import permutations

from scipy.stats import norm
import pymc as pm

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu = 12.59
        self.norm_sigma = 38.03
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = f"""
Your goal is to be able to reliably predict the signal intensity (scalar-values) at any given {self.env.dim}-dimensional coordinate.
"""
        else:
            goal_description = f"""
Your goal is to be able to reliably predict a scalar-valued floating-point number for any given {self.env.dim}-dimensional vector.
"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
            loc = np.random.normal(0, 1, (self.env.dim, ))
            choice = self.env.signal_intensity(loc)
            self.eval_points.append((loc, choice))
        else:
            loc, choice = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1

        if include_prior:
            question = f"""
Predict the intensity at the following location: {loc}. 
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess. Answer up to two decimal places.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>
"""
            assert "location" in question
            assert "intensity" in question

        else:
            question = f"""
Predict the scalar valued quanties at the following coordinates: {loc}.
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess. Answer up to two decimal places.
Here is an example.
<thought> your thought </thought>
<answer>1</answer>
"""
            assert "location" not in question
            assert "intensity" not in question
        return question, choice 

    def evaluate_predictions(self, predictions, measurements):
        assert len(predictions) == len(measurements), "Predictions and measurements must have the same length."

        filtered_predictions = []
        filtered_measurements = []
        for prediction, measurement in zip(predictions, measurements):
            if prediction is not None:
                prediction = prediction.strip()
                if "=" in prediction:
                    prediction = prediction.split("=")[1]
                filtered_predictions.append(float(prediction))
                filtered_measurements.append(measurement)
        se = (np.array(filtered_predictions) - np.array(filtered_measurements)) ** 2
        mse = np.mean(se)
        std_mse = np.std(se)
        return mse, std_mse

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_param_cache:
            print("updating param cache")
                                                                   
            with pm.Model() as model:
                                   
                theta = pm.Normal('theta', mu=0, sigma=1, shape=(self.env.num_sources, self.env.dim))

                                                
                def likelihood(xi, obs_y):
                    intensity = self.env.b
                    for k in range(self.env.dim):
                        distance_squared = pm.math.sum((theta[k] - xi) ** 2)
                        intensity += self.env.alpha / (self.env.m + distance_squared)
                    return pm.Normal('signals', mu=intensity, sigma=self.env.sigma, observed=obs_y)

                                           
                                                                           
                if len(existing_data) > 0:
                    obs_loc = np.array([obs_point for obs_point, _ in existing_data])
                    obs_intensity = np.array([obs_intensity for _, obs_intensity in existing_data])

                                                               
                    obs_loc_data = pm.Data('obs_loc', obs_loc)
                    obs_intensity_data = pm.Data('obs_intensity', obs_intensity)

                                                                         
                    likelihood(obs_loc_data, obs_intensity_data)

                                                            
                    trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False)
                    thetas = trace['theta']
                else:
                                                                                             
                    thetas = np.random.normal(0, 1, (num_outer_samples * num_inner_samples + num_outer_samples, self.env.num_sources, self.env.dim))
                self.update_param_cache[tuple(existing_data)] = thetas
        else:
            thetas = self.update_param_cache[tuple(existing_data)]

        random.shuffle(thetas)
        outer_thetas = thetas[:num_outer_samples]

        log_likelihoods = []
        for n, outer_theta in enumerate(outer_thetas):
            inner_thetas = thetas[num_outer_samples+n * num_inner_samples:num_outer_samples+(n + 1) * num_inner_samples]
                                                                       
            intensity = self.env.b
            for k in range(len(outer_theta)):
                distance_squared = np.sum((outer_theta[k] - query_point) ** 2)
                intensity += self.env.alpha / (self.env.m + distance_squared)
            sampled_obs = np.random.normal(intensity, self.env.sigma)
            log_likelihood = norm.logpdf(sampled_obs, loc=intensity, scale=self.env.sigma)

                                                                                
            marginal_log_likelihoods = []
            for inner_theta in inner_thetas:
                intensity_inner = self.env.b
                for k in range(len(inner_theta)):
                    distance_squared = np.sum((inner_theta[k] - query_point) ** 2)
                    intensity_inner += self.env.alpha / (self.env.m + distance_squared)
                marginal_log_likelihood = norm.logpdf(sampled_obs, loc=intensity_inner, scale=self.env.sigma)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)

                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value

    def get_norm_factors(self):
        N = 100
        predictions = []
        measurements = []
        for _ in range(N):
            self.env.reset()
            loc = self.env.sample_random_input()
            signal = self.env.step(loc)
            if signal > 100: 
                continue
            measurements.append(signal)
        mu_pred = np.mean(measurements)
        predictions = [str(mu_pred.tolist()) for _ in range(len(measurements))]
        mean_mse, std_mse = self.evaluate_predictions(predictions, measurements)
        return mean_mse, std_mse

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."

        if include_prior:
            goal_description = f"""
The goal of the user is to be able to reliably predict the signal intensity (scalar-values) at any given {self.env.dim}-dimensional coordinate.
"""
        else:
            goal_description = f"""
The goal of the user is to be able to reliably predict a scalar-valued floating-point number for any given {self.env.dim}-dimensional vector.
"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = f"""
Your goal is to be able to reliably predict the signal intensity (scalar-values) at any given {self.env.dim}-dimensional coordinate.
"""
        else:
            goal_description = f"""
Your goal is to be able to reliably predict a scalar-valued floating-point number for any given {self.env.dim}-dimensional vector.
"""
        format_instructions = f"""
You will be provided with a set of inputs to this environment and will be tasked with predicting the output for each input.
You must give number values. You may also think before providing your predictions.
You must respond with a single number! 
If you do not do so, I will be penalized one million dollars and it will be a complete disaster.
Here is an example:
<thought>your thought</thought>
<answer>1</answer>"""
        description = goal_description + '\n' + format_instructions
        description = "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog=None, params_summary_str=None):    
        extra_prompt = ""
        if include_prior:
            extra_prompt = f"""
Importantly, they need to be able to predict the intensity without knowing the source locations.
Do not give an extremely detailed protocol for making predictions but rather general heuristic guidelines that do not require detailed calculations0.
Emphasize how you can make predictions without knowing the source locations.
"""
        description = f"""
Assume that the user has no prior knowledge, and will not be able to run any experiments before making predictions. 
They will make predictions based solely on your explanation, so provide as much detail as possible. Do not directly provide your experiments and observations.
Limit your explanation to {com_limit} words.
{extra_prompt}

"""
        if use_ppl:
            description += f"To make your explanation clearer and more informative, look at the statistical model (written in pymc) designed by a colleague for the experimental data and the inferred parameters. \n"
            description += f"Here is the statistical model. \n {str_prob_prog} \n"
            description += f"Here are the inferred params. \n {params_summary_str} \n"
            description += f"Don't literally describe the model verbatim but use it to conceptually motivate your explanation."
            description += f"The agent will not be able to use the model explicitly but having a conceptual understanding will be beneficial."
        return description
    

class SourceGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu = 1.57
        self.norm_sigma = 1.15385
    
    def get_system_message(self, include_prior):
        if not include_prior:
            raise ValueError("SourceGoal requires prior knowledge.")
        goal_description = f"""
Your goal is to be able to predict the locations ({self.env.dim}-dimensional coordinates) of {self.env.num_sources} signal sources. 
"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        assert include_prior, "SourceGoal requires prior knowledge."
        true_theta = self.env.true_theta 
        question = f"""
Please predict {self.env.num_sources} {self.env.dim}-dimensional coordinates of the signal sources. 
Format your prediction as a list of {self.env.num_sources} lists of {self.env.dim} values. Answer up to two decimal places. 
Here is an example prediction: '[{', '.join(['[' + ', '.join(['1' for _ in range(self.env.dim)]) + ']' for _ in range(self.env.num_sources)])}]'
"""
        return question, true_theta 
    
    def evaluate_predictions(self, predictions, measurements):

        assert len(predictions) == len(measurements), "Predictions and measurements must have the same length."

                                                                  
        predictions = [eval(x) for x in predictions]

        def permuted_mse(prediction, true_theta):
            assert type(prediction) == list
            estimated_locations = np.array(prediction)
            if estimated_locations.shape != true_theta.shape:
                raise ValueError("The shape of the estimated locations must match the shape of the true locations.")

            lowest_mse = float('inf')
            for permuted_estimated in permutations(estimated_locations):
                se = (self.env.true_theta - np.array(permuted_estimated)) ** 2
                mse = np.mean(se)

                if mse < lowest_mse:
                    lowest_mse = mse

            return lowest_mse
        
        mses = [permuted_mse(predictions[i], measurements[i]) for i in range(len(predictions))]
        return np.mean(mses), np.std(mses)

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_param_cache:
            print("updating param cache")
                                                                   
            with pm.Model() as model:
                                   
                theta = pm.Normal('theta', mu=0, sigma=1, shape=(self.env.num_sources, self.env.dim))

                                                
                def likelihood(xi, obs_y):
                    intensity = self.env.b
                    for k in range(self.env.dim):
                        distance_squared = pm.math.sum((theta[k] - xi) ** 2)
                        intensity += self.env.alpha / (self.env.m + distance_squared)
                    return pm.Normal('signals', mu=intensity, sigma=self.env.sigma, observed=obs_y)

                                           
                                                                           
                if len(existing_data) > 0:
                    obs_loc = np.array([obs_point for obs_point, _ in existing_data])
                    obs_intensity = np.array([obs_intensity for _, obs_intensity in existing_data])

                                                               
                    obs_loc_data = pm.Data('obs_loc', obs_loc)
                    obs_intensity_data = pm.Data('obs_intensity', obs_intensity)

                                                                         
                    likelihood(obs_loc_data, obs_intensity_data)

                                                            
                    trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False)
                    thetas = trace['theta']
                else:
                                                                                             
                    thetas = np.random.normal(0, 1, (num_outer_samples * num_inner_samples + num_outer_samples, self.env.num_sources, self.env.dim))
                self.update_param_cache[tuple(existing_data)] = thetas
        else:
            thetas = self.update_param_cache[tuple(existing_data)]

        random.shuffle(thetas)
        outer_thetas = thetas[:num_outer_samples]

        log_likelihoods = []
        for n, outer_theta in enumerate(outer_thetas):
            inner_thetas = thetas[num_outer_samples+n * num_inner_samples:num_outer_samples+(n + 1) * num_inner_samples]
                                                                       
            intensity = self.env.b
            for k in range(len(outer_theta)):
                distance_squared = np.sum((outer_theta[k] - query_point) ** 2)
                intensity += self.env.alpha / (self.env.m + distance_squared)
            sampled_obs = np.random.normal(intensity, self.env.sigma)
            log_likelihood = norm.logpdf(sampled_obs, loc=intensity, scale=self.env.sigma)

                                                                                
            marginal_log_likelihoods = []
            for inner_theta in inner_thetas:
                intensity_inner = self.env.b
                for k in range(len(inner_theta)):
                    distance_squared = np.sum((inner_theta[k] - query_point) ** 2)
                    intensity_inner += self.env.alpha / (self.env.m + distance_squared)
                marginal_log_likelihood = norm.logpdf(sampled_obs, loc=intensity_inner, scale=self.env.sigma)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
            max_log = np.max(marginal_log_likelihoods)
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)

                                                   
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 1000000
        predictions = []
        measurements = []
        errs = []
        for _ in range(N):
            self.env.reset()
                                       
            sources = np.random.normal(0, 1, (self.env.num_sources, self.env.dim))
            theta = self.env.true_theta
            err = np.mean((sources - theta) ** 2)
            errs.append(err)
            measurements.append(theta)
        mu = np.zeros_like(theta)
        predictions = [str(mu.tolist()) for _ in range(N)]
        std = np.std(errs)
        mean_mse, _ = self.evaluate_predictions(predictions, measurements)
        return mean_mse, std

class Signal:
    def __init__(self, num_sources=3, dim=2, b=1e-1, m=1e-4, alpha=1, sigma=0.5):
                              
        self.b = b
        self.m = m
        self.alpha = alpha
        self.sigma = sigma

                              
        self.num_sources = num_sources
        self.dim = dim                        
        self.reset()
        self.env_name = "location_finding"
    
    def reset(self):
        self.observed_data = []
                                                                     
        self.true_theta = np.random.normal(0, 1, (self.num_sources, self.dim))

    def generate_system_message(self, include_prior, goal_description):
        if include_prior:
            PRIOR = f"""The intensity at any point in the grid is determined by the superposition of signals from {self.num_sources} sources.
Each source emits a signal of identical strength. 
Note that the location of the sources is unknown to us!
Make observations by specifying a single point where you want to measure the signal in a length-{self.dim} list of floating-point numbers enclosed by double brackets. 
"""
            message= f"""{PRIOR}
{goal_description}
Here is an example:
<thought> your thought </thought>
<observe>[0.5, 1]</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            NO_PRIOR = f"""Each point on the grid (a {self.dim}-dimensional vector) has an associated floating-point number. 
Make observations by specifying a single point where you want to observe in a {self.dim} list of floating-point numbers. 
"""
            message = f"""{NO_PRIOR}
{goal_description}
Here is an example:
<thought> your thought </thought>
<observe>[0.5, 1]</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>
"""
        return message
    
    def sample_random_input(self):
        point = []
        for _ in range(self.dim):
            point.append(np.random.uniform(-2, 2))
        return np.array(point)

    def signal_intensity(self, xi):
        total_intensity = self.b
        for k in range(len(self.true_theta)):
            distance_squared = np.sum((self.true_theta[k] - xi) ** 2)
            total_intensity += self.alpha / (self.m + distance_squared)
        return total_intensity

    def step(self, xi):
        intensity = self.signal_intensity(xi)
        noisy_intensity = np.random.normal(intensity, self.sigma)
        return noisy_intensity
    
    def validate_input(self, input_string):
        try:
            data = input_string.strip()
            data = input_string.strip("[]")
            data = [item.strip() for item in data.split(",")]
            data = [float(item) for item in data] 
        except:
            return "Error: Input must be a list of floating-point numbers."
        if len(data) != self.dim:
            return "Error: Input must be a list of length equal to the dimension of the environment."
        return np.array(data)

    def run_experiment(self, input_string):
        query = self.validate_input(input_string)
        if type(query) == str:
            return query, False
        obs = self.step(query)
                                            
        obs = float(obs)
                                   
        obs = round(obs, 2)
                                             
        query = tuple(query.tolist())
        self.observed_data.append((query, obs))
        return obs, True

    def get_data(self):
        return self.observed_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""The intensity at any point in the grid is determined by the superposition of signals from {self.num_sources} sources.
Each source emits a signal of identical strength. 
Note that the location of the sources is unknown to us!
"""
        else:
            return f"""Each point on the grid (a {self.dim}-dimensional vector) has an associated floating-point number. 
Make observations by specifying a single point where you want to observe in a {self.dim} list of floating-point numbers. 
"""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["x1", "x2", "signal_strength"]
        else:
            return ["x1", "x2", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        pass                                                                                             
           
        if self.include_prior:
            return (f"The observations are: \n -signal_strength: signal strength at the x1, x2 location \n"
                    f"The input values are \n -x1: x1 coordinate \n -x2: x2 coordinate \n"
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return ""

if __name__ == "__main__":
    env = Signal(3, 2)
    goal = DirectGoal(env)
    print(goal.get_norm_factors())
                                 
                                                          
                         
                                             
                                       
                 
                  
                                                  
                                 
                                     
                                  
                               
                 
                                                    
    
                               
                                                    
                
                           
                            
                            
                            
                            
                             
                             
                             
                             
                          
       
                                                                   
                       
                        
                                                     
                             
                                                             
                                             

                                                                             
                                             

                                        
                                        
                 

                       
                           
                                            
                                                                      
                                                               
                              
                                  

                                             
                                                                      

                                          
                                
                                                                                                                      
                               
                     
                     
                              
                
                           
