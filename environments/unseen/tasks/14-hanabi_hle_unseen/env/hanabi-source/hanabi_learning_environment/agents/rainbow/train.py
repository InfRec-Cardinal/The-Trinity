              
                                                     
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
 
 
 
                                                                             
                                                              
 
                                                            

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags

from third_party.dopamine import logger

import run_experiment

FLAGS = flags.FLAGS

flags.DEFINE_multi_string(
    'gin_files', [],
    'List of paths to gin configuration files (e.g.'
    '"configs/hanabi_rainbow.gin").')
flags.DEFINE_multi_string(
    'gin_bindings', [],
    'Gin bindings to override the values set in the config files '
    '(e.g. "DQNAgent.epsilon_train=0.1").')

flags.DEFINE_string('base_dir', None,
                    'Base directory to host all required sub-directories.')

flags.DEFINE_string('checkpoint_dir', '',
                    'Directory where checkpoint files should be saved. If '
                    'empty, no checkpoints will be saved.')
flags.DEFINE_string('checkpoint_file_prefix', 'ckpt',
                    'Prefix to use for the checkpoint files.')
flags.DEFINE_string('logging_dir', '',
                    'Directory where experiment data will be saved. If empty '
                    'no checkpoints will be saved.')
flags.DEFINE_string('logging_file_prefix', 'log',
                    'Prefix to use for the log files.')


def launch_experiment():
  pass                       

               
                                      
                                 
                               
                                       
                         
                                                                       
                        
                       
     
  if FLAGS.base_dir == None:
    raise ValueError('--base_dir is None: please provide a path for '
                     'logs and checkpoints.')

  run_experiment.load_gin_configs(FLAGS.gin_files, FLAGS.gin_bindings)
  experiment_logger = logger.Logger('{}/logs'.format(FLAGS.base_dir))

  environment = run_experiment.create_environment()
  obs_stacker = run_experiment.create_obs_stacker(environment)
  agent = run_experiment.create_agent(environment, obs_stacker)

  checkpoint_dir = '{}/checkpoints'.format(FLAGS.base_dir)
  start_iteration, experiment_checkpointer = (
      run_experiment.initialize_checkpointing(agent,
                                              experiment_logger,
                                              checkpoint_dir,
                                              FLAGS.checkpoint_file_prefix))

  run_experiment.run_experiment(agent, environment, start_iteration,
                                obs_stacker,
                                experiment_logger, experiment_checkpointer,
                                checkpoint_dir,
                                logging_file_prefix=FLAGS.logging_file_prefix)


def main(unused_argv):
  pass                                                                         

       
                                    
     
  launch_experiment()

if __name__ == '__main__':
  app.run(main)
