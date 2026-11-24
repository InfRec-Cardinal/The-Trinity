#!/usr/bin/env python3
                                                    

                                                  

                                                                                            
                                                                                    
                                                                           
                                                           
                                                                                      

                                                                                        
                                                                                            
                                                                                    
   
import json
import os
import re
import subprocess
import sys
import time

                                                                                                      
_PROTO_OUT = sys.stdout
sys.stdout = sys.stderr

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE_ROOT = os.path.realpath(os.path.join(HERE, "../../../..", "vendor", "TextArena"))
sys.path.insert(0, PACKAGE_ROOT)

import textarena as ta
if os.path.realpath(ta.__file__) != os.path.join(PACKAGE_ROOT, 'textarena', '__init__.py'):
    raise RuntimeError('Expected the shared bundled TextArena source')
from textarena.core import Wrapper              
from textarena.agents.basic_agents import STANDARD_GAME_PROMPT              
from textarena.envs.Coup.env import _CoupInvalid              
from textarena.envs.Coup.coup_types import CoupActionType as A, GamePhase              
from textarena.wrappers import ActionFormattingWrapper              

ENV_ID = "Coup-v0"
NUM_PLAYERS = 4
NUM_GAMES = 40
SEED_BASE = 2026101100

CODEX = os.environ.get("H0_OPPONENT_CODEX_BIN", "codex")                                                                   
OPP_MODEL = "gpt-5.6-luna"
OPP_TIMEOUT_S = 180
OPP_RETRIES = 3                                                                               

ACTION_CLAIM = {A.Tax: "Duke", A.Assassinate: "Assassin", A.Steal: "Captain", A.Exchange: "Ambassador"}
BLOCK_CLAIM = {A.BlockForeignAid: "Duke", A.BlockStealCaptain: "Captain",
               A.BlockStealAmbassador: "Ambassador", A.BlockAssassinate: "Contessa"}
DIRECTED = {A.Coup, A.Assassinate, A.Steal}


def log(*args):
    print("[coup-bridge]", *args, file=sys.stderr, flush=True)


def emit(obj):
    _PROTO_OUT.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _PROTO_OUT.flush()


def _redact(text):
    text = re.sub(r"(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+", r"\1<redacted>", text)
    return re.sub(r"(?i)(api[_-]?key|authorization|bearer|token)([\"'=: ]+)\S+", r"\1\2<redacted>", text)


                                                                                               
           
                                                                                               
class OpponentFailure(RuntimeError):
    pass


class CodexOpponents:
    pass                                                                                               

    def __init__(self, game, log_path):
        self.game = game
        self.log_path = log_path
        self.scratch = os.path.join(os.environ.get("H0_BRIDGE_SCRATCH", os.path.join(HERE, "scratch")), f"game-{game:02d}-pid{os.getpid()}")
        os.makedirs(self.scratch, exist_ok=True)
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self.calls = 0

    def _log(self, rec):
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def __call__(self, seat, observation, env_turn):
        prompt = STANDARD_GAME_PROMPT + "\n\n" + observation
        last_err = None
        seat_dir = os.path.join(self.scratch, f"seat-{seat}")                                 
        os.makedirs(seat_dir, exist_ok=True)
        for attempt in range(1, OPP_RETRIES + 2):
            self.calls += 1
            outfile = os.path.join(seat_dir, f"reply-t{env_turn}-a{attempt}.txt")
            if os.path.exists(outfile):
                os.remove(outfile)
            cmd = ([sys.executable, CODEX] if CODEX.endswith(".py") else [CODEX]) + ["exec", "--skip-git-repo-check", "-s", "read-only", "-m", OPP_MODEL,
                   "-c", "model_reasoning_effort=low", "-o", outfile, prompt]
            t0 = time.time()
            status, err, reply = "ok", None, None
            try:
                proc = subprocess.run(cmd, cwd=seat_dir, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                      timeout=OPP_TIMEOUT_S)
                if proc.returncode != 0:
                    status = "error"
                    err = f"exit {proc.returncode}: " + _redact(proc.stderr.decode("utf-8", "replace")[-300:])
                else:
                    with open(outfile, "r", encoding="utf-8") as fh:
                        reply = fh.read()
                    if not reply.strip():
                        status, err = "error", "empty reply"
            except subprocess.TimeoutExpired:
                status, err = "error", f"timeout after {OPP_TIMEOUT_S}s"
            except Exception as exc:                
                status, err = "error", _redact(f"{type(exc).__name__}: {exc}")[:300]
            latency = round(time.time() - t0, 3)
            self._log({"ts": round(t0, 3), "game": self.game, "seat": seat, "envTurn": env_turn,
                       "attempt": attempt, "latencySec": latency, "status": status, "error": err,
                       "promptChars": len(prompt), "replyChars": len(reply) if reply else 0,
                       "model": OPP_MODEL})
            log(f"opponent seat {seat} turn {env_turn} attempt {attempt}: {status} in {latency}s"
                + (f" ({err})" if err else ""))
            if status == "ok":
                return reply
            last_err = err
        raise OpponentFailure(f"seat {seat} env turn {env_turn}: {OPP_RETRIES + 1} attempts failed; last: {last_err}")


