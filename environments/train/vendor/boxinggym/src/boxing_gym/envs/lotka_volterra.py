import numpy as np
from scipy.integrate import odeint

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

class DirectGoal(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_param_cache = {}
        self.norm_mu, self.norm_sigma = (8.327445247142364, 17.548285564117467)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = f"""
Your goal is to be able to reliably predict the populations of predators and prey (two positive integers) at any given (positive float) time. Conduct experiments to learn more about the environment.
"""
        else:
            goal_description = f"""
Your goal is to be able to reliably predict the response of the environment (a tuple of two positive integers) to a given input (positive float). Conduct experiments to learn more about the environment.
"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
            time = np.round((np.random.beta(2, 5) * 4), 1)
            counts = self.env.step(time)
            self.eval_points.append((time, counts))
        else:
            time, counts = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1

        if include_prior:
            question = f"""Predict the population counts of prey and predators at time: {time}. 
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess. Answer in the format: [num of prey, num of predator].
Here is an example.
<thought> your thought </thought>
<answer>[2, 3]</answer>"""

        else:
            question = f"""
            Predict the response (tuple of two positive integers) to the following input: {time}.
When asked to answer a question about the environment, respond in the format specified below. Make assumptions about the environment and provide your best guess.
Here is an example.
<thought> your thought </thought>
<answer>[2, 3]</answer>"""
        return question, counts

    def evaluate_predictions(self, predictions, measurements):
        assert len(predictions) == len(measurements), f"Predictions and measurements must have the same length. {len(predictions)}, {len(measurements)}"
        predictions = [eval(x) for x in predictions]
        abs_error = np.abs(np.array(predictions) - np.array(measurements))
        mean_abs = np.mean(abs_error)
        std_abs = np.std(abs_error)
        return mean_abs, std_abs
    
    def get_norm_factors(self):
        N = 100000
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
            if out[0] > 1000 or out[1] > 1000:
                continue
            measurements.append(out)

        mu1 = np.mean([x[0] for x in measurements])
        mu2 = np.mean([x[1] for x in measurements])
        print(mu1,mu2)
        pred = [f"[{mu1},{mu2}]"] * len(measurements)
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        raise NotImplementedError("Expected Information Gain not implemented for this goal.")
                               
                                                   
                                                                 
                                                
                                       
                                                                               
                                                                            
                                                                               
                                                                                
                                                  
                                                         
                                                          
                                                                             
                                                                                                              
                                                                                                            
                                                                                                                    
                                                       

                                            
                                                                                   
                                                                                          
                                                                                          
                                                   
                                                                                                                                                                        
                                          
                                        
                                          
                                          
                                                                
                                           
                                                                 
                                                                                                 
               
                                                                                           
        
                                                   
                                                 
                                                   
                                                   
                              
                                                                                                                              
                                             
                                                                         
                                                                                                                                     
                                             
                                                 
                                                                                       
                                                                                           
                                                                                          

                                                                                                                        
                                                                                                                      
                                                                                                                        
                                                                                                                        
                                               
                                                                                                                                      
                                                                             
                                                                                                                                         
                                                                                     
                                                                                             
                                                                                        
                                                               
                                                                
                                                                                                                           
                                                                                  
                                              
                          

class DirectGoalNaive(DirectGoal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."

        if include_prior:
            goal_description = f"""
The goal of the user is to be able to reliably predict the population counts (tuple of two nonnegative floats) at any given time.
"""
        else:
            goal_description = f"""
The goal of the user is to be able to reliably predict a tuple of two nonnegative floats (output) for any given float (input).
"""
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = f"""
Your goal is to be able to reliably predict the population counts of prey and predator (tuple of two positive integers) at any given time.
"""
        else:
            goal_description = f"""
Your goal is to be able to reliably predict a tuple of two positive integers (output) for any given float (input).
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
        description += "Here is what you know about the environment:\n"
        return description    
    
    def get_comm_prompt(self, include_prior, com_limit=300, use_ppl=False, str_prob_prog=None, params_summary_str=None):    
        extra_prompt = ""
        if include_prior:
            extra_prompt = f"""
"""
        description = f"""
Assume that the user has no prior knowledge, and will not be able to run any experiments before making predictions. 
They will make predictions based solely on your explanation, so provide as much detail as possible. You cannot provide your own experiments or observations.
Limit your explanation to {com_limit} words
{extra_prompt}
"""
        if use_ppl:
            description += f"To make your explanation clearer and more informative, look at the statistical model (written in pymc) designed by a colleague for the experimental data and the inferred parameters. \n"
            description += f"Here is the statistical model. \n {str_prob_prog} \n"
            description += f"Here are the inferred params. \n {params_summary_str} \n"
            description += f"Don't literally describe the model verbatim but use it to conceptually motivate your explanation."
            description += f"The agent will not be able to use the model explicitly but having a conceptual understanding will be beneficial."
        return description
    
class LotkaVolterra:
    def __init__(self, 
                prey_init=40, 
                predator_init=9, 
                alpha=0.1, 
                beta=0.02, 
                gamma=0.4, 
                delta=0.01,
                lower_limit = 0,
                upper_limit = 50):
        self.prey_init = prey_init
        self.predator_init = predator_init
        self.alpha_mu = alpha
        self.beta_mu = beta
        self.gamma_mu = gamma
        self.delta_mu = delta
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.reset()
        
        self.env_name = "lotka_volterra"
    
                                  
    def reset(self):
        self.alpha = np.random.normal(self.alpha_mu, 0.01)
        self.beta = np.random.normal(self.beta_mu, 0.01)
        self.gamma = np.random.normal(self.gamma_mu, 0.04)
        self.delta = np.random.normal(self.delta_mu, 0.001)
        self.observation_data = []


    def generate_system_message(self, include_prior, goal_description):
        if include_prior:
            PRIOR = f"""You are observing the populations of predators and prey at different times.
Make observations by specifying a single time you want to observe with a float number. The environment will return the population counts of prey and predators successively.
The time values are between {self.lower_limit} and {self.upper_limit}.
"""
            message= f"""
{goal_description}
{PRIOR}

Here is an example:
<thought> your thought </thought>
<observe>2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            NO_PRIOR = f"""You may observe the value of the function one input value at a time. Make observations by specifying a single value you want to observe with a float number.
The environment will return two nonnegative floating numbers as response of the function at that input.
The input values are between {self.lower_limit} and {self.upper_limit}.
"""
            message = f"""
{goal_description}
{NO_PRIOR}

Here is an example:
<thought> your thought </thought>
<observe>2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
Example:
<thought> your thought </thought>
<answer> your answer </answer>

"""
        return message

    @staticmethod
    def lotka_volterra_system(y, t, alpha, beta, gamma, delta):
        prey, predator = y
        dprey_dt = alpha * prey - beta * prey * predator
        dpredator_dt = delta * prey * predator - gamma * predator
        return [dprey_dt, dpredator_dt]

    def sample_random_input(self):
        ti = np.random.uniform(self.lower_limit, self.upper_limit)
        return ti

    def step(self, time):
        params = [self.alpha, self.beta, self.gamma, self.delta]
        populations = [self.prey_init, self.predator_init]

                                                                                              
        solution = odeint(
            self.lotka_volterra_system, populations, [0, time], args=tuple(params)
        )

                                                                                                               
        rounded_solution = np.round(solution[-1]).astype(int)                                               
        rounded_solution = rounded_solution.clip(min=0)                                               
        rounded_solution = rounded_solution.tolist()
        return rounded_solution

    def validate_input(self, input_string):
                                                 
        try:
            query = float(input_string.strip())
        except:
            return "Input must be a float."
        if query < self.lower_limit or query > self.upper_limit:
            return f"Input must be between {self.lower_limit} and {self.upper_limit}."
                                                               
                                                                                     
                               
                                                                           
                                                                               
        return query

    def run_experiment(self, input_string):
        time = self.validate_input(input_string)
        if isinstance(time, str):
            return time, False
        result = self.step(time)
        self.observation_data.append((time, tuple(result)))
        return result, True

    def get_data(self):
        return self.observation_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""
The environment consists of the populations of predators and prey (two nonnegative floats) at any given (real number) time.
"""
        else:
            return f""""
The environment returns a response (tuple of two real numbers) to a scalar input.
"""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["t", "prey", "predator"]
        else:
            return ["t", "y1", "y2"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        if self.include_prior:
            return (f"The observations are: \n -prey: prey population -predator: predator population \n"
                    f"The input values are \n -t: time"
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return ""

if __name__ == "__main__":
    env = LotkaVolterra()
    goal = DirectGoal(env)
    print(goal.get_norm_factors())
                     
                                          
                
                                           
                         
                                                  
