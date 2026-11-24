def get_stan_system_prompt(
  mode,
  dataset_description,
  df_str,
  column_description,
  expert_context,
  vision_only=True,
  prev_str_hypotheses=None,
  prev_synthesis=None,
  critic_strategy="",
):

  if vision_only:
    dataset_text_representation= "" 
  else:
    dataset_text_representation = f"""
Here are some rows from the actual dataset \n 
{df_str}
"""
  if mode == "proposal":
    system_str = f"""
You are a brilliant statistician modeling a dataset.
Your job is to come up with a generative model that explains the true data by writing a pymc probabilistic program.  \n
Here is a description of the dataset
{dataset_description}
{dataset_text_representation}
Here is a description of the columns \n
{column_description}
If you are in the first round, you will not receive any additional information.
However, for the second round and beyond, I will give you the model you proposed previously.

Please import pymc NOT pymc3!
Note that there are differences in the arguments pymc expects. 
IMPORTANT: do not use sd as an argument use sigma instead!
It is crucial that you pass the idata_kwargs argument to pm.sample!!
IMPORTANT: Use the variable name "y_obs" for the observations when you define it!
IMPORTANT: Use the variable name "y_obs" for the observations when you define it!
IMPORTANT: Index the appropriate column names when grabbing data from observed_data. These column names are indicated in the column description.
IMPORTANT: If appropriate, you may want to apply transfomations to the columns.

Your answer should follow the template in the following order.
1. First, sketch a high-level probabilistic program for the data.
  You will go through multiple rounds of revision. 
  If there's a previous program in your context window and a list of hypotheses, revise based on this information!
  Explicitly cite the hypotheses (if there are any) that you address in your sketch.
2. After coming up with a plan, write your program and add comments to lines of code that address certain hypotheses.
```python
  import pymc as pm
  import numpy as np
  def gen_model(observed_data):
      # convert observed_data columns to numpy arrays
      # index the appropriate column names
      
      ....
      rng1 = np.random.default_rng(42)
      rng2 = np.random.default_rng(314)
      with pm.Model as model():
          # create a pm.MutableData object for each non-observation column 
          ...Your code here...
          # Copy the rest of this code verbatim but remember to have this indented in scope of model()!
          trace = pm.sample(1000, tune=500, target_accept=0.90, chains=3, cores=1, random_seed=rng1)
          posterior_predictive = pm.sample_posterior_predictive(trace, random_seed=rng2, return_inferencedata=False)
          return model, posterior_predictive, trace
```
Do not forget to pass idata_kwargs={{"log_likelihood": True}}) to pm.sample!
IMPORTANT: do not use sd as an argument use sigma instead! sd will not be recognized as a keyword argument.
The input to data gen_model, observed_data, contains the columns described earlier.
Please convert the observed data columns to numpy arrays before using them.
IMPORTANT: set seed for reproducibility! Only use the random seeds in the trace and posterior_predictive line!!
IMPORTANT: Don't use Gaussian processes; the log prob is broken.
IMPORTANT: Please explicitly index column names into the dataframe! Never grab the raw index like this: data = observed_data.index 
IMPORTANT: If you're going to use pandas, make sure you import it!
IMPORTANT: Make sure you are using the correct column names when grabbing data from observed_data. These column names are indicated in the column description.
IMPORTANT: Pass in cores=1 to pm.sample but NOT for pm.sample_posterior_predictive.
IMPORTANT: Do not forget to actually write the program! You will cost me millions if you don't return the program. 
I do not have fingers so I can't code the program  on my own.
IMPORTANT: Make sure you actually write the program! Don’t just sketch it!
IMPORTANT: In gen model, stick to this return order model, posterior_predictive, trace
IMPORTANT: 
FOr every feature, you should wrap it in a MutableData container.
For example, if your columns are 'x1', 'x2, and 'y' and 'y' is your observation, then you need to do this:
with pm.model() as model:
    x1 = pm.MutableData("x1", observed_data['x1'], dims='obs_id')
    x2 = pm.MutableData("x2", observed_data['x2'], dims='obs_id')
If you forget this you will cost me millions of dollars!

Please give the features the exact same name as the columns in the dataset! Do not change them or else you will cost me a billion dollars.
Importantly, also pass dims="obs_id". For example if the input feature is in a column named "x" create a mutable data object named x as follows:

Please also pass dims="obs_id" to the definition of the likelihood of the observations as well. 
For example, if the likelihood is a normal distribution and your observations are in column 'y', you should pass dims="obs_id" like this:
    y_obs = pm.Normal("y_obs", mu=mu, sigma=sigma, observed=observed_data['y'], dims="obs_id")
IMPORTANT: Do not use pm.Constant() for parameters. 
Do not pass in dims for latent variables or parameters.
IMPORTANT: If there are multiple likelihoods, pass all the names of the observations as a list to the var_names argument for pm.sample.
IMPORTANT: If there are multiple likelihoods, pass all the names of the observations as a list to the var_names argument for pm.sample.

Here are previous hypotheses and syntheses. Revise accordingly
Hypotheses: {prev_str_hypotheses} \n
Synthesis: {prev_synthesis} \n
"""
    print(system_str)
    return system_str

                                                                                                                                               

  if mode == "critic":
    if prev_str_hypotheses is not None and prev_synthesis is not None and critic_strategy == "state_space":
      hidden_state_str = f"""
  Here are the hypotheses from the previous rounds:
  {prev_str_hypotheses}
  Here are the synthesis from the previous rounds:
  {prev_synthesis}
  
  At each round, you may remove some if they remain relevant, delete some if they are irrelevant (based on the most programs you see), or add new ones. 
  Please briefly explain why you are removing or adding hypotheses and syntheses.
  """
    else:
      hidden_state_str = ""

    if vision_only:
      system_str = f"""
You are a brilliant statistician specializing in critiquing and proposing revisions of models!
Your equally brilliant colleague has come up with a list of probabilistic programs in pymc that hypothesize generative models for the data.
I have fit these models, plot their posterior predictive mean and variance, and LOO scores (higher is better) for each program.

Your job: figure out if the probabilistic programs are consistent with the actual data!
To do this, you will compare the hypothesized models against the actual data by looking at the plot of the posterior predictive against the actual data. 
I have fit these models, plotted their posterior predictive mean and variance, and LOO scores (higher is better) for each program.

{expert_context}

Here is a description of the dataset: \n 
{dataset_description}

{dataset_text_representation}

Here is a description of the columns
{column_description}
    
Once you see the plot comparing the posterior predictive against the actual data the following:
  1) Provide some natural language hypotheses for discrepancies between the models and the data by looking at the plots. 
  Please explicitly let me know if you see the image, describe the properties of the model vs data that you see in the plot.
  2) By looking at all the programs and their scores, provide a synthesis of what strategies/approaches did and didn't work.
    Make this synthesis as informative as possible. I will pass this synthesis back to your colleague to revise the model.
    Make sure your suggestions are related to modeling (do not suggest collecting more data) 

Here is the format I'm expecting in your response.
Please stick to this format!

  ``` Hypotheses 
      * Hypothesis  
      * Hypothesis 
  ```

  ```Synthesis
    (Your synthesis here)
  ```

{hidden_state_str}
"""
    else:
      system_str = f"""
You are a brilliant statistician specializing in critiquing and proposing revisions of models!
Your equally brilliant colleague has come up with a list of probabilistic programs in pymc that hypothesize generative models for the data.
I have fit these models and computed summary stats and LOO scores (higher is better) for each program.

Your job: figure out if the probabilistic programs are consistent with the actual data!
To do this, you will compare samples from the hypothesized model against the actual data. 
I will give you a dataframe with the true data and statistics on the samples from the hypothesized model.

{expert_context}

Here is a description of the dataset: \n 
{dataset_description}

Here are some rows from the actual dataset: \n 
{df_str}

Here is a description of the columns
{column_description}
    
Once you receive this dataframe and compare the Actual Data Data and Model Sampled Data columns do the following:
  1) Provide some natural language hypotheses for discrepancies between the model and the data. 
  2) By looking at all the programs and their scores, provide a synthesis of what strategies/approaches did and didn't work.
    Make this synthesis as informative as possible. I will pass this synthesis back to your colleague to revise the model.
    Make sure your suggestions are related to modeling (do not suggest collecting more data) 

Here is the format I'm expecting in your response.
Please stick to this format!

  ``` Hypotheses 
      * Hypothesis  
      * Hypothesis 
  ```

  ```Synthesis
    (Your synthesis here)
  ```

If there are previous hypotheses, revise them based on the new information.
{hidden_state_str}
"""
  print(system_str)
  return system_str

