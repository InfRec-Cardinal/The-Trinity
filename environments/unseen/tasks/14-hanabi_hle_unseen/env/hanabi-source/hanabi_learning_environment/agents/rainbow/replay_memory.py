              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                  

                                                                           
                                                                              
                                                                              
                                                                         
                       
   

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gzip
import math
import os
import pickle

import gin.tf
import numpy as np
import tensorflow as tf


                                                                        
CHECKPOINT_DURATION = 4
MAX_SAMPLE_ATTEMPTS = 1000000


def invalid_range(cursor, replay_capacity, stack_size):
  pass                                                           

                                                                             

       
                                            
                                                        
                                                                          

          
                                                           
     
  assert cursor < replay_capacity
  return np.array(
      [(cursor - 1 + i) % replay_capacity for i in range(stack_size)])


class OutOfGraphReplayMemory(object):
  pass                                   

                                                                       
                                                                         
                                                     

             
                                                                
                                                              
                                                    
                                                    
                                                        
                                                                           
                                                         
     

  def __init__(self, num_actions, observation_size, stack_size, replay_capacity,
               batch_size, update_horizon=1, gamma=1.0):
    pass                                      

         
                                                   
                                                    
                                                              
                                                                    
                                  
                                                                   
                                        
       
    self._observation_size = observation_size
    self._num_actions = num_actions
    self._replay_capacity = replay_capacity
    self._batch_size = batch_size
    self._stack_size = stack_size
    self._update_horizon = update_horizon
    self._gamma = gamma

                                                                                
                                                                                
    self._cumulative_discount_vector = np.array(
        [math.pow(self._gamma, n) for n in range(update_horizon)],
        dtype=np.float32)

                                                            
    self.observations = np.empty(
        (replay_capacity, observation_size), dtype=np.uint8)
    self.actions = np.empty((replay_capacity), dtype=np.int32)
    self.rewards = np.empty((replay_capacity), dtype=np.float32)
    self.terminals = np.empty((replay_capacity), dtype=np.uint8)
    self.legal_actions = np.empty((replay_capacity, num_actions),
                                  dtype=np.float32)
    self.reset_state_batch_arrays(batch_size)
    self.add_count = np.array(0)

    self.invalid_range = np.zeros((self._stack_size))

  def add(self, observation, action, reward, terminal, legal_actions):
    pass                                      

                                                                              
                                     

                                                                                

         
                                                        
                                                             
                                                                      
                                                                            
                                             
                                                                         
       
    if self.is_empty() or self.terminals[self.cursor() - 1] == 1:
      dummy_observation = np.zeros((self._observation_size))
      dummy_legal_actions = np.zeros((self._num_actions))
      for _ in range(self._stack_size - 1):
        self._add(dummy_observation, 0, 0, 0, dummy_legal_actions)
    self._add(observation, action, reward, terminal, legal_actions)

  def _add(self, observation, action, reward, terminal, legal_actions):
    cursor = self.cursor()
    self.observations[cursor] = observation
    self.actions[cursor] = action
    self.rewards[cursor] = reward
    self.terminals[cursor] = terminal
    self.legal_actions[cursor] = legal_actions
    self.add_count += 1
    self.invalid_range = invalid_range(self.cursor(), self._replay_capacity,
                                       self._stack_size)

  def is_empty(self):
    pass                             
    return self.add_count == 0

  def is_full(self):
    pass                            
    return self.add_count >= self._replay_capacity

  def cursor(self):
    pass                                                                  
    return self.add_count % self._replay_capacity

  def get_stack(self, array, index):
    pass                                       

         
                                               
                                                                          
            
                                      
       
    assert index >= 0
    assert index < self._replay_capacity
    if not self.is_full():
      assert index < self.cursor(), 'Index %i has not been added.' % index
      assert index >= self._stack_size - 1, ('Not enough elements to sample '
                                             'index %i' % index)
                      
    if index >= self._stack_size - 1:
      stack = array[(index - self._stack_size + 1):(index + 1), ...]
                     
    else:
      indices = [(index - i) % self._replay_capacity
                 for i in reversed(range(self._stack_size))]
      stack = array[indices, ...]
    return stack

  def get_observation_stack(self, index):
    state = self.get_stack(self.observations, index)
    return np.transpose(state, [1, 0])

  def get_terminal_stack(self, index):
    return self.get_stack(self.terminals, index)

  def is_valid_transition(self, index):
    pass                                               

                                                                                
              

         
                                                                            
                           

            
                                        

       
                  
    if index < 0 or index >= self._replay_capacity:
      return False
    if not self.is_full():
                                                                     
      if index >= self.cursor() - self._update_horizon:
        return False
                                                                              
      if index < self._stack_size - 1:
        return False

                                                
    if index in set(self.invalid_range):
      return False

                                                                            
                                                 
    if self.get_terminal_stack(index)[:-1].any():
      return False

    return True

  def reset_state_batch_arrays(self, batch_size):
    self._next_state_batch = np.empty(
        (batch_size, self._observation_size, self._stack_size), dtype=np.uint8)
    self._state_batch = np.empty(
        (batch_size, self._observation_size, self._stack_size), dtype=np.uint8)

  def sample_index_batch(self, batch_size):
    pass                                

         
                                                  

            
                                                   

           
                                                                                
       
    indices = []
    attempt_count = 0
    while len(indices) < batch_size and attempt_count < MAX_SAMPLE_ATTEMPTS:
      attempt_count += 1
                                                                     
      if self.is_full():
        index = np.random.randint(0, self._replay_capacity)
      else:
                                                                 
        index = np.random.randint(self._stack_size - 1, self.cursor() - 1)
      if self.is_valid_transition(index):
        indices.append(index)
    if len(indices) != batch_size:
      raise Exception('I tried %i times but only sampled %i valid transitions' %
                      (MAX_SAMPLE_ATTEMPTS, len(indices)))
    return indices

  def sample_transition_batch(self, batch_size=None, indices=None):
    pass                              

         
                                                                             
                                     
                                                                          
                      

            
                                                                   
                                                                            
                                                                     
                                                                  
                              
       
    if batch_size is None:
      batch_size = self._batch_size
    if batch_size != self._state_batch.shape[0]:
      self.reset_state_batch_arrays(batch_size)
    if not self.is_full():
      assert self.add_count >= batch_size, (
          'There is not enough to sample.'
          ' You need to call add at '
          'least %i (batch_size) times (currently it is %i)' % (batch_size,
                                                                self.add_count))
    if indices is None:
      indices = self.sample_index_batch(batch_size)
    assert len(indices) == batch_size

    action_batch = self.actions[indices]
    reward_batch = np.empty((batch_size), dtype=np.float32)
    terminal_batch = np.empty((batch_size), dtype=np.uint8)
    indices_batch = np.empty((batch_size), dtype=np.int32)
    next_legal_actions_batch = np.empty((batch_size, self._num_actions),
                                        dtype=np.float32)

    for batch_element, memory_index in enumerate(indices):
      indices_batch[batch_element] = memory_index

      self._state_batch[batch_element] = self.get_observation_stack(
          memory_index)

                                                                 
      trajectory_indices = [(memory_index + j) % self._replay_capacity for
                            j in range(self._update_horizon)]

                                                                       
      terminals_in_trajectory = np.nonzero(self.terminals[trajectory_indices])
      if terminals_in_trajectory[0].size == 0:
                                                                        
        terminal_batch[batch_element] = 0
        reward_batch[batch_element] = self._cumulative_discount_vector.dot(
            self.rewards[trajectory_indices])
      else:
                                                                            
                                                                          
        terminal_batch[batch_element] = 1
                                                                 
        terminal_index = np.min(terminals_in_trajectory)

        truncated_discount_vector = (
            self._cumulative_discount_vector[0:terminal_index + 1])
        reward_batch[batch_element] = truncated_discount_vector.dot(
            self.rewards[trajectory_indices[0:terminal_index + 1]])

      bootstrap_state_index = (
          (memory_index + self._update_horizon) % self._replay_capacity)
      self._next_state_batch[batch_element] = (
          self.get_observation_stack(bootstrap_state_index))
      next_legal_actions_batch[batch_element] = (
          self.legal_actions[bootstrap_state_index])

    return (self._state_batch, action_batch, reward_batch,
            self._next_state_batch, terminal_batch, indices_batch,
            next_legal_actions_batch)

  def _generate_filename(self, checkpoint_dir, name, suffix):
    return os.path.join(checkpoint_dir, '{}_ckpt.{}.gz'.format(name, suffix))

  def save(self, checkpoint_dir, iteration_number):
    pass                                                    

                                                                         

         
                                                                           
              
                                                                                
                         
       
    if not tf.gfile.Exists(checkpoint_dir):
      return
    for attr in self.__dict__:
      if not attr.startswith('_'):
        filename = self._generate_filename(checkpoint_dir, attr,
                                           iteration_number)
        with tf.gfile.Open(filename, 'wb') as f:
          with gzip.GzipFile(fileobj=f) as outfile:
                                                                              
                                                                               
                   
            if isinstance(self.__dict__[attr], np.ndarray):
              np.save(outfile, self.__dict__[attr], allow_pickle=False)
            else:
              pickle.dump(self.__dict__[attr], outfile)

                                                                               
                                  
      stale_iteration_number = iteration_number - CHECKPOINT_DURATION
      if stale_iteration_number >= 0:
        stale_filename = self._generate_filename(checkpoint_dir, attr,
                                                 stale_iteration_number)
        try:
          tf.gfile.Remove(stale_filename)
        except tf.errors.NotFoundError:
          pass

  def load(self, checkpoint_dir, suffix):
    pass                                                                

         
                                                                               
             
                                                           

           
                                                                      
       
                                                                                
                                                                   
    for attr in self.__dict__:
      if attr.startswith('_'):
        continue
      filename = self._generate_filename(checkpoint_dir, attr, suffix)
      if not tf.gfile.Exists(filename):
        raise tf.errors.NotFoundError(None, None,
                                      'Missing file: {}'.format(filename))
                                                                               
                    
    for attr in self.__dict__:
      if attr.startswith('_'):
        continue
      filename = self._generate_filename(checkpoint_dir, attr, suffix)
      with tf.gfile.Open(filename, 'rb') as f:
        with gzip.GzipFile(fileobj=f) as infile:
          if isinstance(self.__dict__[attr], np.ndarray):
            self.__dict__[attr] = np.load(infile, allow_pickle=False)
          else:
            self.__dict__[attr] = pickle.load(infile)


