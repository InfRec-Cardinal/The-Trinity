                           
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                      
import os
import re
import cffi
import enum
import sys

DEFAULT_CDEF_PREFIXES = (None, ".", os.path.dirname(__file__), "/include")
DEFAULT_LIB_PREFIXES = (None, ".", os.path.dirname(__file__), "/lib")
PYHANABI_HEADER = "pyhanabi.h"
PYHANABI_LIB = ["libpyhanabi.so", "libpyhanabi.dylib"]
COLOR_CHAR = ["R", "Y", "G", "W", "B"]                                      
CHANCE_PLAYER_ID = -1

ffi = cffi.FFI()
lib = None
cdef_loaded_flag = False
lib_loaded_flag = False


if sys.version_info < (3,):
  def encode_ffi_string(x):
    return ffi.string(x)
else:
  def encode_ffi_string(x):
    return str(ffi.string(x), 'ascii')

def try_cdef(header=PYHANABI_HEADER, prefixes=DEFAULT_CDEF_PREFIXES):
  pass                                                                         

       
                                             
                                                               
          
                                                             
     
  global cdef_loaded_flag
  if cdef_loaded_flag: return True
  for prefix in prefixes:
    try:
      cdef_file = header if prefix is None else prefix + "/" + header
      lines = open(cdef_file).readlines()
      reading_cdef = False
      cdef_string = ""
      for line in lines:
        line = line.rstrip()
        if re.match("extern *\"C\" *{", line):
          reading_cdef = True
          continue
        elif re.match("} */[*] *extern *\"C\" *[*]/", line):
          reading_cdef = False
          continue
        if reading_cdef:
          cdef_string = cdef_string + line + "\n"
      ffi.cdef(cdef_string)
      cdef_loaded_flag = True
      return True
    except IOError:
      pass
  return False


def try_load(library=None, prefixes=DEFAULT_LIB_PREFIXES):
  pass                                                             

       
                                               
                                                                
          
                                                              
     
  global lib_loaded_flag
  global lib
  if lib_loaded_flag: return True
  if library is None:
    libnames = PYHANABI_LIB
  elif type(library) in (list, tuple):
    libnames = library
  else:
    libnames = (library,)
  for prefix in prefixes:
    for libname in libnames:
      try:
        lib_file = libname if prefix is None else prefix + "/" + libname
        lib = ffi.dlopen(lib_file)
        lib_loaded_flag = True
        return True
      except OSError:
        pass
  return False


def cdef_loaded():
  pass                                                              
  return cdef_loaded_flag


def lib_loaded():
  pass                                                               
  return lib_loaded_flag


def color_idx_to_char(color_idx):
  pass                                                         

       
                                                 

          
                                                             

         
                                             
     
  assert isinstance(color_idx, int)
  if color_idx == -1:
    return None
  else:
    return COLOR_CHAR[color_idx]


def color_char_to_idx(color_char):
  pass                                                        

       
                                                    

          
                                                                   

         
                                                   
     
  assert isinstance(color_char, str)
  try:
    return next(idx for (idx, c) in enumerate(COLOR_CHAR) if c == color_char)
  except StopIteration:
    raise ValueError("Invalid color: {}. Should be one of {}.".format(
        color_char, COLOR_CHAR))


class HanabiCard(object):
  pass                                    

                                                
     

  def __init__(self, color, rank):
    pass                          

         
                                                                       
                                                                              
                                                               
       
    self._color = color
    self._rank = rank

  def color(self):
    return self._color

  def rank(self):
    return self._rank

  def __str__(self):
    if self.valid():
      return COLOR_CHAR[self._color] + str(self._rank + 1)
    else:
      return "XX"

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self._color == other.color() and self._rank == other.rank()

  def valid(self):
    return self._color >= 0 and self._rank >= 0

  def to_dict(self):
    pass                 

            
                                                 
       
    return {"color": color_idx_to_char(self.color()), "rank": self.rank()}