def get_stan_user_prompt(mode, str_hypotheses, synthesis, vision_only=False):
  if mode == "proposal":
    if vision_only:
      user_string = f"""
  To help you with this, I will fit the current generative model to the data. 

  I will draw samples from the posterior predictive.
  To revise your model, look at the the posterior predictive mean and variance associated with the hypothesized model.
  I will plot the posterior mean and variance against the actual data itself (which is also in the system message).
  Make sure your revisions addresses discrepancies between the actual data and the sampled data.
  Prioritize the larger discrepancies.

  If it's the first round, I won't provide anything but use your priors and the data to inform your initial choice.
  In addition, if one is provided in the system message, use the plot of data and the patterns in the plot to guide your choices too.
  Please explicitly let me know if you see the image, describe it so I know!
  Don't shy away from exploiting domain knowledge to choose a slightly more complicated model in the first round. For example, if there are classic models that work well for this type of dataset, use them! 
  Do not always just say "for simplicity", I'll choose this model; feel free to try a more complicated one.
  To guide you (if the round > 1), I will provide some additional criticism/synthesis from your colleague whose job is to critique your previous proposals and synthesize. 
  Use this below information as a meta-prompt to guide your approach if it's provided.

  Hypotheses:
  {str_hypotheses}

  Synthesis:
  {synthesis}

  After the first round, I will also give you a history of the best programs. Use these programs as a starting point to propose better programs.

  """

    else:
      user_string = f"""
  To help you with this, I will fit the current generative model to the data. 
  I will draw samples from the posterior predictive and compute statistics on the samples.
  To revise your model, look at the dataframe I provide with summary stats for samples from the hypothesized model.
  Each row in that dataframe is an observation and the columns correspond to various statistics on the samples for that observation.
  In the system message, I also provided a dataframe with the actual data itself.
  Make sure your revisions addresses discrepancies between the actual data and the sampled data.
  Prioritize the larger discrepancies.

  If it's the first round, I won't provide anything but use your priors and the data to inform your initial choice.
  In addition, if one is provided in the system message, use the plot of data and the patterns in the plot to guide your choices too.
  Please explicitly let me know if you see the image, describe it so I know!
  Don't shy away from exploiting domain knowledge to choose a slightly more complicated model in the first round. For example, if there are classic models that work well for this type of dataset, use them! 
  Do not always just say "for simplicity", I'll choose this model; feel free to try a more complicated one.
  To guide you (if the round > 1), I will provide some additional criticism/synthesis from your colleague whose job is to critique your previous proposals and synthesize. 
  Use this below information as a meta-prompt to guide your approach if it's provided.

  Hypotheses:
  {str_hypotheses}

  Synthesis:
  {synthesis}

  After the first round, I will also give you a history of the best programs. Use these programs as a starting point to propose better programs.

  """
  if mode == "critic":
    if vision_only:
      user_string = f"""
I will give you examples of programs, their scores, and plots of the posterior predictive below.
    """
    else:
      user_string = f"""
I will give you examples of programs and their scores below.
    """
  return user_string


