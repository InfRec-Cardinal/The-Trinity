                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

                                                                          
                                                                  

#ifndef __CANONICAL_ENCODERS_H__
#define __CANONICAL_ENCODERS_H__

#include <vector>

#include "hanabi_game.h"
#include "hanabi_observation.h"
#include "observation_encoder.h"

namespace hanabi_learning_env {

                                              
class CanonicalObservationEncoder : public ObservationEncoder {
 public:
  explicit CanonicalObservationEncoder(const HanabiGame* parent_game)
      : parent_game_(parent_game) {}

  std::vector<int> Shape() const override;
  std::vector<int> Encode(const HanabiObservation& obs) const override;

  ObservationEncoder::Type type() const override {
    return ObservationEncoder::Type::kCanonical;
  }

 private:
  const HanabiGame* parent_game_ = nullptr;
};

}                                  

#endif
