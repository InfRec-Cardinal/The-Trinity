                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_OBSERVATION_H__
#define __HANABI_OBSERVATION_H__

#include <string>
#include <vector>

#include "hanabi_card.h"
#include "hanabi_game.h"
#include "hanabi_hand.h"
#include "hanabi_history_item.h"
#include "hanabi_move.h"
#include "hanabi_state.h"

namespace hanabi_learning_env {

                                     
class HanabiObservation {
 public:
  HanabiObservation(const HanabiState& state, int observing_player);

  std::string ToString() const;

                                                    
  int CurPlayerOffset() const { return cur_player_offset_; }
                                                                 
                                                                  
                                                        
  const std::vector<HanabiHand>& Hands() const { return hands_; }
                                                        
  const std::vector<HanabiCard>& DiscardPile() const { return discard_pile_; }
  const std::vector<int>& Fireworks() const { return fireworks_; }
  int DeckSize() const { return deck_size_; }                              
  const HanabiGame* ParentGame() const { return parent_game_; }
                                                                           
                                                      
                                                                     
                                                          
  const std::vector<HanabiHistoryItem>& LastMoves() const {
    return last_moves_;
  }
  int InformationTokens() const { return information_tokens_; }
  int LifeTokens() const { return life_tokens_; }
  const std::vector<HanabiMove>& LegalMoves() const { return legal_moves_; }

                                                                             
  bool CardPlayableOnFireworks(int color, int rank) const;
  bool CardPlayableOnFireworks(HanabiCard card) const {
    return CardPlayableOnFireworks(card.Color(), card.Rank());
  }

 private:
  int cur_player_offset_;                                                   
  std::vector<HanabiHand> hands_;                                         
  std::vector<HanabiCard> discard_pile_;                                
  std::vector<int> fireworks_;
  int deck_size_;
  std::vector<HanabiHistoryItem> last_moves_;
  int information_tokens_;
  int life_tokens_;
  std::vector<HanabiMove> legal_moves_;                        
  const HanabiGame* parent_game_ = nullptr;
};

}                                  

#endif
