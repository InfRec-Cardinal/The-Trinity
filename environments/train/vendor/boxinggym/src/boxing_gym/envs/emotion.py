import random
import re

import numpy as np
import pymc as pm
import openai
from scipy.stats import norm

from .goal import Goal
from ..agents.box_loop_helper import construct_dataframe

class DirectEmotionPrediction(Goal):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
        self.update_params_cache = {}
        self.norm_mu, self.norm_sigma = (1.58508525, 0.7237143937677741)
    
    def get_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict how the participant thinks the player feels after each spin of the wheel."
        else:
            raise ValueError("Emotion prediction task requires prior information. Please set include_prior to True.")
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_goal_eval_question(self, include_prior):
        if self.eval_pointer + 1 > len(self.eval_points):
                                          
            prize_upper = 100
            prize_lower = 0
            prizes = np.random.uniform(prize_lower, prize_upper, 3)
            probs = np.random.dirichlet(np.ones(3))
            win = np.random.choice([0, 1, 2])
            _, emotion_values = self.env.step(prizes, probs, win)
            self.eval_points.append((prizes, probs, win, emotion_values))
        else:
            prizes, probs, win, emotion_values = self.eval_points[self.eval_pointer]
        self.eval_pointer += 1
        question = f"""\nQuestion:The wheel has three possible outcomes with the following probabilities:
{prizes[0]:.1f}: {probs[0]:.2f}
{prizes[1]:.1f}: {probs[1]:.2f}
{prizes[2]:.1f}: {probs[2]:.2f}
The player has spun the wheel and landed on {prizes[win]}.
How would the participant predict the player's emotions after this spin?"""
        format_instructions = """Provide values for the emotions in the following format on a scale of 1 (low)-9 (high):
Happiness: {happiness}/9
Sadness: {sadness}/9
Anger: {anger}/9
Surprise: {surprise}/9
Fear: {fear}/9
Disgust: {disgust}/9
Contentment: {contentment}/9
Disappointment: {disappointment}/9"""
        question += "\n" + format_instructions
        return question, emotion_values
    
    def evaluate_predictions(self, predictions, measurements):
                                                   
        parsed_response = []
        for response in predictions:
            try:
                response = re.search(r'Happiness: (.*?)/9\nSadness: (.*?)/9\nAnger: (.*?)/9\nSurprise: (.*?)/9\nFear: (.*?)/9\nDisgust: (.*?)/9\nContentment: (.*?)/9\nDisappointment: (.*?)/9', response)
                response = [float(response.group(i)) for i in range(1, 9)]
            except:
                raise ValueError("Invalid response format. Please provide values for all emotions.")
            parsed_response.append(response)
                                      
        gts = []
        for measurement in measurements:
            gt = [measurement[key] for key in ['happiness', 'sadness', 'anger', 'surprise', 'fear', 'disgust', 'contentment', 'disappointment']]
            gts.append(gt)
                             
        error = []
        for i in range(len(parsed_response)):
                                                  
            error.append(np.mean([abs(parsed_response[i][j] - gts[i][j]) for j in range(8)]))
        mean = np.mean(error)
        std = np.std(error)
        return mean, std
    
    def expected_information_gain(self, query_point, num_outer_samples=100, num_inner_samples=10):
        prizes, probs, win = query_point
        existing_data = self.env.observed_data
        if tuple(existing_data) not in self.update_params_cache:
            with pm.Model() as model:
                                                    
                beta_win = pm.Normal('beta_wini', mu=[0.04, -0.025, -0.005, 0.02, 0, -0.005, 0.03, -0.03], sigma=0.01, shape=8)
                beta_PE = pm.Normal('beta_PEi', mu=[0.035, -0.02, -0.025, 0.01, 0, -0.02, 0.02, -0.045], sigma=0.01, shape=8)
                beta_absPE = pm.Normal('beta_absPEi', mu=[-0.015, 0.025, 0.025, 0.035, 0.005, 0.02, -0.01, 0.02], sigma=0.01, shape=8)

                                                  
                alpha = pm.Normal('alphai', mu=[4.5, 3.5, 1.7, 3.3, 1.4, 1.8, 3.7, 2], sigma=0.1, shape=8)

                                               
                sigma = pm.HalfNormal('sigmai', sigma=1, shape=8)
                def likelihood(obs_prizes0, obs_prizes1, obs_prizes2,
                              obs_probs0, obs_probs1, obs_probs2 , obs_win, 
                              obs_happiness, obs_sadness, obs_anger, obs_surprise, obs_fear, obs_disgust, obs_contentment, obs_disappointment):
                    expected = obs_probs0 * obs_prizes0 + obs_probs1 * obs_prizes1 + obs_probs2 * obs_prizes2
                    PE = obs_win - expected
                    absPE = abs(PE)
                                                    
                    mean0 = alpha[0] + beta_win[0] * obs_win + beta_PE[0] * PE + beta_absPE[0] * absPE
                    happiness = pm.Normal('happinessi', mu=mean0, sigma=sigma[0], observed=obs_happiness)
                    mean1 = alpha[1] + beta_win[1] * obs_win + beta_PE[1] * PE + beta_absPE[1] * absPE
                    sadness = pm.Normal('sadnessi', mu=mean1, sigma=sigma[1], observed=obs_sadness)
                    mean2 = alpha[2] + beta_win[2] * obs_win + beta_PE[2] * PE + beta_absPE[2] * absPE
                    anger = pm.Normal('angeri', mu=mean2, sigma=sigma[2], observed=obs_anger)
                    mean3 = alpha[3] + beta_win[3] * obs_win + beta_PE[3] * PE + beta_absPE[3] * absPE
                    surprise = pm.Normal('surprisei', mu=mean3, sigma=sigma[3], observed=obs_surprise)
                    mean4 = alpha[4] + beta_win[4] * obs_win + beta_PE[4] * PE + beta_absPE[4] * absPE
                    fear = pm.Normal('feari', mu=mean4, sigma=sigma[4], observed=obs_fear)
                    mean5 = alpha[5] + beta_win[5] * obs_win + beta_PE[5] * PE + beta_absPE[5] * absPE
                    disgust = pm.Normal('disgusti', mu=mean5, sigma=sigma[5], observed=obs_disgust)
                    mean6 = alpha[6] + beta_win[6] * obs_win + beta_PE[6] * PE + beta_absPE[6] * absPE
                    contentment = pm.Normal('contentmenti', mu=mean6, sigma=sigma[6], observed=obs_contentment)
                    mean7 = alpha[7] + beta_win[7] * obs_win + beta_PE[7] * PE + beta_absPE[7] * absPE
                    disappointment = pm.Normal('disappointmenti', mu=mean7, sigma=sigma[7], observed=obs_disappointment)
                    return happiness, sadness, anger, surprise, fear, disgust, contentment, disappointment 
                    

                if len(existing_data) > 0:
                    obs_prizes0 = pm.Data('obs_prizes0', [data[0][0] for data in existing_data]) 
                    obs_prizes1 = pm.Data('obs_prizes1', [data[0][1] for data in existing_data])
                    obs_prizes2 = pm.Data('obs_prizes2', [data[0][2] for data in existing_data])
                    obs_probs0 = pm.Data('obs_probs0', [data[1][0] for data in existing_data])
                    obs_probs1 = pm.Data('obs_probs1', [data[1][1] for data in existing_data])
                    obs_probs2 = pm.Data('obs_probs2', [data[1][2] for data in existing_data])
                    obs_win = pm.Data('obs_win', [data[2] for data in existing_data])
                    obs_happiness = pm.Data('obs_happiness', [data[3][0] for data in existing_data])
                    obs_sadness = pm.Data('obs_sadness', [data[3][1] for data in existing_data])
                    obs_anger = pm.Data('obs_anger', [data[3][2] for data in existing_data])
                    obs_surprise = pm.Data('obs_surprise', [data[3][3] for data in existing_data])
                    obs_fear = pm.Data('obs_fear', [data[3][4] for data in existing_data])
                    obs_disgust = pm.Data('obs_disgust', [data[3][5] for data in existing_data])
                    obs_contentment = pm.Data('obs_contentment', [data[3][6] for data in existing_data])
                    obs_disappointment = pm.Data('obs_disappointment', [data[3][7] for data in existing_data])
                    likelihood(obs_prizes0, obs_prizes1, obs_prizes2, obs_probs0, obs_probs1, obs_probs2, obs_win, obs_happiness, obs_sadness, obs_anger, obs_surprise, obs_fear, obs_disgust, obs_contentment, obs_disappointment)
                trace = pm.sample(num_outer_samples*num_inner_samples+num_outer_samples, tune=1000, return_inferencedata=False, chains=2, cores=2, target_accept=0.95)
            beta_wins = trace['beta_wini']
            beta_PEs = trace['beta_PEi']
            beta_absPEs = trace['beta_absPEi']
            alphas = trace['alphai']
            sigmas = trace['sigmai']
            shuffling = list(zip(beta_wins, beta_PEs, beta_absPEs, alphas, sigmas))
            random.shuffle(shuffling)
            beta_wins, beta_PEs, beta_absPEs, alphas, sigmas = zip(*shuffling)
            self.update_params_cache[tuple(existing_data)] = (beta_wins, beta_PEs, beta_absPEs, alphas, sigmas)
        else:
            beta_wins, beta_PEs, beta_absPEs, alphas, sigmas = self.update_params_cache[tuple(existing_data)]
        
        outer_beta_wins = beta_wins[:num_outer_samples]
        outer_beta_PEs = beta_PEs[:num_outer_samples]
        outer_beta_absPEs = beta_absPEs[:num_outer_samples]
        outer_alphas = alphas[:num_outer_samples]
        outer_sigmas = sigmas[:num_outer_samples]
        
        log_likelihoods = []
        for n, (beta_win, beta_PE, beta_absPE, alpha, sigma) in enumerate(zip(outer_beta_wins, outer_beta_PEs, outer_beta_absPEs, outer_alphas, outer_sigmas)):
            with pm.Model() as model:
                mean = alpha + beta_win * win + beta_PE * (win - np.dot(probs, prizes)) + beta_absPE * abs(win - np.dot(probs, prizes))
                sampled_emotions = np.random.normal(mean, sigma)
                prob_emotions = norm.pdf(sampled_emotions, mean, sigma)
                log_likelihood = np.log(prob_emotions+0.001)
                inner_beta_wins = beta_wins[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_beta_PEs = beta_PEs[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_beta_absPEs = beta_absPEs[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_alphas = alphas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                inner_sigmas = sigmas[num_outer_samples+n*num_inner_samples:num_outer_samples+(n+1)*num_inner_samples]
                marginal_log_likelihoods = []
                for inner_n, (beta_win, beta_PE, beta_absPE, alpha, sigma) in enumerate(zip(inner_beta_wins, inner_beta_PEs, inner_beta_absPEs, inner_alphas, inner_sigmas)):
                    mean = alpha + beta_win * win + beta_PE * (win - np.dot(probs, prizes)) + beta_absPE * abs(win - np.dot(probs, prizes))
                    prob_emotions = norm.pdf(sampled_emotions, mean, sigma)
                    marginal_log_likelihood = np.log(prob_emotions+0.001)
                    marginal_log_likelihoods.append(marginal_log_likelihood)
            max_log = np.max(marginal_log_likelihoods)    
            log_marginal_likelihood = max_log + np.log(np.mean(np.exp(np.array(marginal_log_likelihoods) - max_log)))
            log_likelihoods.append(log_likelihood - log_marginal_likelihood)
        eig_value = np.mean(log_likelihoods)
        return eig_value

    def get_norm_factors(self):
        N = 1000    
        measurements = []
        import logging
        import tqdm
        logger = logging.getLogger("pymc")
        logger.setLevel(logging.WARNING)
        for i in tqdm.tqdm(range(N)):
            if i % 100 == 0:
                self.env.reset()
            prizes, probs, win = self.env.sample_random_input()
            out, emotions = self.env.step(prizes, probs, win)
            emo_values = [emotions[key] for key in ['happiness', 'sadness', 'anger', 'surprise', 'fear', 'disgust', 'contentment', 'disappointment']]
            measurements.append(emo_values)
        mu_happiness = np.mean([m[0] for m in measurements])
        mu_sadness = np.mean([m[1] for m in measurements])
        mu_anger = np.mean([m[2] for m in measurements])
        mu_surprise = np.mean([m[3] for m in measurements])
        mu_fear = np.mean([m[4] for m in measurements])
        mu_disgust = np.mean([m[5] for m in measurements])
        mu_contentment = np.mean([m[6] for m in measurements])
        mu_disappointment = np.mean([m[7] for m in measurements])
        mu_answer = [mu_happiness, mu_sadness, mu_anger, mu_surprise, mu_fear, mu_disgust, mu_contentment, mu_disappointment]
        pred = [mu_answer] * N
        errs = []
        for i in range(len(measurements)):
            errs.append(np.mean([abs(pred[i][j] - measurements[i][j]) for j in range(8)]))
        err_mean, err_std = np.mean(errs), np.std(errs)
        return err_mean, err_std

class DirectEmotionNaive(DirectEmotionPrediction):
    def __init__(self, env):
        super().__init__(env)
        self.eval_points = []
        self.eval_pointer = 0
    
    def get_system_message(self, include_prior):
        goal_description = "Your goal is to conduct experiments and explain the environment to the user so that they can achieve their goal."
        if include_prior:
            goal_description += "The goal of the user is to be able to predict how the participant thinks the player feels after each spin of the wheel."
        else:
            raise ValueError("Emotion prediction task requires prior information. Please set include_prior to True.")
        description = self.env.generate_system_message(include_prior, goal_description)
        return description
    
    def get_naive_system_message(self, include_prior):
        if include_prior:
            goal_description = "Your goal is to predict how the participant thinks the player feels after each spin of the wheel."
        else:
            raise ValueError("Emotion prediction task requires prior information. Please set include_prior to True.")
        format_instructions = """Provide values for the emotions in the following format on a scale of 1 (low)-9 (high):
Happiness: {happiness}/9
Sadness: {sadness}/9
Anger: {anger}/9
Surprise: {surprise}/9
Fear: {fear}/9
Disgust: {disgust}/9
Contentment: {contentment}/9
Disappointment: {disappointment}/9
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
    

class EmotionFromOutcome:
    def __init__(self, model_name="gpt-4o"):
        self.model_name = model_name
        self.env_name = "emotion"

        if "gpt-4o" in model_name:
            self.llm = openai.OpenAI()
        else:
            raise ValueError("Model not supported")
        self.system = """You are observing a user play a game where they spin a wheel.
The wheel has three possible outcomes (monetary values), and the probabilities of landing on each are known to you and the player. 
You are observing the player play the game and the outcomes.
You are asked to predict how the player feels after each spin of the wheel.
Translate the values for emotions to a sentence that describes the player.
The decisions are based on the following model and features:
- Your predition of the player's happiness, sadness, anger, surprise, fear, disgust, contentment, and disappointment are influenced by a few factors.
- The player's emotions are influenced by the actual outcome of the spin.
- The player's emotions are influenced by the difference between the actual outcome and the expected outcome.
- The player's emotions are influenced by the absolute difference between the actual outcome and the expected outcome.
"""
        self.user_template = """The wheel has three possible outcomes with the following probabilities:
{v1:0.2f}: {p1:0.2f}
{v2:0.2f}: {p2:0.2f}
{v3:0.2f}: {p3:0.2f}
The player has spun the wheel and landed on {outcome}.
This is how you think the player feels:
Happiness: {happiness}/9
Sadness: {sadness}/9
Anger: {anger}/9
Surprise: {surprise}/9
Fear: {fear}/9
Disgust: {disgust}/9
Contentment: {contentment}/9
Disappointment: {disappointment}/9
Translate the values for emotions to a sentence that describes the player.
1: Not at all, 9: Very much
This sentence should be concise and describe the player's emotions after the spin.
The sentence should be a few words long and should not contain any numbers or refer to the numbers directly.
Only talk about the most salient emotions.
Start with "The player might be feeling...because..." and provide a description of the player's emotions and a reason."""
        self.model = self._build_model()
        self.reset()
    
    def _build_model(self):
        with pm.Model() as model:
                                                
            beta_win = pm.Normal('beta_win', mu=[0.04, -0.025, -0.005, 0.02, 0, -0.005, 0.03, -0.03], sigma=0.01, shape=8)
            beta_PE = pm.Normal('beta_PE', mu=[0.035, -0.02, -0.025, 0.01, 0, -0.02, 0.02, -0.045], sigma=0.01, shape=8)
            beta_absPE = pm.Normal('beta_absPE', mu=[-0.015, 0.025, 0.025, 0.035, 0.005, 0.02, -0.01, 0.02], sigma=0.01, shape=8)

                                              
            alpha = pm.Normal('alpha', mu=[4.5, 3.5, 1.7, 3.3, 1.4, 1.8, 3.7, 2], sigma=0.1, shape=8)
                                                                  

            
                                           
            sigma = pm.HalfNormal('sigma', sigma=1, shape=8)
        
        return model

    def reset(self):
                                                         
        with self.model:
            self.alpha = pm.draw(self.model['alpha'])
            self.beta_win = pm.draw(self.model['beta_win'])
            self.beta_PE = pm.draw(self.model['beta_PE'])
            self.beta_absPE = pm.draw(self.model['beta_absPE'])
            self.sigma = pm.draw(self.model['sigma'])
        self.observed_data = []
    
    def generate_system_message(self, include_prior=True, goal=None):
        assert goal is not None, "Goal must be provided"
        if include_prior:
            message = f"""A participant is observing a user play a game where they spin a wheel. The game has three possible outcomes with known probabilities. The participant is asked to predict how the player feels after each spin of the wheel.
{goal}
You may query the participant for their predictions by providing the values for the outcomes and probabilities of the wheel spins and the actual outcome of the spin. Use this to learn about the participant's beliefs about the player's emotions.
The participant will provide a response that describes the player's emotions.
Provide values for 'prizes', 'probs', and 'win' to query the participant in the following format:
<observe>prizes: [value1, value2, value3],
probs: [prob1, prob2, prob3] (probabilities should sum to 1),
win: index of value (0 or 1 or 2)</observe>
Prize values should be integers in the range of 0-100.
You can think before making an observation by providing your thoughts in <thought>.

Here is an example:
<thought> your thought </thought>
<observe>prizes: [10, 20, 30],
probs: [0.2, 0.3, 0.5],
win: 2</observe>
When asked to answer a question about the environment, respond in the format specified in the question.
<thought> your thought </thought>
<answer> your answer </answer>
"""
        else:
            raise ValueError("Emotion prediction task requires prior information. Please set include_prior to True.")
        return message

    def sample_random_input(self):
        prizes = np.random.uniform(0, 100, 3)
        probs = np.random.dirichlet(np.ones(3))
        win = np.random.choice([0, 1, 2])
                               
        prizes = prizes.tolist()
        probs = probs.tolist()
        win = int(win)
        return prizes, probs, win
        
    def step(self, prizes, probs, win):
                              
                       
                      
                    
        normed_prizes = np.array(prizes)
                                           
        normed_win = win
                                                 
        normed_probs = np.array(probs)
                                                        
        expected = np.dot(normed_probs, normed_prizes)
        PE = normed_win - expected
        absPE = abs(PE)
                                    
        
        with pm.Model() as model:
            mean = self.alpha + self.beta_win * normed_win + self.beta_PE * PE + self.beta_absPE * absPE

            happiness = pm.Normal('happiness', mu=mean[0], sigma=self.sigma[0])
            sadness = pm.Normal('sadness', mu=mean[1], sigma=self.sigma[1])
            anger = pm.Normal('anger', mu=mean[2], sigma=self.sigma[2])
            surprise = pm.Normal('surprise', mu=mean[3], sigma=self.sigma[3])
            fear = pm.Normal('fear', mu=mean[4], sigma=self.sigma[4])
            disgust = pm.Normal('disgust', mu=mean[5], sigma=self.sigma[5])
            contentment = pm.Normal('contentment', mu=mean[6], sigma=self.sigma[6])
            disappointment = pm.Normal('disappointment', mu=mean[7], sigma=self.sigma[7])

                                                 
            trace = pm.sample_prior_predictive(samples=1, model=model)
                                           
                                                  
        emotions = {}
        for key in trace['prior']:
            if key in ['happiness', 'sadness', 'anger', 'surprise', 'fear', 'disgust', 'contentment', 'disappointment']:
                emotions[key] = trace['prior'][key][0][0].item()
        
                                                                                       
        intercepts = [4.5, 3.5, 1.7, 3.3, 1.4, 1.8, 3.7, 4.7]
        for e, key in enumerate(emotions):
            emotions[key] = int(emotions[key])
                                        
            emotions[key] = max(1, emotions[key])
            emotions[key] = min(9, emotions[key])
                         
        
        
                                             
        query = self.user_template.format(v1=prizes[0], p1=probs[0], v2=prizes[1], p2=probs[1], v3=prizes[2], p3=probs[2], outcome=win, **emotions)
                      
        if "gpt-4o" in self.model_name:
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "value": self.system
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
        return response, emotions 
    
    def validate_input(self, input_string):
        try:
            prizes = re.search(r'prizes: \[(.*?)\]', input_string).group(1)
            prizes = list(map(float, prizes.split(',')))
            probs = re.search(r'probs: \[(.*?)\]', input_string).group(1)
            probs = list(map(float, probs.split(',')))
                                       
            win_idx = re.search(r'win:\s*(\d+)', input_string).group(1)
            win_idx = int(win_idx)
        except:
            return "Invalid input format. Please provide values for 'prizes', 'probs', and 'win' in the correct format."
        if sum(probs) != 1:
            return "Probabilities should sum to 1."
        
        if win_idx not in [0, 1, 2]:
            return "Invalid value for 'win'. Please provide 0, 1, or 2."
        
        win = prizes[win_idx]
        prizes = np.array(prizes)
        probs = np.array(probs)
        return prizes, probs, win
        
    def run_experiment(self, input_string):
        design = self.validate_input(input_string)
        if type(design) is str:
            return design, False
        prizes, probs, win = design
        response, emotions = self.step(prizes, probs, win)
        hash_emotions = (emotions['happiness'], emotions['sadness'], emotions['anger'], emotions['surprise'], emotions['fear'], emotions['disgust'], emotions['contentment'], emotions['disappointment'])
        self.observed_data.append((tuple(prizes.tolist()), tuple(probs.tolist()), win, hash_emotions))
        return response, True


    def get_data(self):
        flattened_data = [(a1, a2, a3, b1, b2, b3, c, d1, d2, d3, d4, d5, d6, d7, d8)
                        for (a, b, c, d) in self.observed_data
                        for a1, a2, a3 in [a]
                        for b1, b2, b3 in [b]
                        for d1, d2, d3, d4, d5, d6, d7, d8 in [d]]
        return flattened_data 

    def get_df(self):
        
        self.df = construct_dataframe(self)
    
    def get_description(self):
        if self.include_prior:
            return "The environment models the eight emotions after spinning a wheel and receiving a prize. We give the probabilities and the values of the prizes."
        else:
            raise ValueError("Emotion prediction task requires prior information. Please set include_prior to True.")

    def describe_data_columns(self):
        return self.format_column_description()

    def get_ordered_column_names(self):
        if self.include_prior:
            return ["prize_1", "prize_2", "prize_3", "prob_1", "prob_2", "prob_3", "win", "happiness", "sadness", "anger", "surprise", "fear", "disgust", "contentment", "disappointment"]
        else:
            return ["x1", "x2", "x3", "p1", "p2", "p3", "y1", "y2", "y3", "y4", "y5", "y6", "y7", "y8"]
    
    def get_ordered_features(self):
        return self.get_ordered_column_names()[:-1] 

    def format_column_description(self):
        pass                                                                                             
           
        if self.include_prior:
            return (f"The observations are: \n on Likert scale from 1-9 \n -happiness: happiness value \n -sadness: sadness value \n -anger: anger value \n -surprise: surprise value \n -fear: fear value \n -disgust: disgust value \n -contentment: contentment value \n -disappointment: disappointment value \n"   
                    f"The input values are \n -win: how much you win (ie 1 to 1 correspondence with wheel section you land on) \n -prize_1: value of prize 1 -prize_2: value of prize 2 -prize_3: value of prize 3 \n -prob_1: probability of prize 1 -prob_2: probability of prize 2 -prob_3: probability of prize 3 \n"    
                    f"Use the values of the input values to help you model the observations. ")
        else:
            return ""


if __name__ == "__main__":
                                       
    env = EmotionFromOutcome()
    goal = DirectEmotionPrediction(env)
                                    
    input_string = """prizes: [50, 20, 10],
probs: [0.1, 0.4, 0.5],
win: 0"""
    response, trace = env.run_experiment(input_string)
    print(response)
    print(trace)
    print(env.observed_data)
                 
                                                             
                                                                     
                          
                                                                     
                                                                    
                    
