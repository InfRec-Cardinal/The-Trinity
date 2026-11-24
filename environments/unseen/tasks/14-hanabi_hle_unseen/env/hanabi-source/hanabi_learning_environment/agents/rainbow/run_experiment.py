              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                                 

                                                            
   

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

from third_party.dopamine import checkpointer
from third_party.dopamine import iteration_statistics
import dqn_agent
import gin.tf
from hanabi_learning_environment import rl_env
import numpy as np
import rainbow_agent
import tensorflow as tf

LENIENT_SCORE = False


class ObservationStacker(object):
  pass                                        

  def __init__(self, history_size, observation_size, num_players):
    pass                                   

         
                                                       
                                                                         
                                          
       
    self._history_size = history_size
    self._observation_size = observation_size
    self._num_players = num_players
    self._obs_stacks = list()
    for _ in range(0, self._num_players):
      self._obs_stacks.append(np.zeros(self._observation_size *
                                       self._history_size))

  def add_observation(self, observation, current_player):
    pass                                       

         
                                                         
                                             
       
    self._obs_stacks[current_player] = np.roll(self._obs_stacks[current_player],
                                               -self._observation_size)
    self._obs_stacks[current_player][(self._history_size - 1) *
                                     self._observation_size:] = observation

  def get_observation_stack(self, current_player):
    pass                                                  

         
                                             
       

    return self._obs_stacks[current_player]

  def reset_stack(self):
    pass                                            

    for i in range(0, self._num_players):
      self._obs_stacks[i].fill(0.0)

  @property
  def history_size(self):
    pass                                   
    return self._history_size

  def observation_size(self):
    pass                                                                    
    return self._observation_size * self._history_size


def load_gin_configs(gin_files, gin_bindings):
  pass                             

       
                                                                      
                 
                                                                              
                   
     
  gin.parse_config_files_and_bindings(gin_files,
                                      bindings=gin_bindings,
                                      skip_unknown=False)


@gin.configurable
def create_environment(game_type='Hanabi-Full', num_players=2):
  pass                              

       
                                                                           
                                
                                                                            
                                                          

          
                         
     
  return rl_env.make(
      environment_name=game_type, num_players=num_players, pyhanabi_path=None)


@gin.configurable
def create_obs_stacker(environment, history_size=4):
  pass                              

       
                                    
                                                

          
                                  
     

  return ObservationStacker(history_size,
                            environment.vectorized_observation_shape()[0],
                            environment.players)


@gin.configurable
def create_agent(environment, obs_stacker, agent_type='DQN'):
  pass                        

       
                                 
                                            
                                                

          
                                

         
                                                      
     
  if agent_type == 'DQN':
    return dqn_agent.DQNAgent(observation_size=obs_stacker.observation_size(),
                              num_actions=environment.num_moves(),
                              num_players=environment.players)
  elif agent_type == 'Rainbow':
    return rainbow_agent.RainbowAgent(
        observation_size=obs_stacker.observation_size(),
        num_actions=environment.num_moves(),
        num_players=environment.players)
  else:
    raise ValueError('Expected valid agent_type, got {}'.format(agent_type))


def initialize_checkpointing(agent, experiment_logger, checkpoint_dir,
                             checkpoint_file_prefix='ckpt'):
  pass                                          

                                    
                                                                               
                                                              
                                                                             
                                                                           
                         
                                                                            
                                                                       
                                                                                
                                                                             
                                                                          
                                                                              
                                          

       
                                                                           
                                                                     
                 
                                                                  
                                                            

          
                                                                            
                                                         
     
  experiment_checkpointer = checkpointer.Checkpointer(
      checkpoint_dir, checkpoint_file_prefix)

  start_iteration = 0

                                                                             
                                                                          
  latest_checkpoint_version = checkpointer.get_latest_checkpoint_number(
      checkpoint_dir)
  if latest_checkpoint_version >= 0:
    dqn_dictionary = experiment_checkpointer.load_checkpoint(
        latest_checkpoint_version)
    if agent.unbundle(
        checkpoint_dir, latest_checkpoint_version, dqn_dictionary):
      assert 'logs' in dqn_dictionary
      assert 'current_iteration' in dqn_dictionary
      experiment_logger.data = dqn_dictionary['logs']
      start_iteration = dqn_dictionary['current_iteration'] + 1
      tf.logging.info('Reloaded checkpoint and will start from iteration %d',
                      start_iteration)

  return start_iteration, experiment_checkpointer


def format_legal_moves(legal_moves, action_dim):
  pass                             

                                                                                
                                                                              
            
                                             
                                   

       
                                       
                                       

          
                                
     
  new_legal_moves = np.full(action_dim, -float('inf'))
  if legal_moves:
    new_legal_moves[legal_moves] = 0
  return new_legal_moves


def parse_observations(observations, num_actions, obs_stacker):
  pass                                                               

       
                                                     
                                                      
                                            

          
                                          
                                                                            
                                                                          
                                   
                                                                      
     
  current_player = observations['current_player']
  current_player_observation = (
      observations['player_observations'][current_player])

  legal_moves = current_player_observation['legal_moves_as_int']
  legal_moves = format_legal_moves(legal_moves, num_actions)

  observation_vector = current_player_observation['vectorized']
  obs_stacker.add_observation(observation_vector, current_player)
  observation_vector = obs_stacker.get_observation_stack(current_player)

  return current_player, legal_moves, observation_vector


