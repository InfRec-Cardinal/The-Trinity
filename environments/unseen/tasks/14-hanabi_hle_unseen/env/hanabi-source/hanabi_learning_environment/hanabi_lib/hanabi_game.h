                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_GAME_H__
#define __HANABI_GAME_H__

#include <random>
#include <string>
#include <unordered_map>
#include <vector>

#include "hanabi_card.h"
#include "hanabi_move.h"

namespace hanabi_learning_env {

class HanabiGame {
 public:
                                                                        
                                                                  
                                                                         
                                                                            
                                                                             
                                                                         
                                                                              
                                                                          
                           
  enum AgentObservationType { kMinimal = 0, kCardKnowledge = 1, kSeer = 2 };

                           
    
                                                  
                                                       
                                                        
                                            
                                              
                                            
                                                                             
                                                                                
                                                                  
                                                              
                                                                         
                        
                                                                              
                                                                 
  explicit HanabiGame(
      const std::unordered_map<std::string, std::string>& params);

                                      
  int MaxMoves() const;
                                   
  HanabiMove GetMove(int uid) const { return moves_[uid]; }
                                                           
  int GetMoveUid(HanabiMove move) const;
  int GetMoveUid(HanabiMove::Type move_type, int card_index, int target_offset,
                 int color, int rank) const;
                                         
  int MaxChanceOutcomes() const;
                                                  
  HanabiMove GetChanceOutcome(int uid) const { return chance_outcomes_[uid]; }
                                                                          
  int GetChanceOutcomeUid(HanabiMove move) const;
                                                                        
                                         
  HanabiMove PickRandomChance(
      const std::pair<std::vector<HanabiMove>, std::vector<double>>&
          chance_outcomes) const;

  std::unordered_map<std::string, std::string> Parameters() const;
  int MinPlayers() const { return 2; }
  int MaxPlayers() const { return 5; }
  int MinScore() const { return 0; }
  int MaxScore() const { return num_ranks_ * num_colors_; }
  std::string Name() const { return "Hanabi"; }

  int NumColors() const { return num_colors_; }
  int NumRanks() const { return num_ranks_; }
  int NumPlayers() const { return num_players_; }
  int HandSize() const { return hand_size_; }
  int MaxInformationTokens() const { return max_information_tokens_; }
  int MaxLifeTokens() const { return max_life_tokens_; }
  int CardsPerColor() const { return cards_per_color_; }
  int MaxDeckSize() const { return cards_per_color_ * num_colors_; }
  int NumberCardInstances(int color, int rank) const;
  int NumberCardInstances(HanabiCard card) const {
    return NumberCardInstances(card.Color(), card.Rank());
  }
  AgentObservationType ObservationType() const { return observation_type_; }

                                                                           
  int GetSampledStartPlayer() const;

 private:
                                        
  int MaxDiscardMoves() const { return hand_size_; }
  int MaxPlayMoves() const { return hand_size_; }
  int MaxRevealColorMoves() const { return (num_players_ - 1) * num_colors_; }
  int MaxRevealRankMoves() const { return (num_players_ - 1) * num_ranks_; }

  int HandSizeFromRules() const;
  HanabiMove ConstructMove(int uid) const;
  HanabiMove ConstructChanceOutcome(int uid) const;

                                              
  std::vector<HanabiMove> moves_;
                                                        
  std::vector<HanabiMove> chance_outcomes_;
  std::unordered_map<std::string, std::string> params_;
  int num_colors_ = -1;
  int num_ranks_ = -1;
  int num_players_ = -1;
  int hand_size_ = -1;
  int max_information_tokens_ = -1;
  int max_life_tokens_ = -1;
  int cards_per_color_ = -1;
  int seed_ = -1;
  bool random_start_player_ = false;
  AgentObservationType observation_type_ = kCardKnowledge;
  mutable std::mt19937 rng_;
};

}                                  

#endif
