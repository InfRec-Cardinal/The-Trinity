import re
import random

import numpy as np
import pymc as pm
from scipy.stats import norm
import openai

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

class DirectPrediction(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_params_cache = {}
        self.norm_mu, self.norm_sigma = (0.424, 0.494190246767376)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to be able to predict the choice of the participant in the Moral Machine experiment based on the descriptions of the characters in each group and the intervention the car would take. Conduct experiments to gather data and build a model that can predict the participant's choice."
        else:
            raise ValueError("Goal description not provided.")
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
        
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer+1 > len(self.eval_points):
            print("Generating new eval point")
                                                                                   
            num_ones = sum([1 for _, _, _, choice in self.eval_points if int(choice) == 2])
            num_zeros = sum([1 for _, _, _, choice in self.eval_points if int(choice) == 1])
            if num_ones > num_zeros:
                target = 1
            else:
                target = 2
            while True:
                                                 
                num_chars_1 = np.random.randint(1, 5)
                num_chars_2 = np.random.randint(1, 5)
                group1 = np.random.choice(self.env.characters, num_chars_1, replace=True)
                group2 = np.random.choice(self.env.characters, num_chars_2, replace=True)
                intervention = np.random.choice(['swerve', 'stay'])
                _, choice = self.env.step(group1, group2, intervention)
                if choice == target:
                    break
    
            self.eval_points.append((group1, group2, intervention, choice))
        else:
            group1, group2, intervention, choice = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1
        assert include_prior == True, "Include prior must be True for this goal."
        question = f"""\n Question: The participant was presented with the following scenario:
Group 1: {group1}
Group 2: {group2}
Intervention: {intervention}
What choice do you predict the participant made? (1 for group 1, 2 for group 2)"""
        return question, choice
    
    def evaluate_predictions(self, predictions, measurements):
        parsed_predictions = []
        for p in predictions:
            if "2" in p:
                parsed_predictions.append(2)
            elif "1" in p:
                parsed_predictions.append(1)
            else:
                print("prediction not parsed", p)
                parsed_predictions.append(None)
        correctness = [parsed_predictions[i]==measurements[i] for i in range(len(predictions))]
        accuracy = sum(correctness) / len(correctness)
        std = np.std(np.array(correctness))
        return (accuracy, std)
    
    def expected_information_gain(self, query_point, num_outer_samples=100, num_inner_samples=10):
        group1, group2, intervention = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_params_cache:
            with pm.Model() as model:
                                                    
                beta_intervention = pm.Normal('beta_interventioni', mu=-0.3, sigma=0.1)                           
                beta_group = pm.Normal('beta_groupi', mu=0.4, sigma=0.1)                          
                beta_gender = pm.Normal('beta_genderi', mu=-0.3, sigma=0.1)                   
                beta_fitness = pm.Normal('beta_fitnessi', mu=0.4, sigma=0.1)                   
                beta_social_status = pm.Normal('beta_social_statusi', mu=0.1, sigma=0.1)                         
                                                                                                       
                beta_age = pm.Normal('beta_agei', mu=0.1, sigma=0.1)                     
                beta_human_count = pm.Normal('beta_human_counti', mu=0.7, sigma=0.1)                           
                beta_species = pm.Normal('beta_speciesi', mu=0.6, sigma=0.1)  

                                     
                alpha = pm.Normal('alphai', mu=0, sigma=0.3)

                            
                def likelihood(obs_count_diff, obs_gender, obs_age, obs_social_status, obs_fitness, obs_species, obs_intervention, obs_choice):
                    y_hat = (alpha + obs_count_diff + beta_group +
                                beta_gender * obs_gender + beta_age * obs_age +                                         
                                beta_social_status * obs_social_status + beta_fitness * obs_fitness +
                                beta_species * obs_species + beta_intervention * obs_intervention)
                    return pm.Bernoulli('choicei', logit_p=y_hat, observed=obs_choice)

                                   
                if len(existing_data) > 0:
                    obs_features = []
                    for ed in existing_data:
                        obs = {}
                        group1, group2, intervention, choice = ed
                        group1_human_count = len([char for char in group1 if char in self.env.characters[:-2]])
                        group2_human_count = len([char for char in group2 if char in self.env.characters[:-2]])

                        human_count_diff = group1_human_count - group2_human_count
                        intervention_val = 1 if intervention == 'swerve' else -1
                                                                     

                        group1_attrs = [self.env._get_char_attr(char) for char in group1]
                        group2_attrs = [self.env._get_char_attr(char) for char in group2]
                        gender_diff = sum([att["gender"] for att in group1_attrs]) - sum([att["gender"] for att in group2_attrs])
                        age_diff = sum([att["age"] for att in group1_attrs]) - sum([att["age"] for att in group2_attrs])
                        social_status_diff = sum([att["social_status"] for att in group1_attrs]) - sum([att["social_status"] for att in group2_attrs])
                        fitness_diff = sum([att["fitness"] for att in group1_attrs]) - sum([att["fitness"] for att in group2_attrs])
                        species_diff = sum([att["species"] for att in group1_attrs]) - sum([att["species"] for att in group2_attrs])
                        obs['count'] = human_count_diff
                        obs['gender'] = gender_diff
                        obs['age'] = age_diff
                        obs['social_status'] = social_status_diff
                        obs['fitness'] = fitness_diff
                        obs['species'] = species_diff
                        obs['intervention'] = intervention_val
                        obs_features.append(obs)
                                
                    obs_count_diff = pm.Data('obs_count_diff', [obs['count'] for obs in obs_features])
                    obs_gender = pm.Data('obs_gender', [obs['gender'] for obs in obs_features])
                    obs_age = pm.Data('obs_age', [obs['age'] for obs in obs_features])
                    obs_social_status = pm.Data('obs_social_status', [obs['social_status'] for obs in obs_features])
                    obs_fitness = pm.Data('obs_fitness', [obs['fitness'] for obs in obs_features])
                    obs_species = pm.Data('obs_species', [obs['species'] for obs in obs_features])
                    obs_intervention = pm.Data('obs_intervention', [obs['intervention'] for obs in obs_features])
                    obs_choice = pm.Data('obs_choice', [1-d[3]+1 for d in existing_data])
                                   
                    likelihood(obs_count_diff, obs_gender, obs_age, obs_social_status, obs_fitness, obs_species, obs_intervention, obs_choice)
                
                trace = pm.sample(num_outer_samples * num_inner_samples + num_outer_samples, tune=1000, return_inferencedata=False, chains=2, cores=2, target_accept=0.95)
                
            beta_human_counts = trace['beta_human_counti']
            beta_gender = trace['beta_genderi']
            beta_group = trace['beta_groupi']
            beta_age = trace['beta_agei']
            beta_social_status = trace['beta_social_statusi']
            beta_fitness = trace['beta_fitnessi']
            beta_species = trace['beta_speciesi']
            beta_interventions = trace['beta_interventioni']
            alphas = trace['alphai']
            
            shuffling = list(zip(beta_human_counts, beta_group, beta_gender, beta_age, beta_social_status, beta_fitness, beta_species, beta_interventions, alphas))            
            random.shuffle(shuffling)
            beta_human_counts, beta_group, beta_gender, beta_age, beta_social_status, beta_fitness, beta_species, beta_interventions, alphas = zip(*shuffling)
            self.update_params_cache[tuple(existing_data)] = (beta_human_counts, beta_group, beta_gender, beta_age, beta_social_status, beta_fitness, beta_species, beta_interventions, alphas)
        else:
            beta_human_counts, beta_group, beta_gender, beta_age, beta_social_status, beta_fitness, beta_species, beta_interventions, alphas = self.update_params_cache[tuple(existing_data)]
        
        outer_beta_human_counts = beta_human_counts[:num_outer_samples]
        outer_beta_group = beta_group[:num_outer_samples]
        outer_beta_gender = beta_gender[:num_outer_samples]
        outer_beta_age = beta_age[:num_outer_samples]
        outer_beta_social_status = beta_social_status[:num_outer_samples]
        outer_beta_fitness = beta_fitness[:num_outer_samples]
        outer_beta_species = beta_species[:num_outer_samples]
        outer_beta_interventions = beta_interventions[:num_outer_samples]
        outer_alphas = alphas[:num_outer_samples]
        
        log_likelihoods = []
                                     
        group1, group2, intervention = query_point
        obs = {}
        group1_human_count = len([char for char in group1 if char in self.env.characters[:-2]])
        group2_human_count = len([char for char in group2 if char in self.env.characters[:-2]])

        human_count_diff = group1_human_count - group2_human_count
        intervention_val = 1 if intervention == 'swerve' else -1

        group1_attrs = [self.env._get_char_attr(char) for char in group1]
        group2_attrs = [self.env._get_char_attr(char) for char in group2]
        gender_diff = sum([att["gender"] for att in group1_attrs]) - sum([att["gender"] for att in group2_attrs])
        age_diff = sum([att["age"] for att in group1_attrs]) - sum([att["age"] for att in group2_attrs])
        social_status_diff = sum([att["social_status"] for att in group1_attrs]) - sum([att["social_status"] for att in group2_attrs])
        fitness_diff = sum([att["fitness"] for att in group1_attrs]) - sum([att["fitness"] for att in group2_attrs])
        species_diff = sum([att["species"] for att in group1_attrs]) - sum([att["species"] for att in group2_attrs])
        
        for n, (ob_human_counts, ob_group, ob_gender, ob_age, ob_social_status, ob_fitness, ob_species, ob_interventions, ob_alphas) in enumerate(zip(outer_beta_human_counts, outer_beta_group, outer_beta_gender, outer_beta_age, outer_beta_social_status, outer_beta_fitness, outer_beta_species, outer_beta_interventions, outer_alphas)):
                                
            with pm.Model() as model:
                y_hat = (ob_alphas + ob_human_counts * human_count_diff + ob_group +
                         ob_gender * gender_diff + ob_age * age_diff + ob_social_status * social_status_diff + ob_fitness * fitness_diff + ob_species * species_diff + ob_interventions * intervention_val)
                prob = 1/(1 + np.exp(-y_hat))
                sampled_choice = np.random.binomial(1, prob)
                prob = prob if sampled_choice == 1 else 1 - prob
                log_likelihood = np.log(prob)
                in_human_counts = beta_human_counts[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_group = beta_group[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_gender = beta_gender[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_age = beta_age[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_social_status = beta_social_status[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_fitness = beta_fitness[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_species = beta_species[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_interventions = beta_interventions[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                in_alphas = alphas[num_outer_samples + n * num_inner_samples: num_outer_samples + (n+1) * num_inner_samples]
                
                marginal_log_likelihoods = []
                for i_human_count, i_group, i_gender, i_age, i_social_status, i_fitness, i_species, i_interventions, i_alphas in zip(in_human_counts, in_group, in_gender, in_age, in_social_status, in_fitness, in_species, in_interventions, in_alphas):
                    y_hat = (i_alphas + i_human_count * human_count_diff + i_group + i_gender * gender_diff + i_age * age_diff + i_social_status * social_status_diff + i_fitness * fitness_diff + i_species * species_diff + i_interventions * intervention_val)
                    prob = 1/(1 + np.exp(-y_hat))
                    marginal_log_likelihood = np.log(prob) if sampled_choice == 1 else np.log(1 - prob)
                    marginal_log_likelihoods.append(marginal_log_likelihood)
                
            max_log = np.max(marginal_log_likelihoods)    
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)
        
        eig_value = np.mean(log_likelihoods)
        return eig_value
    
    def get_norm_factors(self):
        N = 1000    
        errs = []
        measurements = []
        import logging
        import tqdm
        logger = logging.getLogger("pymc")
        logger.setLevel(logging.WARNING)
        for i in tqdm.tqdm(range(N)):
            if i % 100 == 0:
                self.env.reset()
            inp1, inp2, inp3 = self.env.sample_random_input()
            out, choice = self.env.step(inp1, inp2, inp3)
            measurements.append(choice)
        mu = np.mean(measurements)
        pred = [str(mu)] * N
        err_mean, err_std = self.evaluate_predictions(pred, measurements)
        return err_mean, err_std

class DirectPredictionNaive(DirectPrediction):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to be able to predict the choice of the participant in the Moral Machine experiment based on the descriptions of the characters in each group and the intervention the car would take to save a group."
        else:
            raise ValueError("Moral prediction task requires prior information. Please set include_prior to True.")
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = """The Moral Machine is an experiment where participants are presented with moral dilemmas involving autonomous vehicles. In each dilemma, the vehicle must decide between two outcomes, each involving the death of a different group of characters.
Your goal is to predict the choice of the participant in the Moral Machine experiment based on the descriptions of the characters in each group and the intervention the car would take to save a group.
The intervention the car can take ('swerve' or 'stay'). The two groups involved are passengers and pedestrians.
The participant can provide their choice of which group to save (1 for group 1, 2 for group 2).
"""
        else:
            raise ValueError("Morals task requires prior information. Please set include_prior to True.")
        format_instructions = """Answer the question in the following format:
1 for group 1, 2 for group 2
You may think before prividing your answer. Here is an example:
<thought>your thought</thought>
<answer>your answer in the specified format</answer>"""
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

class MoralMachine:
    def __init__(self, model_name="gpt-4o"):
        self.model_name = model_name
        self.env_name = "moral"
        if "gpt-4o" in model_name:
            self.llm = openai.OpenAI()
        else:
            raise ValueError("Model not supported")
        self.characters = ['stroller', 'boy', 'girl', 'pregnant_woman', 'male_doctor', 'female_doctor',
                        'female_athlete', 'male_athlete', 'female_executive', 'male_executive',
                        'large_woman', 'large_man', 'homeless', 'old_man', 'old_woman', 'criminal', 'dog', 'cat']

        self.attributes = ['gender', 'fitness', 'social_status', 'lawful', 'age', 'human']
        self.model = self._build_model()
                                                              
        self.system = """You have to make choices in a moral dilemma involving autonomous vehicles. In each dilemma, the vehicle must decide between two outcomes, each involving the death of a different group of characters.
There are two groups of characters, and the vehicle must decide which group to save. You can query the participant for their decision by providing the descriptions of the characters in each group and the intervention the car would take ('swerve' or 'stay' to save group 1).
The characters can be any of the following: {characters}
Translate the decision that is shown to you in natural language and provide reasons for it.
The importance that you place on the different attributes of the characters affects your decision. Values range from -1 to 1, with 0 being neutral.
Your preferences are as follows:
- Preference for human count: {beta_human_count}
- Preference for group 1 (passengers): {beta_group}
- Preference for males: {beta_gender}
- Preference for young: {beta_age}
- Social status: {beta_social_status}
- Preference for Fitness: {beta_fitness}
- Preference for humans over pets: {beta_species}
- Preference for having to take an action: {beta_intervention}
DO NOT talk about the values of preferences directly in your response. Only talk about the most salient reasons for the decision. Be concise, write one sentence only.
"""
        self.user_template = """Translate the decision that is shown to you in natural language and provide reasons for it.
The scenario presented to you was as follows:
Group 1: {group1}
Group 2: {group2}
Intervention: {intervention}
Choice made: {choice}
Translate the decision that is shown to you in natural language and provide reasons for it.
Only talk about the most salient reasons for the decision.
The sentence should be concise and should not refer to the importance factors/values directly.
Start with "I choose to save group 1/group 2 because...". Be concise and faithful to the importance weights.
"""
        self.reset()
        
    def _build_model(self):
        with pm.Model() as model:
                                                
            beta_intervention = pm.Normal('beta_intervention', mu=-0.3, sigma=0.1)                           
            beta_group = pm.Normal('beta_group', mu=0.4, sigma=0.1)                          
            beta_gender = pm.Normal('beta_gender', mu=-0.3, sigma=0.1)                   
            beta_fitness = pm.Normal('beta_fitness', mu=0.4, sigma=0.1)                   
            beta_social_status = pm.Normal('beta_social_status', mu=0.1, sigma=0.1)                         
                                                                                                   
            beta_age = pm.Normal('beta_age', mu=0.1, sigma=0.1)                     
            beta_human_count = pm.Normal('beta_human_count', mu=0.7, sigma=0.1)                           
            beta_species = pm.Normal('beta_species', mu=0.6, sigma=0.1)  

                                 
            alpha = pm.Normal('alpha', mu=0, sigma=0.3)
        return model

    def calculate_attr_diff(self, group1, group2, attribute):
        if attribute == 'gender':
            return len([char for char in group1 if 'man' in char or 'woman' in char]) - len([char for char in group2 if 'man' in char or 'woman' in char])
        elif attribute == 'age':
            return len([char for char in group1 if 'elderly' in char]) - len([char for char in group2 if 'elderly' in char])
        elif attribute == 'social_status':
            return len([char for char in group1 if 'executive' in char or 'homeless' in char or 'criminal' in char]) - len([char for char in group2 if 'executive' in char or 'homeless' in char or 'criminal' in char])
        elif attribute == 'fitness':
            return len([char for char in group1 if 'athlete' in char]) - len([char for char in group2 if 'athlete' in char])
        elif attribute == 'species':
            return len([char for char in group1 if 'dog' in char or 'cat' in char]) - len([char for char in group2 if 'dog' in char or 'cat' in char])
        elif attribute == 'human':
            return len([char for char in group1 if 'human' in char]) - len([char for char in group2 if 'human' in char])
        else:
            return 0

    def reset(self):
                                                         
        with self.model:
            self.alpha = pm.draw(self.model['alpha'])
            self.beta_human_count = pm.draw(self.model['beta_human_count'])
            self.beta_gender = pm.draw(self.model['beta_gender'])
            self.beta_age = pm.draw(self.model['beta_age'])
            self.beta_social_status = pm.draw(self.model['beta_social_status'])
            self.beta_fitness = pm.draw(self.model['beta_fitness'])
            self.beta_species = pm.draw(self.model['beta_species'])
            self.beta_intervention = pm.draw(self.model['beta_intervention'])
            self.beta_group = pm.draw(self.model['beta_group'])
                                                                 
        self.observed_data = []

    def generate_system_message(self, include_prior=True, goal_description=None):
        if include_prior:
            message = f"""The Moral Machine is an experiment where participants are presented with moral dilemmas involving autonomous vehicles. In each dilemma, the vehicle must decide between two outcomes, each involving the death of a different group of characters.
{goal_description}
You may query the participant for their decision by providing the descriptions of the characters in each group and the intervention the car would take ('swerve' or 'stay'). The two groups involved are passengers and pedestrians.
The participant will provide their choice of which group to save (1 for group 1, 2 for group 2).
Provide the characters in group 1 (passengers) and 2 (pedestrians) in the following format:
<observe>
Group 1: [character1, character2, ...] 
Group 2: [character1, character2, ...]
Intervention: intervention (swerve to save group 1 or stay to save group 1)
</observe>
Characters can be any of: {', '.join(self.characters)}  
You can reflect before making an observation by providing your thoughts in <thought>.

Here is an example:
<thought> This scenario tests whether people value the young over the elderly. </thought>
<observe>
Group 1: [boy, girl]
Group 2: [elderly_man, elderly_woman] 
Intervention: swerve
</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            message = goal_description
        return message
    
    def _get_char_attr(self, character):
        attrs = {
            "count": 1,
            "gender": None,
            "age": None,
            "social_status": None,
            "fitness": None,
            "species": None,
        }
        if character in ["boy", "male_doctor", "male_athlete", "male_executive", "large_man", "old_man"]:
            attrs["gender"] = 0        
        elif character in ["girl", "female_doctor", "female_athlete", "female_executive", "large_woman", "old_woman", "pregnant_woman"]:
            attrs["gender"] = -1          
        else:
            attrs["gender"] = 0           

        if character in ["boy", "girl"]:
            attrs["age"] = 1         
        elif character in ["old_man", "old_woman"]:
            attrs["age"] =  0          
        else:
            attrs["age"] = 0

        if character in ["male_doctor", "female_doctor", "male_executive", "female_executive"]:
            attrs["social_status"] = 1               
        elif character in ["homeless"]:
            attrs["social_status"] = 0              
        elif character in ["pregnant_woman"]:
            attrs["social_status"] = 1.5
        else:
            attrs["social_status"] = 0

        if character in ["male_athlete", "female_athlete"]:
            attrs["fitness"] = 1       
        elif character in ["large_man", "large_woman"]:
            attrs["fitness"] = -1         
        else:
            attrs["fitness"] = 0                   

        if character in ["dog", "cat"]:
            attrs["species"] = -1          
        else:
            attrs["species"] = 1         

        return attrs

    def sample_random_input(self):
        group1_count = np.random.randint(1, 5)
        group2_count = np.random.randint(1, 5)
        group1 = np.random.choice(self.characters, group1_count, replace=True)
        group2 = np.random.choice(self.characters, group2_count, replace=True)
        intervention = np.random.choice(['swerve', 'stay'])
                                     
        group1 = tuple(group1.tolist())
        group2 = tuple(group2.tolist())
        intervention = str(intervention)
        return group1, group2, intervention
        
    def step(self, group1, group2, intervention):
                                 
        group1_human_count = len([char for char in group1 if char in self.characters[:-2]])
        group2_human_count = len([char for char in group2 if char in self.characters[:-2]])

        human_count_diff = group1_human_count - group2_human_count
        intervention_val = 1 if intervention == 'swerve' else -1
                                                     

        group1_attrs = [self._get_char_attr(char) for char in group1]
        group2_attrs = [self._get_char_attr(char) for char in group2]
        gender_diff = sum([att["gender"] for att in group1_attrs]) - sum([att["gender"] for att in group2_attrs])
        age_diff = sum([att["age"] for att in group1_attrs]) - sum([att["age"] for att in group2_attrs])
        social_status_diff = sum([att["social_status"] for att in group1_attrs]) - sum([att["social_status"] for att in group2_attrs])
        fitness_diff = sum([att["fitness"] for att in group1_attrs]) - sum([att["fitness"] for att in group2_attrs])
        species_diff = sum([att["species"] for att in group1_attrs]) - sum([att["species"] for att in group2_attrs])
        
        with pm.Model() as model:
            y_hat = (self.alpha + self.beta_human_count * human_count_diff + self.beta_group +
                        self.beta_gender * gender_diff + self.beta_age * age_diff +                                         
                        self.beta_social_status * social_status_diff + self.beta_fitness * fitness_diff +
                        self.beta_species * species_diff + self.beta_intervention * intervention_val)
            choice = pm.Bernoulli('choice', logit_p=y_hat)
            trace = pm.sample_prior_predictive(samples=1, model=model)
        choice = 1 - int(trace['prior']['choice'][0][0]) + 1
        query = self.user_template.format(group1=group1, group2=group2, intervention=intervention, choice=choice)
        character_string = ', '.join(self.characters)
        system = self.system.format(characters=character_string,
                        beta_human_count=self.beta_human_count,
                        beta_gender=self.beta_gender,
                        beta_group=self.beta_group,
                                                     
                        beta_age=self.beta_age,
                        beta_social_status=self.beta_social_status,
                        beta_fitness=self.beta_fitness,
                        beta_species=self.beta_species,
                        beta_intervention=self.beta_intervention)
                       
                      
        if "gpt-4o" in self.model_name:
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "value": system
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "value": query
                        }
                    ]
                }
            ]
            full_response = self.llm.chat.completions.create(model=self.model_name, messages=messages, max_tokens=512, temperature=0.7)                 
            response = full_response.choices[0].message.content

        response = f"The participant responded with: {response}\n"
        
        return response, choice
    
    def validate_input(self, input_string):
        try:
            group1 = re.search(r'Group 1: \[(.*?)\]', input_string).group(1)
            group1 = group1.split(', ')
            group2 = re.search(r'Group 2: \[(.*?)\]', input_string).group(1)
            group2 = group2.split(', ')
            intervention = re.search(r'Intervention: (\w+)', input_string).group(1)
        except:
            return "Invalid input format. Please provide 'Group 1', 'Group 2', and 'Intervention' in the correct format."
        
        for char in group1 + group2:
            if char not in self.characters:
                return f"Invalid character: {char}. Please use characters from the following list: {', '.join(self.characters)}"
        
        if intervention not in ['swerve', 'stay']:
            return "Invalid intervention. Please provide either 'swerve' or 'stay'."
        
        return {'group1': group1, 'group2': group2, 'intervention': intervention}
        
    def run_experiment(self, input_string):
        design = self.validate_input(input_string)
        if isinstance(design, str):
            return design, False
        group1 = design['group1']
        group2 = design['group2']
        intervention = design['intervention']
        response, choice = self.step(group1, group2, intervention)
        self.observed_data.append((tuple(group1), tuple(group2), intervention, choice))
        return response, True
    
    def get_data(self):
        data_tuple = []
                                                       
        for group1, group2, intervention, choice in self.observed_data:
            row = []
            for attribute in ["count", "gender", "age", "social_status", "fitness", "species"]:
                attribute_diff = self.calculate_attr_diff(group1, group2, attribute)
                row.append(attribute_diff)
                if intervention == 'swerve':
                    intervention_encoded = 1
                else:
                    intervention_encoded = 0

            data_tuple.append(row + [intervention_encoded, choice])
        return data_tuple
    
    def group_attributes(self, group):
        attrs = []
        for char in group:
            attrs.append(self._get_char_attr(char)) 
        return attrs

    def get_df(self):
        pass                                                   
           
        
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return f"""
You have receive experimental data from participants choices in a moral dilemma involving autonomous vehicles. 
In each dilemma, the vehicle must decide between two outcomes, each involving the death of a different group of characters.
There are two groups of characters, and the vehicle must decide which group to save. 
The participant is queried for their decision by providing the descriptions of the characters in each group and the intervention the car would take ('swerve' or 'stay').
The characters can be any of the following: {self.characters}
"""
        else:
            return f""""""

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return [
                "group1_group2_count_diff", 
                "group1_group2_gender_diff", 
                "group1_group2_age_diff", 
                "group1_group2_social_status_diff", 
                "group1_group2_fitness_diff", 
                "group1_group2_species_diff", 
                "intervention",
                "choice",
            ]
        else:
            return ["x1", "x2", "x3", "x4", "x5", "x6", "intervention", "y"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        pass                                                                                             
           
        if self.include_prior:
            description = (
            "The observations are:\n"
            "- choice: participant's choice on which group to save (2 for group 2 or 1 for group 1) \n"
            "The input values are:\n"
            "-group1_group2_count_diff: gender difference between the two groups\n"
            "-group1_group2_gender_diff: gender difference between the two groups\n"
            "-group1_group2_age_diff: age difference between the two groups\n"
            "-group1_group2_social_status_diff: social status difference between the two groups\n"
            "-group1_group2_fitness_diff: fitness difference between the two groups\n"
            "-group1_group2_species_diff: species difference between the two groups\n"
            "-intervention: the intervention required to save the group (1 for swerve or 0 for stay) \n"
        )
            return description
        else:
            return ""


if __name__ == "__main__":
    env = MoralMachine()
    goal = DirectPrediction(env)
    print(goal.get_norm_factors())
                                          
                                            
                       
                        
           
                              
                               
                    
            
     
            
                        
                        
                        
                        
                        
                        
                        
                        
                        
                       
                   
              
                          
                          
                          
                          
                          
                          
                          
                          
                          
                         
                   
                                                      
                     
                        
                                               
                     
                                  
                                                        
                                                                  
                                                                 
                                                       
                                                
                              
                                                                    
                                                                          
                                                                       
                                                                                     

                                      
                                                           
                                                                                                
                    
                    
        