class HanabiCardKnowledge(object):
  pass                                                                       

                                                                        
                                         

                                                                       
                                                                          
                                                                            
                                           

                                                                             
                                                              
                                                                            
                                                                           
                                                                

                                                                           
                                                                              
                                                                              
                                                                          
                                            

                                                        
     

  def __init__(self, knowledge):
    self._knowledge = knowledge

  def color(self):
    pass                                                                  

                                                                          
       
    if lib.ColorWasHinted(self._knowledge):
      return lib.KnownColor(self._knowledge)
    else:
      return None

  def color_plausible(self, color_index):
    pass                                                                  

         
                                       
       
    return lib.ColorIsPlausible(self._knowledge, color_index)

  def rank(self):
    pass                                                                

                                                                        
       
    if lib.RankWasHinted(self._knowledge):
      return lib.KnownRank(self._knowledge)
    else:
      return None

  def rank_plausible(self, rank_index):
    pass                                                                 

         
                                     
       
    return lib.RankIsPlausible(self._knowledge, rank_index)

  def __str__(self):
    c_string = lib.CardKnowledgeToString(self._knowledge)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def __repr__(self):
    return self.__str__()

  def to_dict(self):
    pass                 

            
                                                 
       
    return {"color": color_idx_to_char(self.color()), "rank": self.rank()}


class HanabiMoveType(enum.IntEnum):
  pass                                                       
  INVALID = 0
  PLAY = 1
  DISCARD = 2
  REVEAL_COLOR = 3
  REVEAL_RANK = 4
  DEAL = 5


class HanabiMove(object):
  pass                                            

                                         
     

  def __init__(self, move):
    assert move is not None
    self._move = move

  @property
  def c_move(self):
    return self._move

  def type(self):
    return HanabiMoveType(lib.MoveType(self._move))

  def card_index(self):
    pass                                                        
    return lib.CardIndex(self._move)

  def target_offset(self):
    pass                                                    
    return lib.TargetOffset(self._move)

  def color(self):
    pass                                                              
    return lib.MoveColor(self._move)

  def rank(self):
    pass                                                            
    return lib.MoveRank(self._move)

  @staticmethod
  def get_discard_move(card_index):
    c_move = ffi.new("pyhanabi_move_t*")
    assert lib.GetDiscardMove(card_index, c_move)
    return HanabiMove(c_move)

  @staticmethod
  def get_play_move(card_index):
    c_move = ffi.new("pyhanabi_move_t*")
    assert lib.GetPlayMove(card_index, c_move)
    return HanabiMove(c_move)

  @staticmethod
  def get_reveal_color_move(target_offset, color):
    pass                                                                     
    c_move = ffi.new("pyhanabi_move_t*")
    assert lib.GetRevealColorMove(target_offset, color, c_move)
    return HanabiMove(c_move)

  @staticmethod
  def get_reveal_rank_move(target_offset, rank):
    pass                                                                     
    c_move = ffi.new("pyhanabi_move_t*")
    assert lib.GetRevealRankMove(target_offset, rank, c_move)
    return HanabiMove(c_move)

  def __str__(self):
    c_string = lib.MoveToString(self._move)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def __repr__(self):
    return self.__str__()

  def __del__(self):
    if self._move is not None:
      lib.DeleteMove(self._move)
      self._move = None
    del self

  def to_dict(self):
    pass                 

            
                                                                

           
                                                
       
    move_dict = {}
    move_type = self.type()
    move_dict["action_type"] = move_type.name
    if move_type == HanabiMoveType.PLAY or move_type == HanabiMoveType.DISCARD:
      move_dict["card_index"] = self.card_index()
    elif move_type == HanabiMoveType.REVEAL_COLOR:
      move_dict["target_offset"] = self.target_offset()
      move_dict["color"] = color_idx_to_char(self.color())
    elif move_type == HanabiMoveType.REVEAL_RANK:
      move_dict["target_offset"] = self.target_offset()
      move_dict["rank"] = self.rank()
    elif move_type == HanabiMoveType.DEAL:
      move_dict["color"] = color_idx_to_char(self.color())
      move_dict["rank"] = self.rank()
    else:
      raise ValueError("Unsupported move: {}".format(self))

    return move_dict


