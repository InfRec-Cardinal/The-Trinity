              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                                                           

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools

import dqn_agent
import gin.tf
import numpy as np
import prioritized_replay_memory
import tensorflow as tf


slim = tf.contrib.slim


@gin.configurable
def rainbow_template(state,
                     num_actions,
                     num_atoms=51,
                     layer_size=512,
                     num_layers=1):
  pass                                                               

       
                                               
                                                                   
                                                                         
                                                      
                                             

          
                                     
                                                                           
                             
     
  weights_initializer = slim.variance_scaling_initializer(
      factor=1.0 / np.sqrt(3.0), mode='FAN_IN', uniform=True)

  net = tf.cast(state, tf.float32)
  net = tf.squeeze(net, axis=2)

  for _ in range(num_layers):
    net = slim.fully_connected(net, layer_size,
                               activation_fn=tf.nn.relu)
  net = slim.fully_connected(net, num_actions * num_atoms, activation_fn=None,
                             weights_initializer=weights_initializer)
  net = tf.reshape(net, [-1, num_actions, num_atoms])
  return net


@gin.configurable
class RainbowAgent(dqn_agent.DQNAgent):
  pass                                                            

  @gin.configurable
  def __init__(self,
               num_actions=None,
               observation_size=None,
               num_players=None,
               num_atoms=51,
               vmax=25.,
               gamma=0.99,
               update_horizon=1,
               min_replay_history=500,
               update_period=4,
               target_update_period=500,
               epsilon_train=0.0,
               epsilon_eval=0.0,
               epsilon_decay_period=1000,
               learning_rate=0.000025,
               optimizer_epsilon=0.00003125,
               tf_device='/cpu:*'):
    pass                                              

         
                                                                          
                                                        
                                                            
                                                                                
                                                                    
                                                                          
                                                                             
                      
                                                                            
                                                     
                                                                      
                                                       
                                                     
                                                                      
                                                            
                                                           
                                                                     
       
                                                                     
    vmax = float(vmax)
    self.num_atoms = num_atoms
                                                                               
                                                         
    self.support = tf.linspace(-vmax, vmax, num_atoms)
    self.learning_rate = learning_rate
    self.optimizer_epsilon = optimizer_epsilon

    graph_template = functools.partial(rainbow_template, num_atoms=num_atoms)
    super(RainbowAgent, self).__init__(
        num_actions=num_actions,
        observation_size=observation_size,
        num_players=num_players,
        gamma=gamma,
        update_horizon=update_horizon,
        min_replay_history=min_replay_history,
        update_period=update_period,
        target_update_period=target_update_period,
        epsilon_train=epsilon_train,
        epsilon_eval=epsilon_eval,
        epsilon_decay_period=epsilon_decay_period,
        graph_template=graph_template,
        tf_device=tf_device)
    tf.logging.info('\t learning_rate: %f', learning_rate)
    tf.logging.info('\t optimizer_epsilon: %f', optimizer_epsilon)

  def _build_replay_memory(self, use_staging):
    pass                                           

                                    

         
                                                                            

            
                             
       
    return prioritized_replay_memory.WrappedPrioritizedReplayMemory(
        num_actions=self.num_actions,
        observation_size=self.observation_size,
        stack_size=1,
        use_staging=use_staging,
        update_horizon=self.update_horizon,
        gamma=self.gamma)

  def _reshape_networks(self):
                                                    
                                                  
    self._logits = self._q
                                                         
    self._probabilities = tf.contrib.layers.softmax(self._q)
                                 
    self._q = tf.reduce_sum(self.support * self._probabilities, axis=2)
                                                             
    self._q_argmax = tf.argmax(self._q + self.legal_actions_ph, axis=1)[0]

                                                         
    self._replay_logits = self._replay_qs
                                                              
    self._replay_next_logits = self._replay_next_qt
    del self._replay_qs
    del self._replay_next_qt

  def _build_target_distribution(self):
    self._reshape_networks()
    batch_size = tf.shape(self._replay.rewards)[0]
                                     
    rewards = self._replay.rewards[:, None]
                                                   
    tiled_support = tf.tile(self.support, [batch_size])
    tiled_support = tf.reshape(tiled_support, [batch_size, self.num_atoms])
                                                    

    is_terminal_multiplier = 1. - tf.cast(self._replay.terminals, tf.float32)
                                                    
                                                 
    gamma_with_terminal = self.cumulative_gamma * is_terminal_multiplier
    gamma_with_terminal = gamma_with_terminal[:, None]

    target_support = rewards + gamma_with_terminal * tiled_support
                                                                       
    next_probabilities = tf.contrib.layers.softmax(
        self._replay_next_logits)

                                      
    next_qt = tf.reduce_sum(self.support * next_probabilities, 2)
                                            
    next_qt_argmax = tf.argmax(
        next_qt + self._replay.next_legal_actions, axis=1)[:, None]
    batch_indices = tf.range(tf.to_int64(batch_size))[:, None]
                                            
    next_qt_argmax = tf.concat([batch_indices, next_qt_argmax], axis=1)
                                                        
    next_probabilities = tf.gather_nd(next_probabilities, next_qt_argmax)
    return project_distribution(target_support, next_probabilities,
                                self.support)

  def _build_train_op(self):
    pass                                  

            
                                                      
       
    target_distribution = tf.stop_gradient(self._build_target_distribution())

                                      
    indices = tf.range(tf.shape(self._replay_logits)[0])[:, None]
                                               
    reshaped_actions = tf.concat([indices, self._replay.actions[:, None]], 1)
                                                                              
    chosen_action_logits = tf.gather_nd(self._replay_logits, reshaped_actions)

    loss = tf.nn.softmax_cross_entropy_with_logits(
        labels=target_distribution,
        logits=chosen_action_logits)

    optimizer = tf.train.AdamOptimizer(
        learning_rate=self.learning_rate,
        epsilon=self.optimizer_epsilon)

    update_priorities_op = self._replay.tf_set_priority(
        self._replay.indices, tf.sqrt(loss + 1e-10))

    target_priorities = self._replay.tf_get_priority(self._replay.indices)
    target_priorities = tf.math.add(target_priorities, 1e-10)
    target_priorities = 1.0 / tf.sqrt(target_priorities)
    target_priorities /= tf.reduce_max(target_priorities)

    weighted_loss = target_priorities * loss

    with tf.control_dependencies([update_priorities_op]):
      return optimizer.minimize(tf.reduce_mean(weighted_loss)), weighted_loss


