              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                                                       

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import math
import os
import random

import gin.tf
import numpy as np
import replay_memory
import tensorflow as tf


slim = tf.contrib.slim

Transition = collections.namedtuple(
    'Transition', ['reward', 'observation', 'legal_actions', 'action', 'begin'])


def linearly_decaying_epsilon(decay_period, step, warmup_steps, epsilon):
  pass                                                                     

       
                                                      
                                                                 
                                                                        
                                      

          
                                                 
     
  steps_left = decay_period + warmup_steps - step
  bonus = (1.0 - epsilon) * steps_left / decay_period
  bonus = np.clip(bonus, 0.0, 1.0 - epsilon)
  return epsilon + bonus


def dqn_template(state, num_actions, layer_size=512, num_layers=1):
  pass                                                

       
                                               
                                                                   
                                                      
                                             

          
                                 
                                                                 
     
  weights_initializer = slim.variance_scaling_initializer(
      factor=1.0 / np.sqrt(3.0), mode='FAN_IN', uniform=True)

  net = tf.cast(state, tf.float32)
  net = tf.squeeze(net, axis=2)
  for _ in range(num_layers):
    net = slim.fully_connected(net, layer_size,
                               activation_fn=tf.nn.relu)
  net = slim.fully_connected(net, num_actions, activation_fn=None,
                             weights_initializer=weights_initializer)
  return net


