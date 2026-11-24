                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_CARD_H__
#define __HANABI_CARD_H__

#include <string>

namespace hanabi_learning_env {

class HanabiCard {
 public:
  HanabiCard(int color, int rank) : color_(color), rank_(rank) {}
  HanabiCard() = default;                            
  bool operator==(const HanabiCard& other_card) const;
  bool IsValid() const { return color_ >= 0 && rank_ >= 0; }
  std::string ToString() const;
  int Color() const { return color_; }
  int Rank() const { return rank_; }

 private:
  int color_ = -1;                          
  int rank_ = -1;                          
};

}                                  

#endif
