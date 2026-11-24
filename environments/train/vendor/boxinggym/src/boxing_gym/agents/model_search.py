import os
import pathlib
import traceback
import logging
from typing import List
from io import StringIO
from itertools import chain
import time

from tqdm import tqdm
from omegaconf import DictConfig, OmegaConf
import hydra
from hydra import compose 

from box_loop_helper import extract_python_code, extract_text_within_markers
from src.boxing_gym.agents.openai_wrapper import AsyncOpenAIGPT4V, AsyncOpenAIGPT3_Turbo
from src.boxing_gym.agents.llm import LLMAgent, StanProposalLLMAgent, StanCriticLLMAgent 
from src.boxing_gym.agents.box_loop_experiment import BoxLoop_Experiment

def extract_code_helper(response, logger):
  try:
                                     
    code_extract = extract_python_code(response)
    return code_extract, response
  except Exception as e:
    with StringIO() as buf:
        traceback.print_exc(file=buf)
        tb_str = buf.getvalue()
    logger.error(tb_str)
    logger.info(f"unable to extract code, response: {response}")
    return None

def select_exemplars(num_exemplars, curr_programs, programs, cfg, experiment):

  if cfg.incontext_heuristic == "recent":
    return curr_programs[:num_exemplars]
  else: 
    raise Exception(f"ERROR: {cfg.critic_exemplar_heuristic} is not a valid heuristic")

def get_critic_exemplars(curr_programs, programs, cfg, experiment):

    if cfg.critic_exemplar_heuristic == "recent":
      programs_to_evaluate = curr_programs.copy()
      return programs_to_evaluate
    else: 
      raise Exception(f"ERROR: {cfg.critic_exemplar_heuristic} is not a valid heuristic")
  
def extract_code_from_proposals(responses: List, logger):
                                  
  programs = [extract_code_helper(r, logger) for r in responses]
                                         
  programs = [item for item in programs if item is not None]
  return programs

def propose(
    agent: LLMAgent,
    experiment,
    system_message: str, 
    exemplar_list: List,
    user_messages: List[str],
    temperature: float, 
    logger,
    num_proposals: int,
    log_dir,
):
  pass                                                  
                                                     
                                               
     
  responses = agent.batch_prompt(
          expertise=system_message, 
          messages=user_messages, 
          data_image=None,
          incontext_info=exemplar_list,
          temperature=temperature,
          n=num_proposals,
  )

  if not agent.batch_mode:
    assert len(responses[0]) == num_proposals
    responses = list(chain.from_iterable(responses))
    assert len(responses) == num_proposals
  
  if agent.batch_mode:
    assert len(responses) == len(user_messages)
  
  for r in responses: logger.info(f"unscored program: {r}")
  
  programs = extract_code_from_proposals(responses, logger)

  programs = [extract_code_helper(r, logger) for r in responses]

  programs = [item for item in programs if item is not None]

                                                           
  logger.info(f"percent programs successfully extracted: {len(programs)/len(responses)}")

  if experiment.prior_mode:
    results = [
      {
        "full_llm_response": llm_response, 
        "str_prob_prog": program, 
        "trace": "", 
        "loo": "", 
        "waic": "", 
        "round":"" 
      }
      for program, llm_response in programs
    ]
  
  else:
    results = [
      experiment.score_programs(program=program, logger=logger, llm_response=llm_response) 
      for program, llm_response in programs
    ]

  assert len(results) == len(programs)

                           
  results = [item for item in results if item is not None]
  
                                                                                                 
  results = experiment.filter_fn(results)
  
  logger.info(f"Percent successfuly scored programs: {len(results)/num_proposals}")

  results = experiment.sort_fn(results)
  return results

def initialize_experiment(cfg, logger, log_dir, env, prior_mode):
  return BoxLoop_Experiment(
    dataset=env,
    logger=logger, 
    corrupt=cfg.corrupt,
    log_dir=log_dir,
    language_synthesize=cfg.language_synthesize,
    prior_mode=prior_mode,
  )

def get_llms(cfg):
  experiment2tokens = {"ODE": 2000, "GPs": 1500, "box_loop": 4096, "Other_ODE": 1500}
  if cfg.llm == "GPT4-V":
    return AsyncOpenAIGPT4V(max_tokens=experiment2tokens[cfg.experiment])
  elif cfg.llm == "GPT3.5-turbo":
      assert cfg.use_vision == False 
      return AsyncOpenAIGPT3_Turbo(max_tokens=experiment2tokens[cfg.experiment])  
  else:
    raise Exception(f"ERROR: {cfg.llm} is not a valid API (yet)")