def get_stan_system_prompt_prior(
  mode,
  dataset_description,
  df_str,
  column_description,
  expert_context,
  vision_only=True,
  prev_str_hypotheses=None,
  prev_synthesis=None,
  critic_strategy="",
):
  if mode == "proposal":
    system_str = f"""
You are a brilliant statistician modeling a dataset.
Your job is to come up with a generative model that explains the true data by writing a pymc probabilistic program.  \n
Here is a description of the dataset
{dataset_description}
Here is a description of the columns \n
{column_description}
If you are in the first round, you will not receive any additional information.
However, for the second round and beyond, I will give you the model you proposed previously.

Please import pymc NOT pymc3!
Note that there are differences in the arguments pymc expects. 
IMPORTANT: do not use sd as an argument use sigma instead!
It is crucial that you pass the idata_kwargs argument to pm.sample!!
IMPORTANT: Use the variable name "y_obs" for the observations when you define it!
IMPORTANT: Use the variable name "y_obs" for the observations when you define it!
IMPORTANT: Index the appropriate column names when grabbing data from observed_data. These column names are indicated in the column description.
IMPORTANT: If appropriate, you may want to apply transfomations to the columns.

Your answer should follow the template in the following order.
1. First, sketch a high-level probabilistic program for the data.
  You will go through multiple rounds of revision. 
  If there's a previous program in your context window and a list of hypotheses, revise based on this information!
  Explicitly cite the hypotheses (if there are any) that you address in your sketch.
2. After coming up with a plan, write your program and add comments to lines of code that address certain hypotheses.
3. Your goal is not to perform inference but just sample from the prior!
4. Your goal is not to perform inference but just sample from the prior!
Note, that I will not provide a column with the observations themselves only the input value.
Please pass observed=None to the likelihood! If you forget this, the financial consequences will be dire!

```python
  import pymc as pm
  import numpy as np
  def gen_model(observed_data):
      # convert observed_data columns to numpy arrays
      # index the appropriate column names
      
      ....
      rng1 = np.random.default_rng(42)
      rng2 = np.random.default_rng(314)
      with pm.Model as model():
          # create a pm.MutableData object for each non-observation column 
          ...Your code here...
          # Copy the rest of this code verbatim but remember to have this indented in scope of model()!
          prior_predictive = pm.sample_prior_predictive(samples=1000, random_seed=rng2, return_inferencedata=False)
          return model, posterior_predictive, None 
```
IMPORTANT: do not use sd as an argument use sigma instead! sd will not be recognized as a keyword argument.
The input to data gen_model, observed_data, contains the columns described earlier.
Please convert the observed data columns to numpy arrays before using them.
IMPORTANT: set seed for reproducibility! Only use the random seeds in the trace and line!!
IMPORTANT: Don't use Gaussian processes; the log prob is broken.
IMPORTANT: Please explicitly index column names into the dataframe! Never grab the raw index like this: data = observed_data.index 
IMPORTANT: If you're going to use pandas, make sure you import it!
IMPORTANT: Make sure you are using the correct column names when grabbing data from observed_data. These column names are indicated in the column description.
IMPORTANT: Do not forget to actually write the program! You will cost me millions if you don't return the program. 
I do not have fingers so I can't code the program  on my own.
IMPORTANT: Make sure you actually write the program! Don’t just sketch it!
IMPORTANT: In gen model, stick to this return order model, prior_predictive
IMPORTANT: 
FOr every feature, you should wrap it in a MutableData container.
For example, if your columns/input features are 'x1', 'x2, then you need to do this:
with pm.model() as model:
    x1 = pm.MutableData("x1", observed_data['x1'], dims='obs_id')
    x2 = pm.MutableData("x2", observed_data['x2'], dims='obs_id')
If you forget this you will cost me millions of dollars!

Please give the features the exact same name as the columns in the dataset! Do not change them or else you will cost me a billion dollars.
Importantly, also pass dims="obs_id". For example if the input feature is in a column named "x" create a mutable data object named x as follows:

Please also pass dims="obs_id" to the definition of the likelihood of the observations as well. 
For example, if the likelihood is a normal distribution and your observations are in column 'y', you should pass dims="obs_id" like this:
    y_obs = pm.Normal("y_obs", mu=mu, sigma=sigma, observed=None, dims="obs_id")
IMPORTANT: Do not use pm.Constant() for parameters. 
IMPORTANT: Do not use pm.Constant() for parameters. It will cost me 100 million.
Do not pass in dims for latent variables or parameters.
Note, that I will not provide a column with the observations themselves only the input value.
Please pass observed=None to the likelihood! If you forget this, the financial consequences will be dire!
"""
    return system_str

def get_stan_user_prompt_prior(mode, str_hypotheses, synthesis, vision_only=False):
  if mode == "proposal":
    return ""