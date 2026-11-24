                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

                                                                   
                  

#ifndef __OBSERVATION_ENCODER_H__
#define __OBSERVATION_ENCODER_H__

#include <vector>

#include "hanabi_observation.h"

namespace hanabi_learning_env {

class ObservationEncoder {
 public:
  enum Type { kCanonical = 0 };
  virtual ~ObservationEncoder() = default;

                                                       
  virtual std::vector<int> Shape() const = 0;

                                                                           
                                                                            
  virtual std::vector<int> Encode(const HanabiObservation& obs) const = 0;

                                     
  virtual Type type() const = 0;
};

}                                  

#endif
