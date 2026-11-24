              
                                      
 
                                                                 
                                                                  
                                         
 
                                                 
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                  
   

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class IterationStatistics(object):
  pass                                              

                                                                              
                                                                   

                                                                         
                                                       

             
                                                                            
                      
     

  def __init__(self):
    self.data_lists = {}

  def append(self, data_pairs):
    pass                                                             

         
                                                                 
       
    for key, value in data_pairs.items():
      if key not in self.data_lists:
        self.data_lists[key] = []
      self.data_lists[key].append(value)