class HanabiHistoryItem(object):
  pass                                                                    

                                                                             
                                                                               
                                                                             
                                                              

                                                
     

  def __init__(self, item):
    self._item = item

  def move(self):
    c_move = ffi.new("pyhanabi_move_t*")
    lib.HistoryItemMove(self._item, c_move)
    return HanabiMove(c_move)

  def player(self):
    return lib.HistoryItemPlayer(self._item)

  def scored(self):
    pass                                                   
    return bool(lib.HistoryItemScored(self._item))

  def information_token(self):
    pass                                                               
    return bool(lib.HistoryItemInformationToken(self._item))

  def color(self):
    pass                                                
    return lib.HistoryItemColor(self._item)

  def rank(self):
    pass                                               
    return lib.HistoryItemRank(self._item)

  def card_info_revealed(self):
    pass                                                         

                                                                  
                                                                      
                              
       
    revealed = []
    bitmask = lib.HistoryItemRevealBitmask(self._item)
    for i in range(8):                            
      if bitmask & (1 << i):
        revealed.append(i)
    return revealed

  def card_info_newly_revealed(self):
    pass                                                               

                                                                   
                                                                      
                                                                   
                                                                 
                                                                  
       
    revealed = []
    bitmask = lib.HistoryItemNewlyRevealedBitmask(self._item)
    for i in range(8):                            
      if bitmask & (1 << i):
        revealed.append(i)
    return revealed

  def deal_to_player(self):
    pass                                               
    return lib.HistoryItemDealToPlayer(self._item)

  def __str__(self):
    c_string = lib.HistoryItemToString(self._item)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def __repr__(self):
    return self.__str__()

  def __del__(self):
    if self._item is not None:
      lib.DeleteHistoryItem(self._item)
      self._item = None
    del self


class HanabiEndOfGameType(enum.IntEnum):
  pass                                                                  
  NOT_FINISHED = 0
  OUT_OF_LIFE_TOKENS = 1
  OUT_OF_CARDS = 2
  COMPLETED_FIREWORKS = 3


class HanabiState(object):
  pass                                                   

                                                                             
                                                                           
                                              

                                          
     

  def __init__(self, game, c_state=None):
    pass                   

         
                                                                      
                                                          

                                                                           
       
    self._state = ffi.new("pyhanabi_state_t*")
    if c_state is None:
      self._game = game.c_game
      lib.NewState(self._game, self._state)
    else:
      self._game = ffi.new("pyhanabi_game_t*")
      lib.StateParentGame(c_state, self._game)
      lib.CopyState(c_state, self._state)

  def copy(self):
    pass                              
    return HanabiState(None, self._state)

  def observation(self, player):
    pass                                                              
    return HanabiObservation(self._state, self._game, player)

  def apply_move(self, move):
    pass                                                                 
    lib.StateApplyMove(self._state, move.c_move)

  def cur_player(self):
    pass                                   

                                                                          
       
    return lib.StateCurPlayer(self._state)

  def deck_size(self):
    pass                                           
    return lib.StateDeckSize(self._state)

  def discard_pile(self):
    pass                                                                      
    discards = []
    c_card = ffi.new("pyhanabi_card_t*")
    for index in range(lib.StateDiscardPileSize(self._state)):
      lib.StateGetDiscard(self._state, index, c_card)
      discards.append(HanabiCard(c_card.color, c_card.rank))
    return discards

  def fireworks(self):
    pass                                                                     

                                                                          
                                                                               
                                                  
       
    firework_list = []
    num_colors = lib.NumColors(self._game)
    for c in range(num_colors):
      firework_list.append(lib.StateFireworks(self._state, c))
    return firework_list

  def deal_random_card(self):
    pass                                                                  
    lib.StateDealRandomCard(self._state)

  def player_hands(self):
    pass                                                                   
    hand_list = []
    c_card = ffi.new("pyhanabi_card_t*")
    for pid in range(self.num_players()):
      player_hand = []
      hand_size = lib.StateGetHandSize(self._state, pid)
      for i in range(hand_size):
        lib.StateGetHandCard(self._state, pid, i, c_card)
        player_hand.append(HanabiCard(c_card.color, c_card.rank))
      hand_list.append(player_hand)
    return hand_list

  def information_tokens(self):
    pass                                                     
    return lib.StateInformationTokens(self._state)

  def end_of_game_status(self):
    pass                                                                       
    return HanabiEndOfGameType(lib.StateEndOfGameStatus(self._state))

  def is_terminal(self):
    pass                                                        
    return (lib.StateEndOfGameStatus(self._state) !=
            HanabiEndOfGameType.NOT_FINISHED)

  def legal_moves(self):
    pass                                                          
    moves = []
    c_movelist = lib.StateLegalMoves(self._state)
    num_moves = lib.NumMoves(c_movelist)
    for i in range(num_moves):
      c_move = ffi.new("pyhanabi_move_t*")
      lib.GetMove(c_movelist, i, c_move)
      moves.append(HanabiMove(c_move))
    lib.DeleteMoveList(c_movelist)
    return moves

  def move_is_legal(self, move):
    pass                                                             
    return lib.MoveIsLegal(self._state, move.c_move)

  def card_playable_on_fireworks(self, color, rank):
    pass                                                           

         
                                        
                                      
       
    return lib.CardPlayableOnFireworks(self._state, color, rank)

  def life_tokens(self):
    pass                                                     
    return lib.StateLifeTokens(self._state)

  def num_players(self):
    pass                                            
    return lib.StateNumPlayers(self._state)

  def score(self):
    pass                                                       

                                                        
       
    return lib.StateScore(self._state)

  def move_history(self):
    pass                                                         
    history = []
    history_len = lib.StateLenMoveHistory(self._state)
    for i in range(history_len):
      c_history_item = ffi.new("pyhanabi_history_item_t*")
      lib.StateGetMoveHistory(self._state, i, c_history_item)
      history.append(HanabiHistoryItem(c_history_item))
    return history

  def __str__(self):
    c_string = lib.StateToString(self._state)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def __repr__(self):
    return self.__str__()

  def __del__(self):
    if self._state is not None:
      lib.DeleteState(self._state)
      self._state = None
    del self


