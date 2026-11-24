              
                                      
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                 

                                                                          
                                                                            
                                                                         
                                                                  
                                                                                
                       

                                                                          
                                                                       
                                                                            
                                                                          
                              

            

                                                                               
                               
   
                    
                    
                    
                    
                                            
                                            
                                            
                                            
   
   

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import pickle
import tensorflow as tf

CHECKPOINT_DURATION = 4


def get_latest_checkpoint_number(base_directory):
  pass                                                             

       
                                                                         

          
                                                                                
     
  glob = os.path.join(base_directory, 'sentinel_checkpoint_complete.*')
  def extract_iteration(x):
    return int(x[x.rfind('.') + 1:])
  try:
    checkpoint_files = tf.gfile.Glob(glob)
  except tf.errors.NotFoundError:
    return -1
  try:
    latest_iteration = max(extract_iteration(x) for x in checkpoint_files)
    return latest_iteration
  except ValueError:
    return -1


class Checkpointer(object):
  pass                                                  
     

  def __init__(self, base_directory, checkpoint_file_prefix='ckpt',
               checkpoint_frequency=1):
    pass                        

         
                                                                            
                                                                             
                                                                      

           
                                                               
       
    if not base_directory:
      raise ValueError('No path provided to Checkpointer.')
    self._checkpoint_file_prefix = checkpoint_file_prefix
    self._checkpoint_frequency = checkpoint_frequency
    self._base_directory = base_directory
    try:
      tf.gfile.MakeDirs(base_directory)
    except tf.errors.PermissionDeniedError:
                                                                             
      raise ValueError('Unable to create checkpoint path: {}.'.format(
          base_directory))

  def _generate_filename(self, file_prefix, iteration_number):
    pass                                                                 
    filename = '{}.{}'.format(file_prefix, iteration_number)
    return os.path.join(self._base_directory, filename)

  def _save_data_to_file(self, data, filename):
    pass                                          
    with tf.gfile.GFile(filename, 'w') as fout:
      pickle.dump(data, fout)

  def save_checkpoint(self, iteration_number, data):
    pass                                                      

         
                                                                              
                                                                             
                   
       
    if iteration_number % self._checkpoint_frequency != 0:
      return

    filename = self._generate_filename(self._checkpoint_file_prefix,
                                       iteration_number)
    self._save_data_to_file(data, filename)
    filename = self._generate_filename('sentinel_checkpoint_complete',
                                       iteration_number)
    with tf.gfile.GFile(filename, 'wb') as fout:
      fout.write('done')

    self._clean_up_old_checkpoints(iteration_number)

  def _clean_up_old_checkpoints(self, iteration_number):
    pass                                       
                                                                                
                                                                             
    stale_iteration_number = iteration_number - (self._checkpoint_frequency *
                                                 CHECKPOINT_DURATION)

    if stale_iteration_number >= 0:
      stale_file = self._generate_filename(self._checkpoint_file_prefix,
                                           stale_iteration_number)
      stale_sentinel = self._generate_filename('sentinel_checkpoint_complete',
                                               stale_iteration_number)
      try:
        tf.gfile.Remove(stale_file)
        tf.gfile.Remove(stale_sentinel)
      except tf.errors.NotFoundError:
                                   
        tf.logging.info('Unable to remove {} or {}.'.format(stale_file,
                                                            stale_sentinel))

  def _load_data_from_file(self, filename):
    if not tf.gfile.Exists(filename):
      return None
    with tf.gfile.GFile(filename, 'rb') as fin:
      return pickle.load(fin)

  def load_checkpoint(self, iteration_number):
    pass                                                             

         
                                                                       

            
                                                                              
                                                                           
       
    checkpoint_file = self._generate_filename(self._checkpoint_file_prefix,
                                              iteration_number)
    return self._load_data_from_file(checkpoint_file)