@gin.configurable
class DQNAgent(object):
  pass                                                        

  @gin.configurable
  def __init__(self,
               num_actions=None,
               observation_size=None,
               num_players=None,
               gamma=0.99,
               update_horizon=1,
               min_replay_history=500,
               update_period=4,
               stack_size=1,
               target_update_period=500,
               epsilon_fn=linearly_decaying_epsilon,
               epsilon_train=0.02,
               epsilon_eval=0.001,
               epsilon_decay_period=1000,
               graph_template=dqn_template,
               tf_device='/cpu:*',
               use_staging=True,
               optimizer=tf.train.RMSPropOptimizer(
                   learning_rate=.0025,
                   decay=0.95,
                   momentum=0.0,
                   epsilon=1e-6,
                   centered=True)):
    pass                                              

         
                                                                          
                                                        
                                                            
                                                                          
                                                                             
                      
                                                                            
                                                     
                                                              
                                                                 
                                                                       
                                                                            
                                    
                                                       
                                                     
                                                                      
                                                                     
                                                                     
                                                                          
                       
                                                      
       

    tf.logging.info('Creating %s agent with the following parameters:',
                    self.__class__.__name__)
    tf.logging.info('\t gamma: %f', gamma)
    tf.logging.info('\t update_horizon: %f', update_horizon)
    tf.logging.info('\t min_replay_history: %d', min_replay_history)
    tf.logging.info('\t update_period: %d', update_period)
    tf.logging.info('\t target_update_period: %d', target_update_period)
    tf.logging.info('\t epsilon_train: %f', epsilon_train)
    tf.logging.info('\t epsilon_eval: %f', epsilon_eval)
    tf.logging.info('\t epsilon_decay_period: %d', epsilon_decay_period)
    tf.logging.info('\t tf_device: %s', tf_device)
    tf.logging.info('\t use_staging: %s', use_staging)
    tf.logging.info('\t optimizer: %s', optimizer)

                       
    self.num_actions = num_actions
    self.observation_size = observation_size
    self.num_players = num_players
    self.gamma = gamma
    self.update_horizon = update_horizon
    self.cumulative_gamma = math.pow(gamma, update_horizon)
    self.min_replay_history = min_replay_history
    self.target_update_period = target_update_period
    self.epsilon_fn = epsilon_fn
    self.epsilon_train = epsilon_train
    self.epsilon_eval = epsilon_eval
    self.epsilon_decay_period = epsilon_decay_period
    self.update_period = update_period
    self.eval_mode = False
    self.training_steps = 0
    self.batch_staged = False
    self.optimizer = optimizer

    with tf.device(tf_device):
                                                                      
                                                                            
                         
      online_convnet = tf.make_template('Online', graph_template)
      target_convnet = tf.make_template('Target', graph_template)
                                                                                
                               
      states_shape = (1, observation_size, stack_size)
      self.state = np.zeros(states_shape)
      self.state_ph = tf.placeholder(tf.uint8, states_shape, name='state_ph')
      self.legal_actions_ph = tf.placeholder(tf.float32,
                                             [self.num_actions],
                                             name='legal_actions_ph')
      self._q = online_convnet(
          state=self.state_ph, num_actions=self.num_actions)
      self._replay = self._build_replay_memory(use_staging)
      self._replay_qs = online_convnet(self._replay.states, self.num_actions)
      self._replay_next_qt = target_convnet(self._replay.next_states,
                                            self.num_actions)
      self._train_op = self._build_train_op()
      self._sync_qt_ops = self._build_sync_op()

      self._q_argmax = tf.argmax(self._q + self.legal_actions_ph, axis=1)[0]

                                                
    self._sess = tf.Session(
        '', config=tf.ConfigProto(allow_soft_placement=True))
    self._init_op = tf.global_variables_initializer()
    self._sess.run(self._init_op)

    self._saver = tf.train.Saver(max_to_keep=3)

                                                                         
             
    self.transitions = [[] for _ in range(num_players)]

  def _build_replay_memory(self, use_staging):
    pass                                           

         
                                                                    

            
                             
       
    return replay_memory.WrappedReplayMemory(
        num_actions=self.num_actions,
        observation_size=self.observation_size,
        batch_size=32,
        stack_size=1,
        use_staging=use_staging,
        update_horizon=self.update_horizon,
        gamma=self.gamma)

  def _build_target_q_op(self):
    pass                                                  

            
                                                        
       
                                                       
    replay_next_qt_max = tf.reduce_max(self._replay_next_qt +
                                       self._replay.next_legal_actions, 1)
                                          
                                     
            
                                       
                                                 
         
                                                  
    return self._replay.rewards + self.cumulative_gamma * replay_next_qt_max * (
        1. - tf.cast(self._replay.terminals, tf.float32))

  def _build_train_op(self):
    pass                    

            
                                                      
       
    replay_action_one_hot = tf.one_hot(
        self._replay.actions, self.num_actions, 1., 0., name='action_one_hot')
    replay_chosen_q = tf.reduce_sum(
        self._replay_qs * replay_action_one_hot,
        reduction_indices=1,
        name='replay_chosen_q')

    target = tf.stop_gradient(self._build_target_q_op())
    loss = tf.losses.huber_loss(
        target, replay_chosen_q, reduction=tf.losses.Reduction.NONE)
    return self.optimizer.minimize(tf.reduce_mean(loss))

  def _build_sync_op(self):
    pass                                                             

            
                                                                         
       
                                                              
    sync_qt_ops = []
    trainables_online = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope='Online')
    trainables_target = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope='Target')
    for (w_online, w_target) in zip(trainables_online, trainables_target):
                                                     
      sync_qt_ops.append(w_target.assign(w_online, use_locking=True))
    return sync_qt_ops

  def begin_episode(self, current_player, legal_actions, observation):
    pass                                

         
                                                       
                                                                             
                                                                     

            
                                 
       
    self._train_step()

    self.action = self._select_action(observation, legal_actions)
    self._record_transition(current_player, 0, observation, legal_actions,
                            self.action, begin=True)
    return self.action

  def step(self, reward, current_player, legal_actions, observation):
    pass                                                                 

                                                                            
                                                                             

         
                                                         
                                                       
                                                                             
                                                           

            
                                 
       
    self._train_step()

    self.action = self._select_action(observation, legal_actions)
    self._record_transition(current_player, reward, observation, legal_actions,
                            self.action)
    return self.action

  def end_episode(self, final_rewards):
    pass                                           

         
                                                                            
                                                                           
                        
       
    self._post_transitions(terminal_rewards=final_rewards)

  def _record_transition(self, current_player, reward, observation,
                         legal_actions, action, begin=False):
    pass                                       

                                                                              
                                                            
                                           
                                                                 
                                                   

         
                                                                  
                                         
                                                        
                                                               
                                       
                                                                
       
    self.transitions[current_player].append(
        Transition(reward, np.array(observation, dtype=np.uint8, copy=True),
                   np.array(legal_actions, dtype=np.float32, copy=True),
                   action, begin))

  def _post_transitions(self, terminal_rewards):
    pass                                       

                                                                  

         
                                                                    
       
                                                                        
    for player in range(self.num_players):
      num_transitions = len(self.transitions[player])

      for index, transition in enumerate(self.transitions[player]):
                                                 
        final_transition = index == num_transitions - 1
        if final_transition:
          reward = terminal_rewards[player]
        else:
          reward = self.transitions[player][index + 1].reward

        self._store_transition(transition.observation, transition.action,
                               reward, final_transition,
                               transition.legal_actions)

                                                                           
               
      self.transitions[player] = []

  def _select_action(self, observation, legal_actions):
    pass                                                

                                                                              
                                                                      

         
                                                       
                                                                            
                  

            
                                  
       
    if self.eval_mode:
      epsilon = self.epsilon_eval
    else:
      epsilon = self.epsilon_fn(self.epsilon_decay_period, self.training_steps,
                                self.min_replay_history, self.epsilon_train)

    if random.random() <= epsilon:
                                                        
      legal_action_indices = np.where(legal_actions == 0.0)
      return np.random.choice(legal_action_indices[0])
    else:
                                                      
      self.state[0, :, 0] = observation

                                                                          
      action = self._sess.run(self._q_argmax,
                              {self.state_ph: self.state,
                               self.legal_actions_ph: legal_actions})
      assert legal_actions[action] == 0.0, 'Expected legal action.'
      return action

  def _train_step(self):
    pass                           

                               
                                                                        
                                                          

                                                                            
                                     
       
    if self.eval_mode:
      return

                        
    if (self._replay.memory.add_count >= self.min_replay_history and
        not self.batch_staged):
      self._sess.run(self._replay.prefetch_batch)
      self.batch_staged = True
    if (self._replay.memory.add_count > self.min_replay_history and
        self.training_steps % self.update_period == 0):
      self._sess.run([self._train_op, self._replay.prefetch_batch])
                   
    if self.training_steps % self.target_update_period == 0:
      self._sess.run(self._sync_qt_ops)
    self.training_steps += 1

  def _store_transition(self, observation, action, reward, is_terminal,
                        legal_actions):
    pass                                        

                                                                              
                                                                           
                 

         
                                           
                                    
                                
                                                                             
                                                          
       
    if not self.eval_mode:
      self._sess.run(
          self._replay.add_transition_op, {
              self._replay.add_obs_ph: observation,
              self._replay.add_action_ph: action,
              self._replay.add_reward_ph: reward,
              self._replay.add_terminal_ph: is_terminal,
              self._replay.add_legal_actions_ph: legal_actions
          })

  def bundle_and_checkpoint(self, checkpoint_dir, iteration_number):
    pass                                                    

                                                                              
                                                                                
                                                  

         
                                                                            
                                                                             

            
                                                                        
                                                                     
       
    if not tf.gfile.Exists(checkpoint_dir):
      return None
    self._saver.save(
        self._sess,
        os.path.join(checkpoint_dir, 'tf_ckpt'),
        global_step=iteration_number)
    self._replay.save(checkpoint_dir, iteration_number)
    bundle_dictionary = {}
    bundle_dictionary['state'] = self.state
    bundle_dictionary['eval_mode'] = self.eval_mode
    bundle_dictionary['training_steps'] = self.training_steps
    bundle_dictionary['batch_staged'] = self.batch_staged
    return bundle_dictionary

  def unbundle(self, checkpoint_dir, iteration_number, bundle_dictionary):
    pass                                    

                                                                                
                                                                 
                                                                            
                    

         
                                                                     
                                                
                                                                           

            
                                                             
       
    try:
                                                                       
                                                                   
      self._replay.load(checkpoint_dir, iteration_number)
    except tf.errors.NotFoundError:
      return False
    for key in self.__dict__:
      if key in bundle_dictionary:
        self.__dict__[key] = bundle_dictionary[key]
    self._saver.restore(self._sess, tf.train.latest_checkpoint(checkpoint_dir))
    return True
