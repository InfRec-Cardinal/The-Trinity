from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class GamePhase(Enum):
    Play = "play"                                                                    
    QueryWhichToKeep = "query_which_to_keep"                                                                                          
    QueryForBlockOrChallenge = "query_for_block_or_challenge"                                                                                            
    QueryToChallengeTheBlocker = "query_to_challenge_the_blocker"                                                                                  

class CoupActionType(Enum):
    pass                                                                               
                                                                    
       
    Income = "income"
    Coup = "coup"
    ForeignAid = "foreign aid"
    Tax = "tax"
    Assassinate = "assassinate"
    Exchange = "exchange"
    Steal = "steal"

                                                                         
                                                                                            
                                                                   
    Keep = "keep"

                    
    PASS = "pass"
    BULLSHIT = "bullshit"

    BlockForeignAid = "block foreign aid"
    BlockStealAmbassador = "block steal ambassador"
    BlockStealCaptain = "block steal captain"
    BlockAssassinate = "block assassinate"

    
@dataclass
class ActionMetadata:
    pass                                            
    action_type: CoupActionType
    source_player_id: int                                                           
    target_player_id: Optional[int] = None                                                        

    players_to_query: Optional[List[int]] = None                                           

    blocker_player_id: Optional[int] = None                                               
    block_type: Optional[CoupActionType] = None                                                                                  
    blocker_challenger_player_id: Optional[int] = None                                                                                                    
    challenger_player_id: Optional[int] = None                                                           

    cards_to_keep: Optional[List[str]] = None                                   