class AgentObservationType(enum.IntEnum):
  pass                                                               

                                                                      
                                                                         
                                                                          
                                                                      
                                                                          
                                                                       
                        
     
  MINIMAL = 0
  CARD_KNOWLEDGE = 1
  SEER = 2


class HanabiGame(object):
  pass                                                        

                                         
     

  def __init__(self, params=None):
    pass                           

         
                                                             

                               
                                          
                                                               
                                                            
                                                    
                                                                               
                                                                        
                                                                           
                                                                             
                                                 
       
    if params is None:
      self._game = ffi.new("pyhanabi_game_t*")
      lib.NewDefaultGame(self._game)
    else:
      param_list = []
      for key in params:
        param_list.append(ffi.new("char[]", key.encode('ascii')))
        param_list.append(ffi.new("char[]", str(params[key]).encode('ascii')))
      c_array = ffi.new("char * [" + str(len(param_list)) + "]", param_list)
      self._game = ffi.new("pyhanabi_game_t*")
      lib.NewGame(self._game, len(param_list), c_array)

  def new_initial_state(self):
    return HanabiState(self)

  @property
  def c_game(self):
    pass                                   
    return self._game

  def __del__(self):
    if self._game is not None:
      lib.DeleteGame(self._game)
      self._game = None
    del self

  def parameter_string(self):
    pass                                            
    c_string = lib.GameParamString(self._game)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def num_players(self):
    pass                                            
    return lib.NumPlayers(self._game)

  def num_colors(self):
    pass                                                        
    return lib.NumColors(self._game)

  def num_ranks(self):
    pass                                                       
    return lib.NumRanks(self._game)

  def hand_size(self):
    pass                                                       

                                                                           
                                                                        
                                                                           
                                                                         
       
    return lib.HandSize(self._game)

  def max_information_tokens(self):
    pass                                                   
    return lib.MaxInformationTokens(self._game)

  def max_life_tokens(self):
    pass                                            
    return lib.MaxLifeTokens(self._game)

  def observation_type(self):
    return AgentObservationType(lib.ObservationType(self._game))

  def max_moves(self):
    pass                                                         
    return lib.MaxMoves(self._game)

  def num_cards(self, color, rank):
    pass                                                                       
    return lib.NumCards(self._game, color, rank)

  def get_move_uid(self, move):
    pass                                                                      
    return lib.GetMoveUid(self._game, move.c_move)

  def get_move(self, move_uid):
    pass                                                                  
    move = ffi.new("pyhanabi_move_t*")
    lib.GetMoveByUid(self._game, move_uid, move)
    return HanabiMove(move)