class StubOpponents:
    pass                                                                                                  

    def __init__(self, core, game, log_path):
        self.core, self.game, self.log_path = core, game, log_path
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self.calls = 0

    def __call__(self, seat, observation, env_turn):
        self.calls += 1
        gs = self.core.state.game_state
        phase, md = gs["phase"], gs["action_metadata"]
        alive = [p for p in range(NUM_PLAYERS) if gs["hidden_hand"][p] and p != seat]
        if phase == GamePhase.QueryWhichToKeep:
            n = 2 - len(gs["revealed_hand"][seat])
            reply = "[keep " + " ".join(gs["hidden_hand"][seat][:n]) + "]"
        elif phase == GamePhase.QueryForBlockOrChallenge:
                                                                                                           
            if md.action_type in ACTION_CLAIM and env_turn % 2 == 0:
                reply = "I think you are lying. [BULLSHIT]"
            else:
                reply = "[PASS]"
        elif phase == GamePhase.QueryToChallengeTheBlocker:
            reply = "[PASS]"
        elif gs["coins"][seat] >= 7:
            reply = f"[coup {alive[0]}]"
        elif env_turn % 3 == 0:
            reply = "[tax]"
        else:
            reply = "[income]"
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": round(time.time(), 3), "game": self.game, "seat": seat, "envTurn": env_turn,
                                 "attempt": 1, "latencySec": 0.0, "status": "ok", "error": None,
                                 "model": "stub"}) + "\n")
        return reply


                                                                                               
                                                                               
                                                                                               
