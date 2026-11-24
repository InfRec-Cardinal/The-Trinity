import re
import random

import pymc as pm
import numpy as np

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

    
class DirectCorrectness(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_parameter_cache = {}
        self.norm_mu, self.norm_sigma = (0.5, 0.5)
                                  
        while len(self.eval_points) < 5:
            student_id = np.random.randint(0, self.env.num_students)
            question_id = np.random.randint(0, self.env.num_questions)
            result = self.env.step(student_id, question_id)
            if int(result) == 1:
                self.eval_points.append((student_id, question_id, int(result)))

        while len(self.eval_points) < 10:
            student_id = np.random.randint(0, self.env.num_students)
            question_id = np.random.randint(0, self.env.num_questions)
            result = self.env.step(student_id, question_id)
            if int(result) == 0:
                self.eval_points.append((student_id, question_id, int(result)))
        
        self.env.restricted_pair = [(student_id, question_id) for student_id, question_id, _ in self.eval_points]
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to reliably predict the correctness of a student's answer to a specific question. Respond with 1 if you think the student will respond correctly and with 0 if you think the student will answer incorrectly. Conduct experiments to learn about the environment and make predictions based on your observations."
        else:
            goal_description = "Your goal is to be able to reliably predict the boolean output (0 or 1) of the environment for different integer inputs. Conduct experiments to learn about the environment and make predictions based on your observations."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        student_id, question, response = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1
        if include_prior:
            question = f"Will student {student_id} answer question {question} correctly?"
        else:
            question = f"What is the output of the environment at input [{student_id}, {question}]?"
        return question, response
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            pred = pred.strip()
            try:
                pred = int(pred)
            except:
                                      
                pred = int(re.findall(r'\d+', pred)[-1])
            parsed_predictions.append(int(pred))
        correct = np.array(parsed_predictions) == np.array(measurements)
        accuracy = np.mean(correct)
        std = np.std(correct)
        return 1-accuracy, std
    
    def expected_information_gain(self, query_point, num_outer_samples=1000, num_inner_samples=10):
        student_id, question_id = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_parameter_cache:
                                                   
            print("Updating parameters")
            with pm.Model() as model:
                                             
                alphai = pm.Normal('alpha_inf', mu=0, sigma=1, shape=self.env.num_students)
                betai = pm.Normal('beta_inf', mu=0, sigma=1, shape=self.env.num_questions)
                if self.env.mode in ['2pl', '3pl']:
                    gammai = pm.Normal('gamma_inf', mu=0, sigma=1, shape=self.env.num_questions)


                def likelihood(si, qi, ri):
                    if self.env.mode == '1pl':
                        alpha = alphai[si]
                        beta = betai[qi]
                    elif self.env.mode == '2pl':
                        alpha = alphai[si]
                        beta = betai[qi]
                        gamma = gammai[qi]
                        pi = pm.math.invlogit(gamma * (alpha - beta))
                    return pm.Bernoulli('responsei', p=pi, observed=ri)
                
                if len(existing_data) > 0:
                    stud_obs = pm.Data('stud_obs', [d[0] for d in existing_data])
                    quest_obs = pm.Data('quest_obs', [d[1] for d in existing_data])
                    resp_obs = pm.Data('resp_obs', [d[2] for d in existing_data])
                    likelihood(stud_obs, quest_obs, resp_obs)
                trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False)
            
            alphas = trace['alpha_inf']
            betas = trace['beta_inf']
            gammas = trace['gamma_inf']
            shuffling = list(zip(alphas, betas, gammas))
            random.shuffle(shuffling)
            alphas, betas, gammas = zip(*shuffling)            
            self.update_parameter_cache[tuple(existing_data)] = (alphas, betas, gammas)
        else:
            alphas, betas, gammas = self.update_parameter_cache[tuple(existing_data)]

        log_likelihoods = []
        updated_alpha_samples = alphas[:num_outer_samples]
        updated_beta_samples = betas[:num_outer_samples]
        updated_gamma_samples = gammas[:num_outer_samples]

        for n in range(num_outer_samples):
                                                                       
            if self.env.mode == '1pl':
                prob = sigmoid(updated_alpha_samples[n][student_id] - updated_beta_samples[n][question_id])
            elif self.env.mode == '2pl':
                prob = sigmoid(updated_gamma_samples[n][question_id] *
                               (updated_alpha_samples[n][student_id] - updated_beta_samples[n][question_id]))

            sampled_choice = np.random.binomial(n=1, p=prob)
            log_likelihood = np.log(prob) if sampled_choice == 1 else np.log(1 - prob)

            inner_alphas = alphas[num_outer_samples + n*num_inner_samples:num_outer_samples + (n+1)*num_inner_samples]
            inner_betas = betas[num_outer_samples + n*num_inner_samples:num_outer_samples + (n+1)*num_inner_samples]
            inner_gammas = gammas[num_outer_samples + n*num_inner_samples:num_outer_samples + (n+1)*num_inner_samples]
                                                                                
            marginal_log_likelihoods = []
            for m in range(num_inner_samples):
                prob = sigmoid(inner_gammas[m][question_id] *
                                (inner_alphas[m][student_id] - inner_betas[m][question_id]))

                prob = prob if sampled_choice == 1 else 1 - prob
                marginal_log_likelihood = np.log(prob)
                marginal_log_likelihoods.append(marginal_log_likelihood)

                                                               
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
            s_id, q_id = self.env.sample_random_input()
            result = self.env.step(s_id, q_id)
            measurements.append(result)
        mu = np.mean(measurements)
        pred = 1 if mu > 0.5 else 0
        predictions = [str(pred)] * N
        _, std_err = self.evaluate_predictions(predictions, measurements)
        mu_pred = 0.5
        return mu_pred, std_err
        

