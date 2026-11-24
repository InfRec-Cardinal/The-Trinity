                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __HANABI_STATE_H__
#define __HANABI_STATE_H__

#include <random>
#include <string>
#include <vector>

#include "hanabi_card.h"
#include "hanabi_game.h"
#include "hanabi_hand.h"
#include "hanabi_history_item.h"
#include "hanabi_move.h"

namespace hanabi_learning_env {

constexpr int kChancePlayerId = -1;

class HanabiState {
 public:
  class HanabiDeck {
   public:
    explicit HanabiDeck(const HanabiGame& game);
                                                
    HanabiCard DealCard(int color, int rank);
    HanabiCard DealCard(std::mt19937* rng);
    int Size() const { return total_count_; }
    bool Empty() const { return total_count_ == 0; }
    int CardCount(int color, int rank) const {
      return card_count_[CardToIndex(color, rank)];
    }

   private:
    int CardToIndex(int color, int rank) const {
      return color * num_ranks_ + rank;
    }
    int IndexToColor(int index) const { return index / num_ranks_; }
    int IndexToRank(int index) const { return index % num_ranks_; }

                                                     
                                                                       
                                                                          
    std::vector<int> card_count_;
    int total_count_ = -1;                                                     
    int num_ranks_ = -1;                                                       
  };

  enum EndOfGameType {
    kNotFinished,                               
    kOutOfLifeTokens,                                      
    kOutOfCards,                                     
    kCompletedFireworks                          
  };

                                                                   
                                                                       
                                                       
  explicit HanabiState(HanabiGame* parent_game, int start_player = -1);
                                                                            
  HanabiState(const HanabiState& state) = default;

  bool MoveIsLegal(HanabiMove move) const;
  void ApplyMove(HanabiMove move);
                                                                               
  std::vector<HanabiMove> LegalMoves(int player) const;
                                                                              
  bool CardPlayableOnFireworks(int color, int rank) const;
  bool CardPlayableOnFireworks(HanabiCard card) const {
    return CardPlayableOnFireworks(card.Color(), card.Rank());
  }
  bool ChanceOutcomeIsLegal(HanabiMove move) const { return MoveIsLegal(move); }
  double ChanceOutcomeProb(HanabiMove move) const;
  void ApplyChanceOutcome(HanabiMove move) { ApplyMove(move); }
  void ApplyRandomChance();
                                                              
                                                          
  std::pair<std::vector<HanabiMove>, std::vector<double>> ChanceOutcomes()
      const;
  EndOfGameType EndOfGameStatus() const;
  bool IsTerminal() const { return EndOfGameStatus() != kNotFinished; }
  int Score() const;
  std::string ToString() const;

  int CurPlayer() const { return cur_player_; }
  int LifeTokens() const { return life_tokens_; }
  int InformationTokens() const { return information_tokens_; }
  const std::vector<HanabiHand>& Hands() const { return hands_; }
  const std::vector<int>& Fireworks() const { return fireworks_; }
  HanabiGame* ParentGame() const { return parent_game_; }
  const HanabiDeck& Deck() const { return deck_; }
                                                                               
  const std::vector<HanabiCard>& DiscardPile() const { return discard_pile_; }
                                                                       
  const std::vector<HanabiHistoryItem>& MoveHistory() const {
    return move_history_;
  }

 private:
                                                             
                                             
                                                                  
                                                                    
                                                                         
  std::pair<bool, bool> AddToFireworks(HanabiCard card);
  const HanabiHand& HandByOffset(int offset) const {
    return hands_[(cur_player_ + offset) % hands_.size()];
  }
  HanabiHand* HandByOffset(int offset) {
    return &hands_[(cur_player_ + offset) % hands_.size()];
  }
  void AdvanceToNextPlayer();                                          
  bool HintingIsLegal(HanabiMove move) const;
  int PlayerToDeal() const;                                  
  bool IncrementInformationTokens();
  void DecrementInformationTokens();
  void DecrementLifeTokens();

  HanabiGame* parent_game_ = nullptr;
  HanabiDeck deck_;
                                                                   
  std::vector<HanabiCard> discard_pile_;
  std::vector<HanabiHand> hands_;
  std::vector<HanabiHistoryItem> move_history_;
  int cur_player_ = -1;
  int next_non_chance_player_ = -1;                                   
  int information_tokens_ = -1;
  int life_tokens_ = -1;
  std::vector<int> fireworks_;
  int turns_to_play_ = -1;                                                
};

}                                  

#endif