class PlayerStats:
    pass                                                                                                    
                                                                                                           
                                                                            
                                                                                            
                                                                                                       
                                                                          
                                                                                                          
       

    def __init__(self, seat):
        self.seat = seat
        self.c = dict(claims=0, bluffsMade=0, bluffsSucceeded=0, bluffsCaught=0, bluffsUnresolved=0,
                      honestClaimsChallenged=0, challengesMade=0, challengesSucceeded=0, challengesFailed=0,
                      timesBlockedByOthers=0)
        self.open = None                                                           
        self.events = []

    @staticmethod
    def snapshot(core):
        gs = core.state.game_state
        md = gs["action_metadata"]
        return {
            "phase": gs["phase"], "cur": core.state.current_player_id, "turn": core.state.turn,
            "hands": {p: list(h) for p, h in gs["hidden_hand"].items()},
            "md": None if md is None else dict(action_type=md.action_type, source=md.source_player_id,
                                                target=md.target_player_id, blocker=md.blocker_player_id,
                                                block_type=md.block_type),
        }

    def update(self, pre, parsed, valid, core):
        if not valid or parsed is None:
            self._close_if_window_ended(core)
            return
        atype, _arg = parsed
        cur, phase, md, P = pre["cur"], pre["phase"], pre["md"], self.seat
                              
        if cur == P and phase == GamePhase.Play and atype in ACTION_CLAIM:
            self._claim("action", ACTION_CLAIM[atype], atype, pre)
        elif cur == P and phase == GamePhase.QueryForBlockOrChallenge and atype in BLOCK_CLAIM:
            self._claim("block", BLOCK_CLAIM[atype], atype, pre)
                                             
        if cur != P and phase == GamePhase.QueryForBlockOrChallenge and atype in BLOCK_CLAIM and md and md["source"] == P:
            self.c["timesBlockedByOthers"] += 1
                    
        if atype == A.BULLSHIT and phase in (GamePhase.QueryForBlockOrChallenge, GamePhase.QueryToChallengeTheBlocker) and md:
            if phase == GamePhase.QueryForBlockOrChallenge:
                challenged, card = md["source"], ACTION_CLAIM.get(md["action_type"], ".")
            else:
                challenged, card = md["blocker"], BLOCK_CLAIM.get(md["block_type"], ".")
            honest = card in pre["hands"].get(challenged, [])
            if cur == P:
                self.c["challengesMade"] += 1
                self.c["challengesSucceeded" if not honest else "challengesFailed"] += 1
                self.events.append(dict(envTurn=pre["turn"], event="player_challenged", target=challenged,
                                        claimedCard=card, claimWasTrue=honest))
            if challenged == P and self.open is not None:
                if self.open["bluff"]:
                    self.c["bluffsCaught"] += 1
                else:
                    self.c["honestClaimsChallenged"] += 1
                self.events.append(dict(envTurn=pre["turn"], event="player_claim_challenged", by=cur,
                                        claimedCard=self.open["card"], bluff=self.open["bluff"]))
                self.open = None
        self._close_if_window_ended(core)

    def _claim(self, kind, card, atype, pre):
        bluff = card not in pre["hands"][self.seat]
        self.c["claims"] += 1
        if bluff:
            self.c["bluffsMade"] += 1
        self.open = dict(kind=kind, card=card, bluff=bluff, envTurn=pre["turn"])
        self.events.append(dict(envTurn=pre["turn"], event="player_claim", kind=kind, action=atype.value,
                                claimedCard=card, bluff=bluff))

    def _close_if_window_ended(self, core):
        if self.open is None:
            return
        gs = core.state.game_state
        md, phase = gs["action_metadata"], gs["phase"]
        if self.open["kind"] == "action":
            still = phase == GamePhase.QueryForBlockOrChallenge and md is not None and md.source_player_id == self.seat
        else:
            still = phase == GamePhase.QueryToChallengeTheBlocker and md is not None and md.blocker_player_id == self.seat
        if still:
            return                                                                              
        if self.open["bluff"]:
            self.c["bluffsSucceeded"] += 1
        self.events.append(dict(envTurn=core.state.turn, event="player_claim_unchallenged",
                                claimedCard=self.open["card"], bluff=self.open["bluff"]))
        self.open = None

    def result(self):
        out = dict(self.c)
        if self.open is not None and self.open["bluff"]:
            out["bluffsUnresolved"] += 1
        return out


                                                                                               
      
                                                                                               
def unwrap(env):
    core, action_fmt = env, None
    while isinstance(core, Wrapper):
        if isinstance(core, ActionFormattingWrapper):
            action_fmt = core
        core = core.env
    return core, action_fmt


def install_crash_guard(core):
    pass                                                                                                     
                                                                                                           
                                                                                                      
                                                                                                          
       
    orig = core._parse_action

    def guarded(response_str):
        try:
            atype, arg = orig(response_str)
        except IndexError:
            chunks = re.findall(r"\[([^\[\]]+)\]", response_str.replace("[GAME]", " "))
            raise _CoupInvalid(core.m("err", "unrecognized", cmd=chunks[-1].strip().lower() if chunks else ""))
        if atype in DIRECTED and not (0 <= arg < core.state.num_players):
            raise _CoupInvalid(core.m("err", "directed_target", token=atype.value))
        return atype, arg

    core._parse_action = guarded
    return orig


def read_player_action():
    line = sys.stdin.readline()
    if not line:
        raise EOFError("stdin closed while waiting for the Player's action")
    msg = json.loads(line)
    if not isinstance(msg, dict) or not isinstance(msg.get("action"), str):
        raise ValueError('expected one JSON line {"action": <string>}')
    return msg["action"]


