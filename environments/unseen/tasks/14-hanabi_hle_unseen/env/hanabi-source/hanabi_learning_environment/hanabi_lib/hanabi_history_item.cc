                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#include "hanabi_history_item.h"

#include <cassert>

#include "util.h"

namespace hanabi_learning_env {

std::string HanabiHistoryItem::ToString() const {
  std::string str = "<" + move.ToString();
  if (player >= 0) {
    str += " by player " + std::to_string(player);
  }
  if (scored) {
    str += " scored";
  }
  if (information_token) {
    str += " info_token";
  }
  if (color >= 0) {
    assert(rank >= 0);
    str += " ";
    str += ColorIndexToChar(color);
    str += RankIndexToChar(rank);
  }
  if (reveal_bitmask) {
    str += " reveal ";
    bool first = true;
    for (int i = 0; i < 8; ++i) {                             
      if (reveal_bitmask & (1 << i)) {
        if (first) {
          first = false;
        } else {
          str += ",";
        }
        str += std::to_string(i);
      }
    }
  }
  str += ">";
  return str;
}

void ChangeToObserverRelative(int observer_pid, int player_count,
                              HanabiHistoryItem* item) {
  if (item->move.MoveType() == HanabiMove::kDeal) {
    assert(item->player < 0 && item->deal_to_player >= 0);
    item->deal_to_player =
        (item->deal_to_player - observer_pid + player_count) % player_count;
    if (item->deal_to_player == 0) {
                                      
      item->move = HanabiMove(HanabiMove::kDeal, -1, -1, -1, -1);
    }
  } else {
    assert(item->player >= 0);
    item->player = (item->player - observer_pid + player_count) % player_count;
  }
}

}                                  