class DirectCorrectnessNaive(DirectCorrectness):
    def __init__(self, env):
        super().__init__(env)

    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to be able to reliably predict the correctness of a student's answer to a specific question. Respond with 1 if you think the student will respond correctly and with 0 if you think the student will answer incorrectly. Conduct experiments to learn about the environment."
        else:
            goal_description += "The goal of the user is to be able to reliably predict the boolean output (0 or 1) of the environment for different integer inputs. Conduct experiments to learn about the environment."
        description = self.env.generate_system_message(include_prior, goal_description)
        return description

    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict the correctness of a student's answer to a specific question. Respond with 1 if you think the student will respond correctly and with 0 if you think the student will answer incorrectly."

            format_description = "You will be provided with a student ID and a question ID. Respond with 1 if you think the student will respond correctly and with 0 if you think the student will answer incorrectly."
        else:
            goal_description = "Your goal is to predict the boolean output of the environment for different integer inputs."
            format_description = "You will be provided with two integer inputs. Respond with 1 if you think the student will respond correctly and with 0 if you think the student will answer incorrectly."
        description = goal_description + format_description
        description += "Here is what you know about the enivronment:\n"
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

class BestStudent(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to identify the student with the highest ability. Respond with the student ID of the student you think has the highest ability. Conduct experiments to learn about the environment and make predictions based on your observations."
        else:
            raise ValueError("The naive agent cannot be evaluated without prior knowledge.")
        description = self.env.get_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
                                          
        student_id = np.argmax(self.env.responses.sum(axis=1))
        question = f"Who is the student with the highest ability?"
        return question, student_id
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            parsed_predictions.append(int(pred))
        correct = np.array(parsed_predictions) == np.array(measurements)
        accuracy = np.mean(correct)
        std = np.std(correct)
        return 1-accuracy, std

class DifficultQuestion(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to identify the most difficult question. Respond with the question ID of the question you think is the most difficult. Conduct experiments to learn about the environment and make predictions based on your observations."
        else:
            raise ValueError("The agent cannot be evaluated without prior knowledge.")
        description = self.env.get_system_message(include_prior, goal_description)
        return description

    def get_goal_eval_question(self, include_prior):
                                          
        question_id = np.argmin(self.env.responses.sum(axis=0))
        question = f"Which question is the most difficult?"
        question += f" Respond with the question ID."
        return question, question_id
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            parsed_predictions.append(int(pred))
        correct = np.array(parsed_predictions) == np.array(measurements)
        accuracy = np.mean(correct)
        std = np.std(correct)
        return 1-accuracy, std

class DiscriminatingQuestion(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to identify the most discriminating question, that can discriminate among students' abilities the most. Respond with the question ID of the question you think is the most discriminating. Conduct experiments to learn about the environment and make predictions based on your observations."
        else:
            raise ValueError("The agent cannot be evaluated without prior knowledge.")
        description = self.env.get_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
                                                                 
        gamma = np.std(self.env.responses, axis=0)
        question_id = np.argmax(gamma)
        question = f"Which question is the most discriminating?"
        question += f" Respond with the question ID."
        return question, question_id
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for pred in predictions:
            parsed_predictions.append(int(pred))
        correct = np.array(parsed_predictions) == np.array(measurements)
        accuracy = np.mean(correct)
        std = np.std(correct)
        return 1-accuracy, std

class IRT:
    def __init__(self, num_students=6, num_questions=6, mode='2pl', restricted_pair=None):
        self.num_students = num_students
        self.num_questions = num_questions
        self.mode = mode
        self.restricted_pair = restricted_pair
        self.reset()
        self.env_name = "irt"

    def reset(self):
        with pm.Model() as model:
                                    
            alpha = pm.Normal('alpha', mu=0, sigma=1, shape=self.num_students)

                                    
            beta = pm.Normal('beta', mu=0, sigma=1, shape=self.num_questions)

            if self.mode in ['2pl', '3pl']:
                                                         
                gamma = pm.Normal('gamma', mu=0, sigma=1, shape=self.num_questions)

            if self.mode == '3pl':
                                                
                c = pm.Uniform('c', lower=0, upper=1, shape=self.num_questions)

                                                             
            if self.mode == '1pl':
                p = pm.math.invlogit(alpha[:, None] - beta[None, :])
            elif self.mode == '2pl':
                p = pm.math.invlogit(gamma[None, :] * (alpha[:, None] - beta[None, :]))
            else:       
                p = c[None, :] + (1 - c[None, :]) * pm.math.invlogit(gamma[None, :] * (alpha[:, None] - beta[None, :]))

                                                                
            responses = pm.Bernoulli('responses', p=p, shape=(self.num_students, self.num_questions))

        with model:
            prior_pred = pm.sample_prior_predictive(samples=1)

                                                         
            prior_group = prior_pred.prior

                                                        
            responses_samples = prior_group['responses'].values
            self.responses = responses_samples[0, 0]
        self.observed_data = []
    
    def generate_system_message(self, include_prior=True, goal=None):
        assert goal is not None, "Goal must be provided"
        if include_prior:
            message = f"""There are {self.num_students} students and {self.num_questions} questions.
{goal}
You may query a student-question pair to check if a student got a specific question right or wrong.
Student IDs range from 0 to {self.num_students-1} and question IDs range from 0 to {self.num_questions-1}.
Make observations about the students and questions by specifying a single student-question pair in the following format: [student_id, question_id]
The environment will respond with the correctness of the student's answer to the question.

You can think before making an observation by providing your thoughts in <thought>.

Here is an example:
<thought> your thought </thought>
<observe>[1, 3](student 1 and question 3)</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            message = f"""The environment maps two integers to a boolean value. The first integer ranges from 0 to {self.num_students-1}, and the second integer ranges from 0 to {self.num_questions-1}.
The function outputs a boolean 0 or 1.
{goal}
Make observations by specifying an input in the following format: [integer 1, integer 2]
You can think before making an observation by providing your thoughts in <thought>.

Here is an example:
<thought> your thought </thought>
<observe>[1, 3]</observe>
When asked to answer a question about the environement, respond in the format specified in the question.
<thought> your thought</thought>
<answer> your answer </answer>
"""
        return message

    def validate_input(self, input_string):
        try:
            list_string = input_string.strip("[]")
            items = [item.strip() for item in list_string.split(",")]
        except:
            return "Error: The input must be a list of two integers."
        if len(items) != 2:
            return "Error: The input must be a list of two integers."
        try:
            items = [int(item) for item in items]
        except:
            return "Error: The input must be a list of two integers."
        student_id, question_id = items
        return student_id, question_id


    def sample_random_input(self):

        query_points = [(student_id, question_id) for student_id in range(self.num_students) for question_id in range(self.num_questions)]
        while True:
            query_point = random.choice(query_points)
            if query_point not in self.restricted_pair:
                break
        return query_point

    def step(self, student_id, question_id):
        obs = self.responses[student_id, question_id]
        return int(obs) 

    def run_experiment(self, input_string):
        designs = self.validate_input(input_string)
        if isinstance(designs, str):
            return designs, False
        student_id, question_id = designs
        if (student_id, question_id) in self.restricted_pair:
            return "You cannot query this observation, try again.", False
        result = self.step(student_id, question_id)
        self.observed_data.append((student_id, question_id, result))
        return  result, True

    def get_data(self):
        return self.observed_data

    def get_df(self):
        pass                                                   
           
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""There are {self.num_students} students and {self.num_questions} questions.
You may query a student-question pair to check if a student got a specific question right or wrong.
Student IDs range from 0 to {self.num_students-1} and question IDs range from 0 to {self.num_questions-1}.
You will receive observations about the student-question pairs [student_id, question_id]
The environment will respond with the correctness (binary response) of the student's answer to the question.
"""
        else:
            return f""""
The environment models a binary response to a tuple of two positive integer values.
"""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["student_id", "question_id", "correctness"]
        else:
            return ["x1", "x2", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        if self.include_prior:
            return (f"The observations are: \n -correctness: student 's choice between delayed or immediate reward. \n"
                    f"The input values are \n -student_id: student id \n -question_id: question id"
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return ""


if __name__ == "__main__":
    env = IRT(num_students=30, num_questions=10, mode='2pl', restricted_pair=[])
    print("True parameters:", env.responses)
    goal = DirectCorrectness(env)
    print(goal.get_norm_factors())

                       
                                                           
                                                          
       

                                        
                                                     
                                         

                                                     

                    
                     
                                                                                                         
               

                                      
                                                                                                     
                                                           
                          
                              

                        
                                     

                                               
                                                             
                                                              

                                                                    
                                                                                           
                                                                                               

                                                  
                                                                  

                                           
                                                                    
                                             
                                               
                                

                        
                                 
                                                                           
                               
                                                                                      
                                                                       
                               
                              
                              
                        
                