def project_distribution(supports, weights, target_support,
                         validate_args=False):
  pass                                                          

                                                    
                                    
                                                                           

                                                                              
                                                     
                                        
                                        
                                                  
                                                  
                                      
                                                                               
         

       
                                                                              
                   
                                                                           
                                                                          
                                                                  
                                                                                
                                                                              
                                                                       
                                                                     
                                                             
                               

          
                                                                              
                                           

         
                                                                              
                                                   
     
  target_support_deltas = target_support[1:] - target_support[:-1]
                                
  delta_z = target_support_deltas[0]
  validate_deps = []
  supports.shape.assert_is_compatible_with(weights.shape)
  supports[0].shape.assert_is_compatible_with(target_support.shape)
  target_support.shape.assert_has_rank(1)
  if validate_args:
                                                            
    validate_deps.append(
        tf.Assert(
            tf.reduce_all(tf.equal(tf.shape(supports), tf.shape(weights))),
            [supports, weights]))
                                                                              
    validate_deps.append(
        tf.Assert(
            tf.reduce_all(
                tf.equal(tf.shape(supports)[1], tf.shape(target_support))),
            [supports, target_support]))
                                                        
    validate_deps.append(
        tf.Assert(
            tf.equal(tf.size(tf.shape(target_support)), 1), [target_support]))
                                                                 
    validate_deps.append(
        tf.Assert(tf.reduce_all(target_support_deltas > 0), [target_support]))
                                                                  
    validate_deps.append(
        tf.Assert(
            tf.reduce_all(tf.equal(target_support_deltas, delta_z)),
            [target_support]))

  with tf.control_dependencies(validate_deps):
                                
    v_min, v_max = target_support[0], target_support[-1]
                           
    batch_size = tf.shape(supports)[0]
                 
                         
    num_dims = tf.shape(target_support)[0]
                                                                 
                                                     
                                                        
    clipped_support = tf.clip_by_value(supports, v_min, v_max)[:, None, :]
                                                   
                                                   
                                                   
                                                   
                                                    
                                                   
                                                   
                                                   
                                                   
                                                        
    tiled_support = tf.tile([clipped_support], [1, 1, num_dims, 1])
                                            
                                            
                                            
                                            
                                             
                                            
                                            
                                            
                                            
                                                
    reshaped_target_support = tf.tile(target_support[:, None], [batch_size, 1])
    reshaped_target_support = tf.reshape(reshaped_target_support,
                                         [batch_size, num_dims, 1])
                                                   
                                               
                                               
                                               
                                               
                                                
                                               
                                               
                                               
                                               
                                                    
    numerator = tf.abs(tiled_support - reshaped_target_support)
    quotient = 1 - (numerator / delta_z)
                                                                   
                                                      
                                                      
                                                      
                                                      
                                                       
                                                      
                                                      
                                                      
                                                      
                                                           
    clipped_quotient = tf.clip_by_value(quotient, 0, 1)
                                                
                                                   
    weights = weights[:, None, :]
                                                                         
             
                                                    
                                                    
                                                    
                                                    
                                                     
                                                    
                                                    
                                                    
                                                    
                                                         
    inner_prod = clipped_quotient * weights
                                               
                                                  
    projection = tf.reduce_sum(inner_prod, 3)
    projection = tf.reshape(projection, [batch_size, num_dims])
    return projection