def get_proposal_agent(cfg, warm_start_examples, logger):

  llm = get_llms(cfg)

  if cfg.warm_start:
    experiment_to_agent = {
      "box_loop": StanProposalLLMAgent(
        llm, 
        model_id=cfg.llm, 
        batch_mode=False,
        warm_start_examples=warm_start_examples,
        logger=logger,
        use_vision=cfg.use_vision,
        ),
    }
    assert cfg.experiment in experiment_to_agent
    return experiment_to_agent[cfg.experiment]
  
  else:
    experiment_to_agent = {
      "box_loop": StanProposalLLMAgent(llm, vision_only=cfg.vision_only, model_id=cfg.llm, use_vision=cfg.use_vision, batch_mode=False, logger=logger),
    }

    assert cfg.experiment in experiment_to_agent
    return experiment_to_agent[cfg.experiment]

def get_critic_agent(cfg, logger):
  llm = get_llms(cfg)

  experiment_to_agent = {
      "box_loop": StanCriticLLMAgent(llm, 
                                 logger=logger, 
                                 vision_only=cfg.vision_only ,model_id=cfg.llm, use_vision=cfg.use_vision, batch_mode=False),
  }

  assert cfg.experiment in experiment_to_agent
  return experiment_to_agent[cfg.experiment]

def validate_exemplars(cfg, round_idx, exemplar_list):
                                                                                      
  if (len(exemplar_list) > 0) and (cfg.incontext_heuristic == "recent"):
    for r in exemplar_list:
      assert r['round'] == round_idx-1

def critic(
    agent: LLMAgent, 
    system_message: str, 
    incontext_info: List,
    user_messages: List[str],
    temperature: float, 
    experiment,
    logger,
    cfg, 
):

  responses = agent.batch_prompt(
          expertise=system_message, 
          messages=user_messages, 
          data_image=None,
          incontext_info=incontext_info,
          temperature=temperature
  )

  assert len(responses) == 1
  llm_response = responses[0][0]

  logger.info(f"Critic response: {llm_response}")

  try:
                                     
    str_hypotheses = extract_text_within_markers(llm_response, "Hypotheses")[0]
    synthesis = extract_text_within_markers(llm_response, "Synthesis")[0]
    logger.info(f"hypotheses: \n {str_hypotheses} \n")
    logger.info(f"synthesis: \n {synthesis} \n")
  except Exception as e:
    print(f"unable to extract hypotheses:( {e}")
    with StringIO() as buf:
        traceback.print_exc(file=buf)
        tb_str = buf.getvalue()
                       
    logger.error(tb_str)
    return "", "" 
  
  return str_hypotheses, synthesis

def get_warm_start_example(experiment):

  results = [{"loo": experiment.expert_loo}]
  return results

def get_log_dir(cfg, env):

  global_ts = time.time()

  if not os.path.exists("./logs"): os.mkdir("./logs")

  log_dir = f"./logs/{cfg.experiment}_{env.env_name}_logs_{global_ts}/"
  log_file = f"{global_ts}_{cfg.experiment}.log"
  os.mkdir(log_dir)
  return log_dir, log_file

def validate_critic_state(cfg, critic_system_message, programs_to_evaluate, curr_programs, programs_all):
  if cfg.critic_exemplar_heuristic == "state_space":
    assert "Here are the hypotheses from the previous round" in critic_system_message
    assert "Here are the synthesis from the previous round" in critic_system_message

