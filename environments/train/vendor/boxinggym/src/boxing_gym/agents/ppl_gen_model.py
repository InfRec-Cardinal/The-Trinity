import numpy as np
import pymc as pm
import pandas as pd

def gen_model(observed_data):
                                                   
    win = observed_data['win'].values
    prize_1 = observed_data['prize_1'].values
    prize_2 = observed_data['prize_2'].values
    prize_3 = observed_data['prize_3'].values
    prob_1 = observed_data['prob_1'].values
    prob_2 = observed_data['prob_2'].values
    prob_3 = observed_data['prob_3'].values
    
                  
    happiness = observed_data['happiness'].values
    sadness = observed_data['sadness'].values
    anger = observed_data['anger'].values
    surprise = observed_data['surprise'].values
    fear = observed_data['fear'].values
    disgust = observed_data['disgust'].values
    contentment = observed_data['contentment'].values
    disappointment = observed_data['disappointment'].values

    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(314)
    
    with pm.Model() as model:
                                                                       
        win_data = pm.MutableData("win", win, dims="obs_id")
        prize_1_data = pm.MutableData("prize_1", prize_1, dims="obs_id")
        prize_2_data = pm.MutableData("prize_2", prize_2, dims="obs_id")
        prize_3_data = pm.MutableData("prize_3", prize_3, dims="obs_id")
        prob_1_data = pm.MutableData("prob_1", prob_1, dims="obs_id")
        prob_2_data = pm.MutableData("prob_2", prob_2, dims="obs_id")
        prob_3_data = pm.MutableData("prob_3", prob_3, dims="obs_id")
        
                                            
        beta_win = pm.Normal("beta_win", mu=0, sigma=1)
        beta_prize_1 = pm.Normal("beta_prize_1", mu=0, sigma=1)
        beta_prize_2 = pm.Normal("beta_prize_2", mu=0, sigma=1)
        beta_prize_3 = pm.Normal("beta_prize_3", mu=0, sigma=1)
        beta_prob_1 = pm.Normal("beta_prob_1", mu=0, sigma=1)
        beta_prob_2 = pm.Normal("beta_prob_2", mu=0, sigma=1)
        beta_prob_3 = pm.Normal("beta_prob_3", mu=0, sigma=1)
        
                                          
        mu_happiness = (beta_win * win_data + beta_prize_1 * prize_1_data + 
                        beta_prize_2 * prize_2_data + beta_prize_3 * prize_3_data + 
                        beta_prob_1 * prob_1_data + beta_prob_2 * prob_2_data + 
                        beta_prob_3 * prob_3_data)
        
                                                
        y_obs_happiness = pm.Normal("happiness", mu=mu_happiness, sigma=1, observed=happiness, dims="obs_id")
        y_obs_sadness = pm.Normal("sadness", mu=mu_happiness, sigma=1, observed=sadness, dims="obs_id")
        y_obs_anger = pm.Normal("anger", mu=mu_happiness, sigma=1, observed=anger, dims="obs_id")
        y_obs_surprise = pm.Normal("surprise", mu=mu_happiness, sigma=1, observed=surprise, dims="obs_id")
        y_obs_fear = pm.Normal("fear", mu=mu_happiness, sigma=1, observed=fear, dims="obs_id")
        y_obs_disgust = pm.Normal("disgust", mu=mu_happiness, sigma=1, observed=disgust, dims="obs_id")
        y_obs_contentment = pm.Normal("contentment", mu=mu_happiness, sigma=1, observed=contentment, dims="obs_id")
        y_obs_disappointment = pm.Normal("disappointment", mu=mu_happiness, sigma=1, observed=disappointment, dims="obs_id")
        
                                   
        trace = pm.sample(1000, tune=500, target_accept=0.90, chains=3, cores=1, random_seed=rng1, idata_kwargs={"log_likelihood": True})
        
                                              
        posterior_predictive = pm.sample_posterior_predictive(trace, random_seed=rng2, return_inferencedata=False)
        
        return model, posterior_predictive, trace