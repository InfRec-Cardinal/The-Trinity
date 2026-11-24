                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>

#include "canonical_encoders.h"

namespace hanabi_learning_env {

namespace {

                                                                        
                                                   
int FlatLength(const std::vector<int>& shape) {
  return std::accumulate(std::begin(shape), std::end(shape), 1,
                         std::multiplies<int>());
}

const HanabiHistoryItem* GetLastNonDealMove(
    const std::vector<HanabiHistoryItem>& past_moves) {
  auto it = std::find_if(
      past_moves.begin(), past_moves.end(), [](const HanabiHistoryItem& item) {
        return item.move.MoveType() != HanabiMove::Type::kDeal;
      });
  return it == past_moves.end() ? nullptr : &(*it);
}

int BitsPerCard(const HanabiGame& game) {
  return game.NumColors() * game.NumRanks();
}

                                                         
int CardIndex(int color, int rank, int num_ranks) {
  return color * num_ranks + rank;
}

int HandsSectionLength(const HanabiGame& game) {
  return (game.NumPlayers() - 1) * game.HandSize() * BitsPerCard(game) +
         game.NumPlayers();
}

                                                                          
                                                                               
                                                                     
                                                                         
                                                         
int EncodeHands(const HanabiGame& game, const HanabiObservation& obs,
                int start_offset, std::vector<int>* encoding) {
  int bits_per_card = BitsPerCard(game);
  int num_ranks = game.NumRanks();
  int num_players = game.NumPlayers();
  int hand_size = game.HandSize();

  int offset = start_offset;
  const std::vector<HanabiHand>& hands = obs.Hands();
  assert(hands.size() == num_players);
  for (int player = 1; player < num_players; ++player) {
    const std::vector<HanabiCard>& cards = hands[player].Cards();
    int num_cards = 0;

    for (const HanabiCard& card : cards) {
                                                             
      assert(card.IsValid());
      assert(card.Color() < game.NumColors());
      assert(card.Rank() < num_ranks);
      (*encoding)[offset + CardIndex(card.Color(), card.Rank(), num_ranks)] = 1;

      ++num_cards;
      offset += bits_per_card;
    }

                                                                       
                                                                           
                                   
    if (num_cards < hand_size) {
      offset += (hand_size - num_cards) * bits_per_card;
    }
  }

                                                                
  for (int player = 0; player < num_players; ++player) {
    if (hands[player].Cards().size() < game.HandSize()) {
      (*encoding)[offset + player] = 1;
    }
  }
  offset += num_players;

  assert(offset - start_offset == HandsSectionLength(game));
  return offset - start_offset;
}

int BoardSectionLength(const HanabiGame& game) {
  return game.MaxDeckSize() - game.NumPlayers() * game.HandSize() +         
         game.NumColors() * game.NumRanks() +              
         game.MaxInformationTokens() +                       
         game.MaxLifeTokens();                               
}

                               
                          
                                                                  
                                                                   
                                                                              
                                                                
                                                                                
                                                                         
                                                         
int EncodeBoard(const HanabiGame& game, const HanabiObservation& obs,
                int start_offset, std::vector<int>* encoding) {
  int num_colors = game.NumColors();
  int num_ranks = game.NumRanks();
  int num_players = game.NumPlayers();
  int hand_size = game.HandSize();
  int max_deck_size = game.MaxDeckSize();

  int offset = start_offset;
                         
  for (int i = 0; i < obs.DeckSize(); ++i) {
    (*encoding)[offset + i] = 1;
  }
  offset += (max_deck_size - hand_size * num_players);                         

              
  const std::vector<int>& fireworks = obs.Fireworks();
  for (int c = 0; c < num_colors; ++c) {
                                                                           
                                                                              
    if (fireworks[c] > 0) {
      (*encoding)[offset + fireworks[c] - 1] = 1;
    }
    offset += num_ranks;
  }

                
  assert(obs.InformationTokens() >= 0);
  assert(obs.InformationTokens() <= game.MaxInformationTokens());
  for (int i = 0; i < obs.InformationTokens(); ++i) {
    (*encoding)[offset + i] = 1;
  }
  offset += game.MaxInformationTokens();

                
  assert(obs.LifeTokens() >= 0);
  assert(obs.LifeTokens() <= game.MaxLifeTokens());
  for (int i = 0; i < obs.LifeTokens(); ++i) {
    (*encoding)[offset + i] = 1;
  }
  offset += game.MaxLifeTokens();

  assert(offset - start_offset == BoardSectionLength(game));
  return offset - start_offset;
}

int DiscardSectionLength(const HanabiGame& game) { return game.MaxDeckSize(); }

                                                
                                                                            
                                                                      
                                                                               
                                                                         
                   
  
               
               
  
                             
                                                     
                                                         
                                                        
                                                         
                                               
                                                         
int EncodeDiscards(const HanabiGame& game, const HanabiObservation& obs,
                   int start_offset, std::vector<int>* encoding) {
  int num_colors = game.NumColors();
  int num_ranks = game.NumRanks();

  int offset = start_offset;
  std::vector<int> discard_counts(num_colors * num_ranks, 0);
  for (const HanabiCard& card : obs.DiscardPile()) {
    ++discard_counts[card.Color() * num_ranks + card.Rank()];
  }

  for (int c = 0; c < num_colors; ++c) {
    for (int r = 0; r < num_ranks; ++r) {
      int num_discarded = discard_counts[c * num_ranks + r];
      for (int i = 0; i < num_discarded; ++i) {
        (*encoding)[offset + i] = 1;
      }
      offset += game.NumberCardInstances(c, r);
    }
  }

  assert(offset - start_offset == DiscardSectionLength(game));
  return offset - start_offset;
}

int LastActionSectionLength(const HanabiGame& game) {
  return game.NumPlayers() +              
         4 +                                                              
         game.NumPlayers() +                                      
         game.NumColors() +                            
         game.NumRanks() +                            
         game.HandSize() +                               
         game.HandSize() +                                
         BitsPerCard(game) +                                     
         2;                                                                
}

                                                                            
                                                                            
                                    
                                                                      
                                   
                                                                         
                                                                      
                                                                                
                                                           
                                                                      
                                                         
int EncodeLastAction(const HanabiGame& game, const HanabiObservation& obs,
                     int start_offset, std::vector<int>* encoding) {
  int num_colors = game.NumColors();
  int num_ranks = game.NumRanks();
  int num_players = game.NumPlayers();
  int hand_size = game.HandSize();

  int offset = start_offset;
  const HanabiHistoryItem* last_move = GetLastNonDealMove(obs.LastMoves());
  if (last_move == nullptr) {
    offset += LastActionSectionLength(game);
  } else {
    HanabiMove::Type last_move_type = last_move->move.MoveType();

                
                                                                               
                             
    (*encoding)[offset + last_move->player] = 1;
    offset += num_players;

                
    switch (last_move_type) {
      case HanabiMove::Type::kPlay:
        (*encoding)[offset] = 1;
        break;
      case HanabiMove::Type::kDiscard:
        (*encoding)[offset + 1] = 1;
        break;
      case HanabiMove::Type::kRevealColor:
        (*encoding)[offset + 2] = 1;
        break;
      case HanabiMove::Type::kRevealRank:
        (*encoding)[offset + 3] = 1;
        break;
      default:
        std::abort();
    }
    offset += 4;

                                     
    if (last_move_type == HanabiMove::Type::kRevealColor ||
        last_move_type == HanabiMove::Type::kRevealRank) {
      int8_t observer_relative_target =
          (last_move->player + last_move->move.TargetOffset()) % num_players;
      (*encoding)[offset + observer_relative_target] = 1;
    }
    offset += num_players;

                             
    if (last_move_type == HanabiMove::Type::kRevealColor) {
      (*encoding)[offset + last_move->move.Color()] = 1;
    }
    offset += num_colors;

                            
    if (last_move_type == HanabiMove::Type::kRevealRank) {
      (*encoding)[offset + last_move->move.Rank()] = 1;
    }
    offset += num_ranks;

                                 
    if (last_move_type == HanabiMove::Type::kRevealColor ||
        last_move_type == HanabiMove::Type::kRevealRank) {
      for (int i = 0, mask = 1; i < hand_size; ++i, mask <<= 1) {
        if ((last_move->reveal_bitmask & mask) > 0) {
          (*encoding)[offset + i] = 1;
        }
      }
    }
    offset += hand_size;

                                           
    if (last_move_type == HanabiMove::Type::kPlay ||
        last_move_type == HanabiMove::Type::kDiscard) {
      (*encoding)[offset + last_move->move.CardIndex()] = 1;
    }
    offset += hand_size;

                                       
    if (last_move_type == HanabiMove::Type::kPlay ||
        last_move_type == HanabiMove::Type::kDiscard) {
      assert(last_move->color >= 0);
      assert(last_move->rank >= 0);
      (*encoding)[offset +
                  CardIndex(last_move->color, last_move->rank, num_ranks)] = 1;
    }
    offset += BitsPerCard(game);

                                                                     
    if (last_move_type == HanabiMove::Type::kPlay) {
      if (last_move->scored) {
        (*encoding)[offset] = 1;
      }
      if (last_move->information_token) {
        (*encoding)[offset + 1] = 1;
      }
    }
    offset += 2;
  }

  assert(offset - start_offset == LastActionSectionLength(game));
  return offset - start_offset;
}

int CardKnowledgeSectionLength(const HanabiGame& game) {
  return game.NumPlayers() * game.HandSize() *
         (BitsPerCard(game) + game.NumColors() + game.NumRanks());
}

                                    
                                                                                
                                                                           
                                                                          
                                                                             
                                                                             
                                                                
                        
                                                             
                                                             
                                                          
  
                                                                                
                                                              
                        
                                                                      
                                                           
                                                          
                                     
                                                                  
                                                         
int EncodeCardKnowledge(const HanabiGame& game, const HanabiObservation& obs,
                        int start_offset, std::vector<int>* encoding) {
  int bits_per_card = BitsPerCard(game);
  int num_colors = game.NumColors();
  int num_ranks = game.NumRanks();
  int num_players = game.NumPlayers();
  int hand_size = game.HandSize();

  int offset = start_offset;
  const std::vector<HanabiHand>& hands = obs.Hands();
  assert(hands.size() == num_players);
  for (int player = 0; player < num_players; ++player) {
    const std::vector<HanabiHand::CardKnowledge>& knowledge =
        hands[player].Knowledge();
    int num_cards = 0;

    for (const HanabiHand::CardKnowledge& card_knowledge : knowledge) {
                                     
      for (int color = 0; color < num_colors; ++color) {
        if (card_knowledge.ColorPlausible(color)) {
          for (int rank = 0; rank < num_ranks; ++rank) {
            if (card_knowledge.RankPlausible(rank)) {
              (*encoding)[offset + CardIndex(color, rank, num_ranks)] = 1;
            }
          }
        }
      }
      offset += bits_per_card;

                                                           
      if (card_knowledge.ColorHinted()) {
        (*encoding)[offset + card_knowledge.Color()] = 1;
      }
      offset += num_colors;
      if (card_knowledge.RankHinted()) {
        (*encoding)[offset + card_knowledge.Rank()] = 1;
      }
      offset += num_ranks;

      ++num_cards;
    }

                                                                       
                                                                           
                                   
    if (num_cards < hand_size) {
      offset +=
          (hand_size - num_cards) * (bits_per_card + num_colors + num_ranks);
    }
  }

  assert(offset - start_offset == CardKnowledgeSectionLength(game));
  return offset - start_offset;
}

}              

std::vector<int> CanonicalObservationEncoder::Shape() const {
  return {HandsSectionLength(*parent_game_) +
          BoardSectionLength(*parent_game_) +
          DiscardSectionLength(*parent_game_) +
          LastActionSectionLength(*parent_game_) +
          (parent_game_->ObservationType() == HanabiGame::kMinimal
               ? 0
               : CardKnowledgeSectionLength(*parent_game_))};
}

std::vector<int> CanonicalObservationEncoder::Encode(
    const HanabiObservation& obs) const {
                                                 
  std::vector<int> encoding(FlatLength(Shape()), 0);

                                                                            
                                                  
  int offset = 0;
  offset += EncodeHands(*parent_game_, obs, offset, &encoding);
  offset += EncodeBoard(*parent_game_, obs, offset, &encoding);
  offset += EncodeDiscards(*parent_game_, obs, offset, &encoding);
  offset += EncodeLastAction(*parent_game_, obs, offset, &encoding);
  if (parent_game_->ObservationType() != HanabiGame::kMinimal) {
    offset += EncodeCardKnowledge(*parent_game_, obs, offset, &encoding);
  }

  assert(offset == encoding.size());
  return encoding;
}

}                                  