@gin.configurable(denylist=['observation_size', 'stack_size'])
class WrappedReplayMemory(object):
  pass                                             

        
                                                             
                                                                               

                                                                        
                                                                             
                                                               

                                                                               
                                                      

                                                                            
                                              

             
                                                             
                                                  
                                                                                
                                                                           
                                 
     

  def __init__(self,
               num_actions,
               observation_size,
               stack_size,
               use_staging=True,
               replay_capacity=1000000,
               batch_size=32,
               update_horizon=1,
               gamma=1.0,
               wrapped_memory=None):
    pass                                                        

         
                                                   
                                                    
                                                              
                                                                              
                            
                                                                    
                      
                                                                   
                                      
                                                                                
                                               

           
                                                    
                                                      
       
    if replay_capacity < update_horizon + 1:
      raise ValueError('Update horizon (%i) should be significantly smaller '
                       'than replay capacity (%i).'
                       % (update_horizon, replay_capacity))
    if not update_horizon >= 1:
      raise ValueError('Update horizon must be positive.')
    if not 0.0 <= gamma <= 1.0:
      raise ValueError('Discount factor (gamma) must be in [0, 1].')

                                             
    if wrapped_memory is not None:
      self.memory = wrapped_memory
    else:
      self.memory = OutOfGraphReplayMemory(
          num_actions, observation_size, stack_size,
          replay_capacity, batch_size, update_horizon, gamma)

    with tf.name_scope('replay'):
      with tf.name_scope('add_placeholders'):
        self.add_obs_ph = tf.placeholder(
            tf.uint8, [observation_size], name='add_obs_ph')
        self.add_action_ph = tf.placeholder(tf.int32, [], name='add_action_ph')
        self.add_reward_ph = tf.placeholder(
            tf.float32, [], name='add_reward_ph')
        self.add_terminal_ph = tf.placeholder(
            tf.uint8, [], name='add_terminal_ph')
        self.add_legal_actions_ph = tf.placeholder(
            tf.float32, [num_actions], name='add_legal_actions_ph')

      add_transition_ph = [
          self.add_obs_ph, self.add_action_ph, self.add_reward_ph,
          self.add_terminal_ph, self.add_legal_actions_ph
      ]

      with tf.device('/cpu:*'):
        self.add_transition_op = tf.py_func(
            self.memory.add, add_transition_ph, [], name='replay_add_py_func')

        self.transition = tf.py_func(
            self.memory.sample_transition_batch, [],
            [tf.uint8, tf.int32, tf.float32, tf.uint8, tf.uint8, tf.int32,
             tf.float32],
            name='replay_sample_py_func')

        if use_staging:
                                                                                
                                 
          (states, actions, rewards, next_states,
           terminals, indices, next_legal_actions) = self.transition
                                                              
          states.set_shape([batch_size, observation_size, stack_size])
          actions.set_shape([batch_size])
          rewards.set_shape([batch_size])
          next_states.set_shape(
              [batch_size, observation_size, stack_size])
          terminals.set_shape([batch_size])
          indices.set_shape([batch_size])
          next_legal_actions.set_shape([batch_size, num_actions])

                                           
          prefetch_area = tf.contrib.staging.StagingArea(
              [tf.uint8, tf.int32, tf.float32, tf.uint8, tf.uint8, tf.int32,
               tf.float32])

          self.prefetch_batch = prefetch_area.put(
              (states, actions, rewards, next_states, terminals, indices,
               next_legal_actions))
        else:
          self.prefetch_batch = tf.no_op()

      if use_staging:
                                                                             
                     
        self.transition = prefetch_area.get()

      (self.states, self.actions, self.rewards, self.next_states,
       self.terminals, self.indices, self.next_legal_actions) = self.transition

                                                                            
                                                                 
      self.states.set_shape([None, observation_size, stack_size])
      self.next_states.set_shape([None, observation_size, stack_size])

  def save(self, checkpoint_dir, iteration_number):
    pass                                                      

         
                                                                              
              
                                                                          
                               
       
    self.memory.save(checkpoint_dir, iteration_number)

  def load(self, checkpoint_dir, suffix):
    pass                                                 

         
                                                                              
              
                                                           
       
    self.memory.load(checkpoint_dir, suffix)
