                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_HAND_H__
#define __HANABI_HAND_H__

#include <cstdint>
#include <string>
#include <vector>

#include "hanabi_card.h"

namespace hanabi_learning_env {

class HanabiHand {
 public:
  class ValueKnowledge {
                                                                               
                                                                            
                                                                
                                                                               
                                                                           
                         
                                                       
                                                                  
                                                   
                                                                               
   public:
    explicit ValueKnowledge(int value_range);
    int Range() const { return value_plausible_.size(); }
                                                                
                                                                            
    bool ValueHinted() const { return value_ >= 0; }
    int Value() const { return value_; }                                
                                                                              
    bool IsPlausible(int value) const { return value_plausible_[value]; }
                                                          
    void ApplyIsValueHint(int value);
                                                                     
    void ApplyIsNotValueHint(int value);

   private:
                                                                            
    int value_ = -1;
    std::vector<bool> value_plausible_;                                    
  };

  class CardKnowledge {
                                                                          
   public:
    CardKnowledge(int num_colors, int num_ranks);
                                                       
    int NumColors() const { return color_.Range(); }
                                                                
                                                                            
    bool ColorHinted() const { return color_.ValueHinted(); }
                                                        
    int Color() const { return color_.Value(); }
                                                                          
    bool ColorPlausible(int color) const { return color_.IsPlausible(color); }
    void ApplyIsColorHint(int color) { color_.ApplyIsValueHint(color); }
    void ApplyIsNotColorHint(int color) { color_.ApplyIsNotValueHint(color); }
                                                      
    int NumRanks() const { return rank_.Range(); }
                                                               
                                                                          
    bool RankHinted() const { return rank_.ValueHinted(); }
                                                       
    int Rank() const { return rank_.Value(); }
                                                                         
    bool RankPlausible(int rank) const { return rank_.IsPlausible(rank); }
    void ApplyIsRankHint(int rank) { rank_.ApplyIsValueHint(rank); }
    void ApplyIsNotRankHint(int rank) { rank_.ApplyIsNotValueHint(rank); }
    std::string ToString() const;

   private:
    ValueKnowledge color_;
    ValueKnowledge rank_;
  };

  HanabiHand() {}
  HanabiHand(const HanabiHand& hand)
      : cards_(hand.cards_), card_knowledge_(hand.card_knowledge_) {}
                                                                  
                                                                    
  HanabiHand(const HanabiHand& hand, bool hide_cards, bool hide_knowledge);
                                                                              
                                                          
  const std::vector<HanabiCard>& Cards() const { return cards_; }
  const std::vector<CardKnowledge>& Knowledge() const {
    return card_knowledge_;
  }
  void AddCard(HanabiCard card, const CardKnowledge& initial_knowledge);
                                                                         
                                                              
  void RemoveFromHand(int card_index, std::vector<HanabiCard>* discard_pile);
                                            
                                                                            
                                
  uint8_t RevealRank(int rank);
                                             
                                                                            
                                
  uint8_t RevealColor(int color);
  std::string ToString() const;

 private:
                                             
  std::vector<HanabiCard> cards_;
  std::vector<CardKnowledge> card_knowledge_;
};

}                                  

#endif
