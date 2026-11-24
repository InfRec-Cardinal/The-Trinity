                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#include "hanabi_card.h"

#include "util.h"

namespace hanabi_learning_env {

bool HanabiCard::operator==(const HanabiCard& other_card) const {
  return other_card.Color() == Color() && other_card.Rank() == Rank();
}

std::string HanabiCard::ToString() const {
  if (!IsValid()) {
    return std::string("XX");
  }
  return std::string() + ColorIndexToChar(Color()) + RankIndexToChar(Rank());
}

}                                  