class HanabiObservation(object):
  pass                                                    

                                                                            
                                                                            
                                                                          
                                                                        

                                                
     

  def __init__(self, state, game, player):
    pass                                                  
    self._observation = ffi.new("pyhanabi_observation_t*")
    self._game = game
    lib.NewObservation(state, player, self._observation)

  def __str__(self):
    c_string = lib.ObsToString(self._observation)
    string = encode_ffi_string(c_string)
    lib.DeleteString(c_string)
    return string

  def __repr__(self):
    return self.__str__()

  def __del__(self):
    if self._observation is not None:
      lib.DeleteObservation(self._observation)
      self._observation = None
    del self

  def observation(self):
    pass                                           
    return self._observation

  def cur_player_offset(self):
    pass                                                                      
    return lib.ObsCurPlayerOffset(self._observation)

  def num_players(self):
    pass                                            
    return lib.ObsNumPlayers(self._observation)

  def observed_hands(self):
    pass                                                                

                                                     
       
    hand_list = []
    c_card = ffi.new("pyhanabi_card_t*")
    for pid in range(self.num_players()):
      player_hand = []
      hand_size = lib.ObsGetHandSize(self._observation, pid)
      for i in range(hand_size):
        lib.ObsGetHandCard(self._observation, pid, i, c_card)
        player_hand.append(HanabiCard(c_card.color, c_card.rank))
      hand_list.append(player_hand)
    return hand_list

  def card_knowledge(self):
    pass                                                  

                                                                          
                                                                           
                                             
       
    card_knowledge_list = []
    for pid in range(self.num_players()):
      player_card_knowledge = []
      hand_size = lib.ObsGetHandSize(self._observation, pid)
      for i in range(hand_size):
        c_knowledge = ffi.new("pyhanabi_card_knowledge_t*")
        lib.ObsGetHandCardKnowledge(self._observation, pid, i, c_knowledge)
        player_card_knowledge.append(HanabiCardKnowledge(c_knowledge))
      card_knowledge_list.append(player_card_knowledge)
    return card_knowledge_list

  def discard_pile(self):
    pass                                                                      
    discards = []
    c_card = ffi.new("pyhanabi_card_t*")
    for index in range(lib.ObsDiscardPileSize(self._observation)):
      lib.ObsGetDiscard(self._observation, index, c_card)
      discards.append(HanabiCard(c_card.color, c_card.rank))
    return discards

  def fireworks(self):
    pass                                                                
    firework_list = []
    num_colors = lib.NumColors(self._game)
    for c in range(num_colors):
      firework_list.append(lib.ObsFireworks(self._observation, c))
    return firework_list

  def deck_size(self):
    pass                                           
    return lib.ObsDeckSize(self._observation)

  def last_moves(self):
    pass                                                    

                                                                       
                                                                     
                                                     
       
    history_items = []
    for i in range(lib.ObsNumLastMoves(self._observation)):
      history_item = ffi.new("pyhanabi_history_item_t*")
      lib.ObsGetLastMove(self._observation, i, history_item)
      history_items.append(HanabiHistoryItem(history_item))
    return history_items

  def information_tokens(self):
    pass                                                     
    return lib.ObsInformationTokens(self._observation)

  def life_tokens(self):
    pass                                                     
    return lib.ObsLifeTokens(self._observation)

  def legal_moves(self):
    pass                                                

                                                                          
       
    moves = []
    for i in range(lib.ObsNumLegalMoves(self._observation)):
      move = ffi.new("pyhanabi_move_t*")
      lib.ObsGetLegalMove(self._observation, i, move)
      moves.append(HanabiMove(move))
    return moves

  def card_playable_on_fireworks(self, color, rank):
    pass                                                           

         
                                        
                                      
       
    return lib.ObsCardPlayableOnFireworks(self._observation, color, rank)


class ObservationEncoderType(enum.IntEnum):
  pass                                                       
  CANONICAL = 0


class ObservationEncoder(object):
  pass                        

                                                                         
                                                                         
                               
     

  def __init__(self, game, enc_type=ObservationEncoderType.CANONICAL):
    pass                                                  
    self._game = game.c_game
    self._encoder = ffi.new("pyhanabi_observation_encoder_t*")
    lib.NewObservationEncoder(self._encoder, self._game, enc_type)

  def __del__(self):
    if self._encoder is not None:
      lib.DeleteObservationEncoder(self._encoder)
      self._encoder = None
      self._game = None
    del self

  def shape(self):
    c_shape_str = lib.ObservationShape(self._encoder)
    shape_string = encode_ffi_string(c_shape_str)
    lib.DeleteString(c_shape_str)
    shape = [int(x) for x in shape_string.split(",")]
    return shape

  def encode(self, observation):
    pass                                               
    c_encoding_str = lib.EncodeObservation(self._encoder,
                                           observation.observation())
    encoding_string = encode_ffi_string(c_encoding_str)
    lib.DeleteString(c_encoding_str)
                                                                           
                                                                    
    encoding = [int(x) for x in encoding_string.split(",")]
    return encoding


try_cdef()
if cdef_loaded():
  try_load()