def run_box_loop(env, warm_start_examples, prior_mode=False, critic_mode=False, prev_str_hypotheses="", prev_synthesis=""): 

  cfg = compose(config_name="box_loop")
  
  log_dir, log_file = get_log_dir(cfg, env)

  start = time.time()
  
  logging.basicConfig(filename=os.path.join(log_dir, log_file), level=logging.INFO)
  logger = logging.getLogger(__name__)

  args_str = ', '.join(f'{key}={value}' for key, value in vars(cfg).items())
  logger.info(f'Running with these args: {args_str}')

                                                                                                
  experiment = initialize_experiment(
    cfg=cfg, 
    logger=logger, 
    log_dir=log_dir, 
    env=env,
    prior_mode=prior_mode,
  )

  proposal_agent = get_proposal_agent(cfg, warm_start_examples=warm_start_examples, logger=logger)
  critic_agent = get_critic_agent(cfg, logger=logger)
  
  if not os.path.exists(experiment.checkpoint_dir):
    print(f"making path: {experiment.checkpoint_dir}")
    pathlib.Path(experiment.checkpoint_dir).mkdir(parents=True, exist_ok=True)
  else:
    print(f"path: {experiment.checkpoint_dir} already exists")

  temperature_sched = [cfg.proposal_temperature] * cfg.num_rounds
  num_candidates = [cfg.num_proposals] * cfg.num_rounds

  assert len(num_candidates) == cfg.num_rounds
  assert len(temperature_sched) == cfg.num_rounds

  exemplar_list = []
  programs_all = []
  exemplars_all = []
  critic_info = []

  str_hypotheses = ""
  synthesis = ""

  assert cfg.num_to_consider >= cfg.num_proposals

  print("Entering model_search loop")

  for round_idx in tqdm(range(cfg.num_rounds)):

    proposal_system_message = experiment.get_system_message(
      mode="proposal",
      vision_only=cfg.vision_only,
      prev_str_hypotheses=prev_str_hypotheses,
      prev_synthesis=prev_synthesis,
    )

    proposal_user_message = experiment.get_user_message(
      mode="proposal", 
      synthesis=synthesis, 
      str_hypotheses=str_hypotheses,
      vision_only=cfg.vision_only,
    )

    logger.info(f"proposal_system_message: {proposal_system_message}")
    print(f"proposal_system_message: {proposal_system_message}")
    logger.info(f"proposal_user_message: {proposal_user_message}")

    validate_exemplars(cfg=cfg, round_idx=round_idx, exemplar_list=exemplar_list)

    curr_programs = propose(
        agent=proposal_agent,
        experiment=experiment,
        system_message=proposal_system_message, 
        exemplar_list=exemplar_list,
        user_messages=[proposal_user_message],
        temperature=temperature_sched[round_idx], 
        logger=logger,
        num_proposals=num_candidates[round_idx],
        log_dir=log_dir,
    )


    for p in curr_programs:
      p['round'] = round_idx
      programs_all.append(p)

    exemplar_list = select_exemplars(
      num_exemplars=cfg.num_exemplars, 
      curr_programs=curr_programs, 
      programs=programs_all,
      cfg=cfg,
      experiment=experiment,
      )
    
    for exemplar in exemplar_list:
      exemplars_all.append((round_idx, exemplar))


    if critic_mode: 

      if round_idx == 0:
        assert len(synthesis) == 0
        assert len(str_hypotheses) == 0
      
      
      if cfg.critic_exemplar_heuristic in ["recent"]:
        critic_system_message = experiment.get_system_message(
          mode="critic", 
          critic_strategy=cfg.critic_exemplar_heuristic,  
          vision_only=cfg.vision_only,
          prev_str_hypotheses=prev_str_hypotheses,
          prev_synthesis=prev_str_hypotheses,
          )
        critic_user_message = experiment.get_user_message(
          mode="critic", 
          vision_only=cfg.vision_only, 
          synthesis=None, 
          str_hypotheses=None)
      
      else:
        critic_system_message = experiment.get_system_message(
          mode="critic", 
          critic_strategy=cfg.critic_exemplar_heuristic,  
          vision_only=cfg.vision_only,
          str_hypotheses=str_hypotheses,
          synthesis=synthesis,
          )

        critic_user_message = experiment.get_user_message(
          mode="critic", 
          vision_only=cfg.vision_only, 
          synthesis=synthesis, 
          str_hypotheses=str_hypotheses)

      logger.info(f"critic_system_message: {critic_system_message}")
      logger.info(f"critic_user_message: {critic_user_message}")
      logger.info(f"str_hypotheses: {str_hypotheses}")
      logger.info(f"synthesis: {synthesis}")
      
      programs_to_evaluate = get_critic_exemplars(
        curr_programs=curr_programs, programs=programs_all, cfg=cfg, experiment=experiment)

      validate_critic_state(cfg=cfg, 
                            critic_system_message=critic_system_message, 
                            programs_to_evaluate=programs_to_evaluate, 
                            curr_programs=curr_programs, 
                            programs_all=programs_all)

      str_hypotheses, synthesis = critic(
          agent=critic_agent, 
          system_message=critic_system_message, 
          experiment=experiment,
          incontext_info=programs_to_evaluate,                                          
          user_messages=[critic_user_message] * 1,
          logger=logger,
          temperature=cfg.critic_temperature,
          cfg=cfg,
      )
      critic_info.append(({"round_idx": round_idx, "str_hypotheses": str_hypotheses, "synthesis": synthesis}))

  end = time.time()

  programs_all = experiment.evaluate(programs_all=programs_all, 
                      logger=logger, 
                      cfg=cfg, 
                      critic_info=critic_info,
                      proposal_agent=proposal_agent,
                      critic_agent=critic_agent,
                      )

  end = time.time()
  time_taken = (end-start)/60
  logger.info(f"time taken: {time_taken}")
  print("from run_box_looper_helper")
  return programs_all, critic_info


if __name__ == "__main__":
  run_box_loop()