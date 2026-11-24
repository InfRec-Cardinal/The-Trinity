import traceback
from io import StringIO
import pandas as pd
import importlib

import numpy as np
import pymc as pm

from box_loop_prompts import get_stan_system_prompt, get_stan_user_prompt
from box_loop_prompts import get_stan_system_prompt_prior, get_stan_user_prompt_prior
from box_loop_helper import pymc_evaluate
import threading
import signal

class BoxLoop_Experiment():
  def __init__(self, 
  dataset, 
  corrupt, 
  logger, 
  log_dir, 
  language_synthesize,
  prior_mode=False,
  ) -> None:

    pass                       
       

    self.corrupt = corrupt
    self.dataset = dataset
    self.prior_mode = prior_mode

    if not prior_mode:
      self.observed_data = self.dataset.df

    self.stats_fn_list = ["mean", "std", "median"]
    self.language_synthesize = language_synthesize
    self.checkpoint_dir = "/tmp/oed_llms/stan/"
    self.logger = logger
    self.log_dir = log_dir
    
  def get_posterior_predictive(self, str_prob_prog, observed_data):
    pass                                                                                       
       
    print("entering get_posterior_predictive")


    gen_model = self.get_gen_model(str_prob_prog)
    result = [None, None, None]
    def worker():
      try:
        model, posterior_predictive, trace = gen_model(observed_data)
        result[:] = [model, posterior_predictive, trace]
      except TimeoutError:
        print("PYMC program timed out")
        self.logger.info("PYMC program timed out")
      except Exception as e:
        self.logger.info(f"failed program: {str_prob_prog}")
        with StringIO() as buf:
            traceback.print_exc(file=buf)
            tb_str = buf.getvalue()
        self.logger.info(f"traceback: {tb_str}")
      
    def timeout_handler(signum, frame):
      raise TimeoutError

    signal.signal(signal.SIGALRM, timeout_handler)
    TIMEOUT_TIME = 60 * 8 
    signal.alarm(TIMEOUT_TIME)               

                             
    thread = threading.Thread(target=worker)
    thread.start()

                                                                
    thread.join()
    signal.alarm(0)                     

    print("WE MADE IT HERE")
    return result[0], result[1], result[2]

  def get_gen_model(self, gen_code):
    with open("ppl_gen_model.py", 'w') as file:
      file.write(gen_code)

    importlib.invalidate_caches()
    import src.boxing_gym.agents.ppl_gen_model as ppl_gen_model
    importlib.reload(ppl_gen_model)
    from src.boxing_gym.agents.ppl_gen_model import gen_model
    return gen_model

  def get_prior_samples(self, str_prob_prog):

    try:
      model, posterior_predictive, trace = self.get_posterior_predictive(
          str_prob_prog=str_prob_prog, 
          observed_data=None)
      return "", "", "", model, posterior_predictive, trace
    except Exception as e:
      print("from get_ppcs error")
      with StringIO() as buf:
          traceback.print_exc(file=buf)
          tb_str = buf.getvalue()
      return None 
        
  def score_programs(self, program, logger, llm_response):

    try:
      ppc_results = self.get_ppcs(
                        str_prob_prog=program, 
                        observed_data=self.observed_data, 
                        stats_fn_list=self.stats_fn_list, 
                        logger=logger)
      (
        df_posterior_stats, 
        ppc_stats_str, 
        raw_stats_str,
        model, 
        posterior_predictive, 
        trace
      ) = ppc_results

      summary_stats_str = ppc_stats_str 

      res = pymc_evaluate(trace)

      logger.info(f"Program {res['loo']}: \n {program}")
      return {
        "loo": res['loo'],
        "waic": res['waic'],
        "summary_stats": summary_stats_str,
                                                       
        "summary_stats_df": df_posterior_stats,
        "str_prob_prog": program,
        "trace": trace,
        "model": model,
        "full_llm_response": llm_response
      }

    except Exception as e:
      print(f"score program error: {e}")
      with StringIO() as buf:
          traceback.print_exc(file=buf)
          tb_str = buf.getvalue()

  def get_ppcs(self, str_prob_prog, observed_data, stats_fn_list, logger):

    try:
      model, posterior_predictive, trace = self.get_posterior_predictive(
          str_prob_prog=str_prob_prog, 
          observed_data=observed_data)

    
      assert len(posterior_predictive) == 1
      obs_key = list(posterior_predictive.keys())[0]
      key = obs_key

      assert posterior_predictive[key].ndim == 3
      assert posterior_predictive[key].shape[-1] == observed_data.shape[0]

      posterior_predictive_y_obs = posterior_predictive[key].reshape(
          posterior_predictive[key].shape[0] * posterior_predictive[key].shape[1], 
          posterior_predictive[key].shape[-1]
      )


      def get_observation_index(i):
        return observed_data.index[i].split("True Observation")[-1]

                                                           
      def round_to_n_significant(x, n=2):
          if not np.isfinite(x) or x == 0:
              return x
          else:
              return round(x, -int(np.floor(np.log10(abs(x)))) + (n - 1))

      df_posterior_data = pd.DataFrame(posterior_predictive_y_obs, 
                                      columns = [
                                                f"Model Sampled Observation {get_observation_index(i)}" 
                                                for i in range(0, posterior_predictive_y_obs.shape[1])
                                                ])

      df_posterior_stats = df_posterior_data.agg(stats_fn_list).T
      df_true_stats = observed_data

      df_posterior_stats_round = df_posterior_stats.map(lambda x: round_to_n_significant(x) if np.issubdtype(type(x), np.number) else x)
      df_true_stats_round = df_true_stats.map(lambda x: round_to_n_significant(x) if np.issubdtype(type(x), np.number) else x)

      ppc_stats_str = df_posterior_stats_round.to_string()
      raw_stats_str = df_true_stats_round.to_string()

                                                             
      return df_posterior_stats, ppc_stats_str, raw_stats_str, model, posterior_predictive, trace

    except Exception as e:
      print("from get_ppcs error")
      with StringIO() as buf:
          traceback.print_exc(file=buf)
          tb_str = buf.getvalue()
      return None 

  def filter_fn(self, results):
                                     
    return results 

  def sort_fn(self, results):
    if self.prior_mode:
      return results 

    results = sorted(results, key = lambda x: -x['loo'])
    return results

  def get_user_message(self, mode, str_hypotheses, synthesis, vision_only=False):
    assert mode in ["proposal", "critic"]

    if self.prior_mode:
      return get_stan_user_prompt_prior(
        mode=mode, 
        str_hypotheses=str_hypotheses, 
        vision_only=vision_only,
        synthesis=synthesis)
    else:
      return get_stan_user_prompt(
          mode=mode, 
          str_hypotheses=str_hypotheses, 
          vision_only=vision_only,
          synthesis=synthesis)

  def get_system_message(self, mode, 
                         prior_mode=False,
                         vision_only=False, 
                         critic_strategy=None, 
                         prev_synthesis=None, 
                         prev_str_hypotheses=None,
                         ):
    assert mode in ["proposal", "critic"]

    if self.prior_mode:
      dataset_description = self.dataset.get_description()
      df_str = ""
      column_description = self.dataset.describe_data_columns()
      system_str = get_stan_system_prompt_prior(mode=mode, 
                            dataset_description=dataset_description, 
                            df_str=df_str, 
                            expert_context="",
                            vision_only=vision_only,
                            column_description=column_description,
                            critic_strategy=critic_strategy,
                            prev_str_hypotheses=prev_str_hypotheses,
                            prev_synthesis=prev_synthesis,
                            )

    else:
      dataset_description = self.dataset.get_description()
      df_str = self.dataset.df.to_string(index=False)
      column_description = self.dataset.describe_data_columns()
      system_str = get_stan_system_prompt(mode=mode, 
                            dataset_description=dataset_description, 
                            df_str=df_str, 
                            expert_context="",
                            vision_only=vision_only,
                            column_description=column_description,
                            critic_strategy=critic_strategy,
                            prev_str_hypotheses=prev_str_hypotheses,
                            prev_synthesis=prev_synthesis,
                            )
    return system_str


  def evaluate(self, programs_all, logger, cfg, critic_info, proposal_agent, critic_agent):

    if self.prior_mode:
      return programs_all


    programs_all = sorted(programs_all, key = lambda x: -x['loo'])

    for i, r in enumerate(programs_all[:3]):
      logger.info(f"top {i} program {r['loo']}: \n {r['str_prob_prog']} \n")

    trace_dict = {}
    if len(programs_all) > 0:
      trace_dict['LLM'] = programs_all[0]['trace']
    
    return programs_all

