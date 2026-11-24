import random, re
from typing import Dict, Any, Optional, List, Tuple
import textarena as ta


class LeTrucEnv(ta.Env):
    pass                                                    

                                                                       
                                                                             
                                                                              
                            

                                                                                
                                                                               
                                                                              
                                                                               
                                                                                

                                                                               
                                                                           
                                                                                
                                                                               
                                             
       
    order = ["3", "2", "A", "K", "Q", "J", "7", "6", "5", "4"]

    def __init__(self):
        super().__init__()
        self.action_space = re.compile(
            r"""\[
                (?P<verb>play|raise|accept|fold)            # action keyword
                (?:\s+(?P<card>(10|[234567JQKA])))?         # optional rank (play)
            \]""",
            re.IGNORECASE | re.VERBOSE,
        )
                                
        suits = "♣♦♥♠"
        self.deck = [r + s for r in self.order for s in suits]

                                                                              
    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
                                                                               
        self.state.reset(game_state={"match_points": {0: 0, 1: 0}, "stake": 1, "dealer": 1}, player_prompt_function=self._prompt)
        self._deal_hand()

    def _prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        return self.m("player_prompt", "intro")

    def _deal_hand(self):
        gs = self.state.game_state
        d = self.deck.copy()
        random.shuffle(d)
        gs["hands"]         = {0: d[:3], 1: d[3:6]}
        gs["trick_results"] = []                                                             
        gs["led"]           = None                                                               
        gs["pending"]       = None                                                                         
        gs["raise_origin"]  = None                                                                  
        leader = 1 - gs["dealer"]                                          
        gs["leader"]  = leader
        gs["dealer"]  = 1 - gs["dealer"]                                          
        for pid in (0, 1):
            self.state.add_observation(to_id=pid, message=self.m("board", "new_hand", points=gs["stake"], cards=" ".join(gs["hands"][pid])), observation_type=ta.ObservationType.GAME_BOARD)
        self.state.manually_set_current_player_id(leader)
        self._announce_legal(leader)

                                                                               
    def _rank_idx(self, card: str) -> int:
        return self.order.index(card[:-1])

    def _next_stake(self, stake: int) -> int:
                                                                                     
        return 2 if stake == 1 else min(stake + 2, 12)

    def _legal(self, pid: int) -> List[str]:
        gs = self.state.game_state
        if gs["pending"] is not None:                                                         
            acts = ["accept", "fold"]
            if gs["stake"] < 12: acts.append("raise")
            return acts
        acts = [f"play {c[:-1]}" for c in gs["hands"][pid]]                                   
        if gs["stake"] < 12: acts.append("raise")
        return acts

    def _announce_legal(self, pid: int):
        legal = ", ".join(f"'[{a}]'" for a in self._legal(pid))
        self.state.add_observation(to_id=pid, message=self.m("board", "valid_actions", legal=legal), observation_type=ta.ObservationType.GAME_BOARD)

    def _resolve(self, results: List[Optional[int]]):
        pass                                             

                                                                                  
                                                                                 
                                     
                                                      
                                                                                 
                                                          
                                                                                 
                                                
           
        first_winner = next((r for r in results if r is not None), None)
        spoilt = sum(1 for r in results if r is None)
        eff = {0: 0, 1: 0}
        for r in results:
            if r is not None: eff[r] += 1
        if first_winner is not None: eff[first_winner] += spoilt
        if eff[0] >= 2: return 0
        if eff[1] >= 2: return 1
        if len(results) == 3: return None                                                     
        return "undecided"

                                                                             
    def step(self, action: str) -> Tuple[bool, Dict[str, Any]]:
        pid = self.state.current_player_id
        self.state.add_observation(from_id=pid, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        m = self.action_space.search(action)
        if not m:
            return self._invalid("unrecognised")
        verb = m.group("verb").lower()
        if verb == "raise":  return self._do_raise(pid)
        if verb == "accept": return self._do_accept(pid)
        if verb == "fold":   return self._do_fold(pid)
        return self._do_play(pid, m.group("card"))

    def _invalid(self, key: str):
        self.state.set_invalid_move(reason=self.m("invalid_move", key))
        return self.state.step()

    def _do_raise(self, pid: int):
        gs = self.state.game_state
        if gs["stake"] >= 12:
            return self._invalid("max_stake")
        if gs["pending"] is not None and gs["pending"]["offerer"] == pid:
            return self._invalid("already_raised")                                         
        if gs["pending"] is not None:
            gs["stake"] = gs["pending"]["proposed"]                                                          
        else:
            gs["raise_origin"] = pid                                                                   
        proposed = self._next_stake(gs["stake"])
        gs["pending"] = {"offerer": pid, "proposed": proposed}
        self.state.add_observation(message=self.m("action", "raise", pid=pid, points=proposed), observation_type=ta.ObservationType.GAME_MESSAGE)
        responder = 1 - pid
        self.state.manually_set_current_player_id(responder)
        self._announce_legal(responder)
        return self.state.step(rotate_player=False)

    def _do_accept(self, pid: int):
        gs = self.state.game_state
        if gs["pending"] is None or gs["pending"]["offerer"] == pid:
            return self._invalid("no_raise_to_accept")
        gs["stake"] = gs["pending"]["proposed"]
        gs["pending"] = None
        origin = gs["raise_origin"]
        gs["raise_origin"] = None
        self.state.add_observation(message=self.m("action", "accept", pid=pid, points=gs["stake"]), observation_type=ta.ObservationType.GAME_MESSAGE)
        self.state.manually_set_current_player_id(origin)                                       
        self._announce_legal(origin)
        return self.state.step(rotate_player=False)

    def _do_fold(self, pid: int):
        gs = self.state.game_state
        if gs["pending"] is None or gs["pending"]["offerer"] == pid:
            return self._invalid("cannot_fold")
        winner = 1 - pid                                                                
        self.state.add_observation(message=self.m("outcome", "folded"), observation_type=ta.ObservationType.GAME_MESSAGE)
                                                                                     
                               
        return self._award_hand(winner)

    def _do_play(self, pid: int, card_group: Optional[str]):
        gs = self.state.game_state
        if gs["pending"] is not None:
            return self._invalid("must_respond")
        if card_group is None:
            return self._invalid("unrecognised")
        rank = card_group.upper()
        if rank not in [c[:-1] for c in gs["hands"][pid]]:
            return self._invalid("wrong_rank")
        idx = next(i for i, c in enumerate(gs["hands"][pid]) if c[:-1] == rank)
        card_str = gs["hands"][pid].pop(idx)

        if gs["led"] is None:                                                 
            gs["led"] = (pid, card_str)
            self.state.add_observation(message=self.m("action", "lead", pid=pid, card=card_str), observation_type=ta.ObservationType.GAME_MESSAGE)
            follower = 1 - pid
            self.state.manually_set_current_player_id(follower)
            self._announce_legal(follower)
            return self.state.step(rotate_player=False)

                                                                         
        lead_pid, lead_card = gs["led"]
        if self._rank_idx(card_str) < self._rank_idx(lead_card):   trick_winner = pid
        elif self._rank_idx(card_str) > self._rank_idx(lead_card): trick_winner = lead_pid
        else:                                                      trick_winner = None           
        gs["led"] = None
        gs["trick_results"].append(trick_winner)
        if trick_winner is None:
            self.state.add_observation(message=self.m("action", "spoilt", pid=pid, card=card_str), observation_type=ta.ObservationType.GAME_MESSAGE)
        else:
            self.state.add_observation(message=self.m("action", "play", pid=pid, card=card_str, winner=trick_winner), observation_type=ta.ObservationType.GAME_MESSAGE)

        decision = self._resolve(gs["trick_results"])
        if decision == "undecided":
            next_leader = trick_winner if trick_winner is not None else gs["leader"]                         
            gs["leader"] = next_leader
            self.state.manually_set_current_player_id(next_leader)
            self._announce_legal(next_leader)
            return self.state.step(rotate_player=False)
        if decision is None:
            return self._void_hand()
        return self._award_hand(decision)

                                                                               
    def _award_hand(self, winner: int):
        gs = self.state.game_state
        gs["match_points"][winner] += gs["stake"]
        p0, p1 = gs["match_points"][0], gs["match_points"][1]
        self.state.add_observation(message=self.m("outcome", "hand_won", winner=winner, points=gs["stake"], p0=p0, p1=p1), observation_type=ta.ObservationType.GAME_MESSAGE)
        if gs["match_points"][winner] >= 12:
            self.state.set_winner(winner, reason=self.m("outcome", "reached_twelve"))
            return self.state.step()
        gs["stake"] = 1
        self._deal_hand()
        return self.state.step(rotate_player=False)

    def _void_hand(self):
        gs = self.state.game_state
        p0, p1 = gs["match_points"][0], gs["match_points"][1]
        self.state.add_observation(message=self.m("outcome", "void", p0=p0, p1=p1), observation_type=ta.ObservationType.GAME_MESSAGE)
        gs["stake"] = 1
        self._deal_hand()
        return self.state.step(rotate_player=False)