def run_one_episode(agent, environment, obs_stacker):
  pass                                                           

       
                                
                                        
                                            

          
                                                        
                                                              
     
  obs_stacker.reset_stack()
  observations = environment.reset()
  current_player, legal_moves, observation_vector = (
      parse_observations(observations, environment.num_moves(), obs_stacker))
  action = agent.begin_episode(current_player, legal_moves, observation_vector)

  is_done = False
  total_reward = 0
  step_number = 0

  has_played = {current_player}

                                    
  reward_since_last_action = np.zeros(environment.players)

  while not is_done:
    observations, reward, is_done, _ = environment.step(action.item())

    modified_reward = max(reward, 0) if LENIENT_SCORE else reward
    total_reward += modified_reward

    reward_since_last_action += modified_reward

    step_number += 1
    if is_done:
      break
    current_player, legal_moves, observation_vector = (
        parse_observations(observations, environment.num_moves(), obs_stacker))
    if current_player in has_played:
      action = agent.step(reward_since_last_action[current_player],
                          current_player, legal_moves, observation_vector)
    else:
                                                                            
                                    
      action = agent.begin_episode(current_player, legal_moves,
                                   observation_vector)
      has_played.add(current_player)

                                             
    reward_since_last_action[current_player] = 0

  agent.end_episode(reward_since_last_action)

  tf.logging.info('EPISODE: %d %g', step_number, total_reward)
  return step_number, total_reward


def run_one_phase(agent, environment, obs_stacker, min_steps, statistics,
                  run_mode_str):
  pass                                                               

       
                                
                                    
                                            
                                                                      
                                                                           
              
                                                             

          
                                                                        
                                   
     
  step_count = 0
  num_episodes = 0
  sum_returns = 0.

  while step_count < min_steps:
    episode_length, episode_return = run_one_episode(agent, environment,
                                                     obs_stacker)
    statistics.append({
        '{}_episode_lengths'.format(run_mode_str): episode_length,
        '{}_episode_returns'.format(run_mode_str): episode_return
    })

    step_count += episode_length
    sum_returns += episode_return
    num_episodes += 1

  return step_count, sum_returns, num_episodes


@gin.configurable
def run_one_iteration(agent, environment, obs_stacker,
                      iteration, training_steps,
                      evaluate_every_n=100,
                      num_evaluation_games=100):
  pass                                                   

                                                                          
                     

       
                                
                                        
                                            
                                                                    
                                                                 
                                                   
                                                              

          
                                                            
     
  start_time = time.time()

  statistics = iteration_statistics.IterationStatistics()

                                                                    
  agent.eval_mode = False
  number_steps, sum_returns, num_episodes = (
      run_one_phase(agent, environment, obs_stacker, training_steps, statistics,
                    'train'))
  time_delta = time.time() - start_time
  tf.logging.info('Average training steps per second: %.2f',
                  number_steps / time_delta)

  average_return = sum_returns / num_episodes
  tf.logging.info('Average per episode return: %.2f', average_return)
  statistics.append({'average_return': average_return})

                                            
  if evaluate_every_n is not None and iteration % evaluate_every_n == 0:
    episode_data = []
    agent.eval_mode = True
                                         
    for _ in range(num_evaluation_games):
      episode_data.append(run_one_episode(agent, environment, obs_stacker))

    eval_episode_length, eval_episode_return = map(np.mean, zip(*episode_data))

    statistics.append({
        'eval_episode_lengths': eval_episode_length,
        'eval_episode_returns': eval_episode_return
    })
    tf.logging.info('Average eval. episode length: %.2f  Return: %.2f',
                    eval_episode_length, eval_episode_return)
  else:
    statistics.append({
        'eval_episode_lengths': -1,
        'eval_episode_returns': -1
    })

  return statistics.data_lists


def log_experiment(experiment_logger, iteration, statistics,
                   logging_file_prefix='log', log_every_n=1):
  pass                                            

       
                                         
                                     
                                                    
                                                              
                                                  
     
  if iteration % log_every_n == 0:
    experiment_logger['iter{:d}'.format(iteration)] = statistics
    experiment_logger.log_to_file(logging_file_prefix, iteration)


def checkpoint_experiment(experiment_checkpointer, agent, experiment_logger,
                          iteration, checkpoint_dir, checkpoint_every_n):
  pass                          

       
                                                     
                       
                                                                              
                                                       
                                                                 
                                                                   
     
  if iteration % checkpoint_every_n == 0:
    agent_dictionary = agent.bundle_and_checkpoint(checkpoint_dir, iteration)
    if agent_dictionary:
      agent_dictionary['current_iteration'] = iteration
      agent_dictionary['logs'] = experiment_logger.data
      experiment_checkpointer.save_checkpoint(iteration, agent_dictionary)


@gin.configurable
def run_experiment(agent,
                   environment,
                   start_iteration,
                   obs_stacker,
                   experiment_logger,
                   experiment_checkpointer,
                   checkpoint_dir,
                   num_iterations=200,
                   training_steps=5000,
                   logging_file_prefix='log',
                   log_every_n=1,
                   checkpoint_every_n=1):
  pass                                                          
  tf.logging.info('Beginning training...')
  if num_iterations <= start_iteration:
    tf.logging.warning('num_iterations (%d) < start_iteration(%d)',
                       num_iterations, start_iteration)
    return

  for iteration in range(start_iteration, num_iterations):
    start_time = time.time()
    statistics = run_one_iteration(agent, environment, obs_stacker, iteration,
                                   training_steps)
    tf.logging.info('Iteration %d took %d seconds', iteration,
                    time.time() - start_time)
    start_time = time.time()
    log_experiment(experiment_logger, iteration, statistics,
                   logging_file_prefix, log_every_n)
    tf.logging.info('Logging iteration %d took %d seconds', iteration,
                    time.time() - start_time)
    start_time = time.time()
    checkpoint_experiment(experiment_checkpointer, agent, experiment_logger,
                          iteration, checkpoint_dir, checkpoint_every_n)
    tf.logging.info('Checkpointing iteration %d took %d seconds', iteration,
                    time.time() - start_time)
