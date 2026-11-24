                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#include "hanabi_move.h"

#include "util.h"

namespace hanabi_learning_env {

bool HanabiMove::operator==(const HanabiMove& other_move) const {
  if (MoveType() != other_move.MoveType()) {
    return false;
  }
  switch (MoveType()) {
    case kPlay:
    case kDiscard:
      return CardIndex() == other_move.CardIndex();
    case kRevealColor:
      return TargetOffset() == other_move.TargetOffset() &&
             Color() == other_move.Color();
    case kRevealRank:
      return TargetOffset() == other_move.TargetOffset() &&
             Rank() == other_move.Rank();
    case kDeal:
      return Color() == other_move.Color() && Rank() == other_move.Rank();
    default:
      return true;
  }
}

std::string HanabiMove::ToString() const {
  switch (MoveType()) {
    case kPlay:
      return "(Play " + std::to_string(CardIndex()) + ")";
    case kDiscard:
      return "(Discard " + std::to_string(CardIndex()) + ")";
    case kRevealColor:
      return "(Reveal player +" + std::to_string(TargetOffset()) + " color " +
             ColorIndexToChar(Color()) + ")";
    case kRevealRank:
      return "(Reveal player +" + std::to_string(TargetOffset()) + " rank " +
             RankIndexToChar(Rank()) + ")";
    case kDeal:
      if (color_ >= 0) {
        return std::string("(Deal ") + ColorIndexToChar(Color()) +
               RankIndexToChar(Rank()) + ")";
      } else {
        return std::string("(Deal XX)");
      }
    default:
      return "(INVALID)";
  }
}

}                                  
