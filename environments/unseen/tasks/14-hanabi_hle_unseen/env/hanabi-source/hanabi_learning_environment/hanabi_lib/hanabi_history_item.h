                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_HISTORY_ITEM_H__
#define __HANABI_HISTORY_ITEM_H__

#include <cstdint>
#include <string>

#include "hanabi_move.h"

namespace hanabi_learning_env {

                                                                              
                       
struct HanabiHistoryItem {
  explicit HanabiHistoryItem(HanabiMove move_made) : move(move_made) {}
  HanabiHistoryItem(const HanabiHistoryItem& past_move) = default;
  std::string ToString() const;

                        
  HanabiMove move;
                                       
  int8_t player = -1;
                                                     
  bool scored = false;
                                                                        
  bool information_token = false;
                                                                      
  int8_t color = -1;
                                                                    
  int8_t rank = -1;
                                                                      
                                                                 
                                                                  
                                                      
  uint8_t reveal_bitmask = 0;
                                                                            
                                                                       
                                                                      
                                                                         
                                                               
  uint8_t newly_revealed_bitmask = 0;
                                                  
  int8_t deal_to_player = -1;
};

}                                  

#endif