def main():
    if len(sys.argv) != 2:
        print("usage: env/bin/python coup_bridge.py <game_index 0..39>", file=sys.stderr)
        return 64
    game = int(sys.argv[1])
    if not 0 <= game < NUM_GAMES:
        print(f"game_index must be in 0..{NUM_GAMES - 1}", file=sys.stderr)
        return 64
    seat = game % NUM_PLAYERS
    seed = SEED_BASE + game
    stub = os.environ.get("COUP_STUB_OPPONENTS") == "1"
    log_path = os.environ.get("COUP_LOG") or os.path.join(HERE, "logs", "opponents.jsonl")
    if not os.path.isabs(log_path):
        log_path = os.path.join(HERE, log_path)
    max_steps = int(os.environ.get("COUP_DEBUG_MAX_STEPS", "0"))                                         

    env = ta.make(ENV_ID)
    env.reset(num_players=NUM_PLAYERS, seed=seed)
    core, action_fmt = unwrap(env)
    raw_parse = install_crash_guard(core)

    invalid = {p: 0 for p in range(NUM_PLAYERS)}
    _orig_siv = core.state.set_invalid_move

    def counting_set_invalid_move(reason):                                           
        invalid[core.state.current_player_id] += 1
        return _orig_siv(reason)

    core.state.set_invalid_move = counting_set_invalid_move

    opponents = StubOpponents(core, game, log_path) if stub else CodexOpponents(game, log_path)
    stats = PlayerStats(seat)
    log(f"game {game}: seed {seed}, player seat {seat}, opponents {'STUB' if stub else OPP_MODEL}")

    player_decisions, steps = 0, 0
    elimination_order = []
    done = False
    t_start = time.time()
    try:
        while not done:
            pid, observation = env.get_observation()
            env_turn = core.state.turn
            if pid == seat:
                emit({"kind": "player_request", "message": observation, "seat": seat})
                action = read_player_action()
                player_decisions += 1
            else:
                action = opponents(pid, observation, env_turn)
            pre = PlayerStats.snapshot(core)
            before = invalid[pid]
            try:
                parsed = raw_parse(action_fmt.action(action) if action_fmt else action)
            except Exception:                
                parsed = None
            done, _info = env.step(action)
            stats.update(pre, parsed, invalid[pid] == before, core)
            for p in range(NUM_PLAYERS):
                if p not in elimination_order and not core.state.game_state["hidden_hand"][p]:
                    elimination_order.append(p)
            steps += 1
            if max_steps and steps >= max_steps and not done:
                log(f"COUP_DEBUG_MAX_STEPS={max_steps} reached; stopping (debug run, no terminal record)")
                emit({"kind": "error", "error": "debug step cap reached", "game": game, "steps": steps})
                return 4
    except OpponentFailure as exc:
        emit({"kind": "error", "error": "opponent_failure", "detail": str(exc), "game": game,
              "playerSeat": seat, "envTurn": core.state.turn})
        return 3
    except (EOFError, ValueError) as exc:
        emit({"kind": "error", "error": "player_io", "detail": str(exc), "game": game,
              "playerSeat": seat, "envTurn": core.state.turn})
        return 2

    rewards, game_info = env.close()
    rewards = {str(k): v for k, v in (rewards or {}).items()}
    winners = [int(k) for k, v in rewards.items() if v == 1]
    winner = winners[0] if len(winners) == 1 else None
    gs = core.state.game_state
    emit({
        "kind": "terminal",
        "game": game,
        "seed": seed,
        "envId": ENV_ID,
        "rewards": rewards,
        "winner": winner,
        "playerSeat": seat,
        "playerWon": winner == seat,
        "turns": core.state.turn,
        "playerDecisions": player_decisions,
        "invalidMoves": {str(k): v for k, v in invalid.items()},
        "forfeitedByInvalid": [p for p in range(NUM_PLAYERS) if game_info[p].get("invalid_move")],
        "eliminationOrder": elimination_order,
        "gameInfo": {str(k): v for k, v in game_info.items()},
        "finalState": {"coins": {str(p): c for p, c in gs["coins"].items()},
                       "revealed": {str(p): list(h) for p, h in gs["revealed_hand"].items()},
                       "hidden": {str(p): list(h) for p, h in gs["hidden_hand"].items()}},
        "stats": stats.result(),
        "statsEvents": stats.events,
        "opponentCalls": opponents.calls,
        "opponents": "stub" if stub else OPP_MODEL,
        "wallSec": round(time.time() - t_start, 1),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
