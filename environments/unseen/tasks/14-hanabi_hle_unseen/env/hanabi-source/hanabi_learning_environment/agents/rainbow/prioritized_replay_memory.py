              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                                            

                                                                         
                                                                             
                                                                             
   

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from third_party.dopamine import sum_tree
import gin.tf
import numpy as np
import replay_memory
import tensorflow as tf

DEFAULT_PRIORITY = 100.0


class OutOfGraphPrioritizedReplayMemory(replay_memory.OutOfGraphReplayMemory):
  pass                                                               

                                   
     

  def __init__(self, num_actions, observation_size, stack_size, replay_capacity,
               batch_size, update_horizon=1, gamma=1.0):
    pass                                                               

         
                                          
                                                          
                                                              
                                                                    
                                  
                                                                   
                                      
       
    super(OutOfGraphPrioritizedReplayMemory, self).__init__(
        num_actions=num_actions,
        observation_size=observation_size, stack_size=stack_size,
        replay_capacity=replay_capacity, batch_size=batch_size,
        update_horizon=update_horizon, gamma=gamma)

    self.sum_tree = sum_tree.SumTree(replay_capacity)

  def add(self, observation, action, reward, terminal, legal_actions):
    pass                                      

                                                                              
                                     

                                                                                

                                                                        
                                  

         
                                                                          
                                                           
                                                                      
                                                                          
                                             
                                                                         
       
    if self.is_empty() or self.terminals[self.cursor() - 1] == 1:
      dummy_observation = np.zeros((self._observation_size))
      dummy_legal_actions = np.zeros((self._num_actions))
      for _ in range(self._stack_size - 1):
        self._add(dummy_observation, 0, 0, 0, dummy_legal_actions, priority=0.0)

    self._add(observation, action, reward, terminal, legal_actions,
              priority=DEFAULT_PRIORITY)

  def _add(self, observation, action, reward, terminal, legal_actions,
           priority=DEFAULT_PRIORITY):
    new_element_index = self.cursor()

    super(OutOfGraphPrioritizedReplayMemory, self)._add(
        observation, action, reward, terminal, legal_actions)

    self.sum_tree.set(new_element_index, priority)

  def sample_index_batch(self, batch_size):
    pass                                

         
                                                  

            
                                                       

           
                                                                                
       
    indices = []
    allowed_attempts = replay_memory.MAX_SAMPLE_ATTEMPTS

    while len(indices) < batch_size and allowed_attempts > 0:
      index = self.sum_tree.sample()

      if self.is_valid_transition(index):
        indices.append(index)
      else:
        allowed_attempts -= 1

    if len(indices) != batch_size:
      raise Exception('Could only sample {} valid transitions'.format(
          len(indices)))
    else:
      return indices

  def set_priority(self, indices, priorities):
    pass                                                                 

         
                                                                   
                                                               
       
    assert indices.dtype == np.int32, ('Indices must be integers, '
                                       'given: {}'.format(indices.dtype))
    for i, memory_index in enumerate(indices):
      self.sum_tree.set(memory_index, priorities[i])

  def get_priority(self, indices, batch_size=None):
    pass                                                              

                                                                          

         
                                                                   
                                                 
            
                                   
       
    if batch_size is None:
      batch_size = self._batch_size
    if batch_size != self._state_batch.shape[0]:
      self.reset_state_batch_arrays(batch_size)

    priority_batch = np.empty((batch_size), dtype=np.float32)

    assert indices.dtype == np.int32, ('Indices must be integers, '
                                       'given: {}'.format(indices.dtype))
    for i, memory_index in enumerate(indices):
      priority_batch[i] = self.sum_tree.get(memory_index)

    return priority_batch


@gin.configurable(denylist=['observation_size', 'stack_size'])
class WrappedPrioritizedReplayMemory(replay_memory.WrappedReplayMemory):
  pass                                             

        
                                                             
                                                                              

                                                                        
                                                                             
                                                               

                                                                               
                                                      

                                                                            
                                              

             
                                                              
          
           
           
               
             

                                                                        
                                                                                
              
                 
                 
                   
     

  def __init__(self,
               num_actions,
               observation_size,
               stack_size,
               use_staging=True,
               replay_capacity=1000000,
               batch_size=32,
               update_horizon=1,
               gamma=1.0):
    pass                                                        

         
                                                   
                                                          
                                                              
                                                                          
                                
                                                                    
                      
                                                                   
                                      

           
                                                    
                                                      
       
    memory = OutOfGraphPrioritizedReplayMemory(num_actions, observation_size,
                                               stack_size, replay_capacity,
                                               batch_size, update_horizon,
                                               gamma)
    super(WrappedPrioritizedReplayMemory, self).__init__(
        num_actions,
        observation_size, stack_size, use_staging, replay_capacity, batch_size,
        update_horizon, gamma, wrapped_memory=memory)

  def tf_set_priority(self, indices, losses):
    pass                                         

         
                                                 
                                               

            
                                                                         
              
       
    return tf.py_func(
        self.memory.set_priority, [indices, losses],
        [],
        name='prioritized_replay_set_priority_py_func')

  def tf_get_priority(self, indices):
    pass                                         

         
                                                 

            
                                        
       
    return tf.py_func(
        self.memory.get_priority, [indices],
        [tf.float32],
        name='prioritized_replay_get_priority_py_func')
