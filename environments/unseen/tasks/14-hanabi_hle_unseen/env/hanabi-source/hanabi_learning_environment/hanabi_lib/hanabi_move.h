                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_MOVE_H__
#define __HANABI_MOVE_H__

#include <cstdint>
#include <string>

namespace hanabi_learning_env {

                    
                                              
                                                 
                                                                          
                                                                             
                                                                          
                                                     
                                
class HanabiMove {
                                                             
 public:
  enum Type { kInvalid, kPlay, kDiscard, kRevealColor, kRevealRank, kDeal };

  HanabiMove(Type move_type, int8_t card_index, int8_t target_offset,
             int8_t color, int8_t rank)
      : move_type_(move_type),
        card_index_(card_index),
        target_offset_(target_offset),
        color_(color),
        rank_(rank) {}
                                                         
  bool operator==(const HanabiMove& other_move) const;
  std::string ToString() const;

  Type MoveType() const { return move_type_; }
  bool IsValid() const { return move_type_ != kInvalid; }
  int8_t CardIndex() const { return card_index_; }
  int8_t TargetOffset() const { return target_offset_; }
  int8_t Color() const { return color_; }
  int8_t Rank() const { return rank_; }

 private:
  Type move_type_ = kInvalid;
  int8_t card_index_ = -1;
  int8_t target_offset_ = -1;
  int8_t color_ = -1;
  int8_t rank_ = -1;
};

}                                  

#endif
