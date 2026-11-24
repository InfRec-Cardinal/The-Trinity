#!/usr/bin/env python3
                                                                           

      
                                                      

                                                                  
                                                                         
                                                                  

                                                                           
                                                              

                                                                              
                                                  
                                                                          
                                                                    
                                                                      

            
                                                          
                                                         
                                                                     
                                                                           
                                                                               
                                                              
                                                                             
   

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

                                       
import pyspiel              
from game_arena.harness import model_generation              
from game_arena.harness import telemetry              
from game_arena.harness.games.poker import poker_agents              

                                                                             
                    
                                  
                                                                 
                                                                             
                                                                             
UNIVERSAL_POKER_GAME_STRING = (
    "universal_poker("
    "betting=nolimit,"
    "bettingAbstraction=fullgame,"
    "blind=2 1,"
    "firstPlayer=2 1 1 1,"
    "numBoardCards=0 3 1 1,"
    "numHoleCards=2,"
    "numPlayers=2,"
    "numRanks=13,"
    "numRounds=4,"
    "numSuits=4,"
    "stack=200 200)"
)
REPEATED_POKER_GAME_STRING = (
    "repeated_poker("
    "max_num_hands=100,"
    "reset_stacks=True,"
    "rotate_dealer=True,"
    f"universal_poker_game_string={UNIVERSAL_POKER_GAME_STRING})"
)
BIG_BLIND = 2
NUM_EPISODES = 20
PRESET_FILE = ROOT / "official" / "preset_hands.jsonl"

CODEX_BIN = os.environ.get("H0_OPPONENT_CODEX_BIN", "codex")                                                                   
CODEX_MODEL = "gpt-5.6-luna"
CODEX_TIMEOUT_S = 180
CODEX_MAX_RETRIES = 3                                                    

STUB_REPLY = "Stub opponent.\nFinal Answer: call"


def log(*args):
  print("[poker_bridge]", *args, file=sys.stderr, flush=True)


def emit(record: dict) -> None:
  sys.stdout.write(json.dumps(record) + "\n")
  sys.stdout.flush()


def now_iso() -> str:
  return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")


class FatalBridgeError(Exception):
  pass                                                                      

  def __init__(self, msg: str, exit_code: int):
    super().__init__(msg)
    self.exit_code = exit_code


                                                                             
                                                                            
                                                                             
class Ctx:
  episode = -1
  hand = -1
  legal: list[str] = []
  attempt = 0
  role = ""


                                                                             
                                                                           
                                                                
                                                                             
class IllegalCounter:

  def __init__(self):
    self.events: list[dict] = []

  def send(self, module: str, **kwargs):
    del module
    if "rethinking_attempt" in kwargs:
      self.events.append({"role": Ctx.role, "hand": Ctx.hand, "type": "retry"})
    if "illegal_action" in kwargs:
      self.events.append(
          {"role": Ctx.role, "hand": Ctx.hand, "type": "fallback",
           "default_action": kwargs["illegal_action"].get("default_action")})


COUNTER = IllegalCounter()
telemetry.set_exporter(COUNTER.send)


                                                                             
                                                              
                                                                             
class StdioPlayerModel:
  pass                                                                            

  def __init__(self):
    self.fatal: FatalBridgeError | None = None
    self.calls = 0

  def generate_with_text_input(self, model_input, **unused):
    self.calls += 1
    is_retry = "A legal action could not be parsed" in model_input.prompt_text
    emit({
        "kind": "player_request",
        "episode": Ctx.episode,
        "hand": Ctx.hand,
        "legal": list(Ctx.legal),
        "retry": is_retry,
        "message": model_input.prompt_text,
    })
    line = sys.stdin.readline()
    if not line:
      self.fatal = FatalBridgeError("stdin closed while waiting for Player", 2)
      raise self.fatal
    try:
      reply = json.loads(line)
      text = reply["action"]
      if text is None:
        text = ""
      if not isinstance(text, str):
        text = str(text)
    except Exception as e:                                
      self.fatal = FatalBridgeError(f"bad Player reply line: {e}", 2)
      raise self.fatal
    return model_generation.GenerateReturn(
        main_response=text, main_response_and_thoughts=text)


class CodexOpponentModel:
  pass                                                    

  def __init__(self, episode: int, stub: bool):
    self.stub = stub
    self.fatal: FatalBridgeError | None = None
    self.calls = 0
    self.scratch = pathlib.Path(os.environ.get("H0_BRIDGE_SCRATCH", str(ROOT / "scratch"))) / "codex" / f"ep{episode:02d}"
    self.scratch.mkdir(parents=True, exist_ok=True)
    self.log_path = pathlib.Path(
        os.environ.get("POKER_LOG", str(ROOT / "logs" / "opponents.jsonl")))
    if not self.log_path.is_absolute():
      self.log_path = ROOT / self.log_path
    self.log_path.parent.mkdir(parents=True, exist_ok=True)
    self.full_prompt = os.environ.get("POKER_LOG_FULL_PROMPT") == "1"

  def _log(self, rec: dict):
    with open(self.log_path, "a", encoding="utf-8") as f:
      f.write(json.dumps(rec) + "\n")

  def generate_with_text_input(self, model_input, **unused):
    self.calls += 1
    prompt = model_input.prompt_text
    is_retry = "A legal action could not be parsed" in prompt
    base = {
        "ts": now_iso(), "episode": Ctx.episode, "hand": Ctx.hand,
        "retry": is_retry, "model": CODEX_MODEL, "stub": self.stub,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt_chars": len(prompt), "legal": list(Ctx.legal),
    }
    if self.full_prompt:
      base["prompt"] = prompt
    else:
      idx = prompt.rfind("Current hand:")
      base["prompt_tail"] = prompt[idx:] if idx >= 0 else prompt[-3000:]
    if self.stub:
      self._log({**base, "attempts": [], "reply": STUB_REPLY, "ok": True,
                 "latency_s": 0.0})
      return model_generation.GenerateReturn(
          main_response=STUB_REPLY, main_response_and_thoughts=STUB_REPLY)

    attempts = []
    t_total = time.monotonic()
    for attempt in range(CODEX_MAX_RETRIES + 1):
      outfile = self.scratch / f"reply-{uuid.uuid4().hex}.txt"
      cmd = ([sys.executable, CODEX_BIN] if CODEX_BIN.endswith(".py") else [CODEX_BIN]) + ["exec", "--skip-git-repo-check", "-s", "read-only",
             "-m", CODEX_MODEL, "-c", "model_reasoning_effort=low",
             "-o", str(outfile), prompt]
      t0 = time.monotonic()
      rec = {"attempt": attempt}
      try:
        proc = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=str(self.scratch),
            timeout=CODEX_TIMEOUT_S, check=False)
        rec["returncode"] = proc.returncode
        rec["stderr_tail"] = proc.stderr.decode("utf-8", "replace")[-400:]
      except subprocess.TimeoutExpired:
        rec["returncode"] = None
        rec["timeout"] = True
      rec["latency_s"] = round(time.monotonic() - t0, 3)
      reply = None
      if outfile.exists():
        reply = outfile.read_text(encoding="utf-8", errors="replace")
        outfile.unlink()
      ok = rec.get("returncode") == 0 and reply is not None and reply.strip()
      rec["ok"] = bool(ok)
      attempts.append(rec)
      if ok:
        self._log({**base, "attempts": attempts, "reply": reply, "ok": True,
                   "latency_s": rec["latency_s"],
                   "total_latency_s": round(time.monotonic() - t_total, 3)})
        return model_generation.GenerateReturn(
            main_response=reply, main_response_and_thoughts=reply)
      log(f"codex attempt {attempt} failed (rc={rec.get('returncode')}, "
          f"timeout={rec.get('timeout', False)})")
    self._log({**base, "attempts": attempts, "reply": None, "ok": False,
               "total_latency_s": round(time.monotonic() - t_total, 3)})
    self.fatal = FatalBridgeError(
        f"Codex failed {CODEX_MAX_RETRIES + 1} times (hand {Ctx.hand})", 3)
    raise self.fatal


                                                                             
                                                      
                                                                             
def load_preset(pair: int) -> list[list[int]]:
  with open(PRESET_FILE, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
      if i == pair:
        return json.loads(line)["presetHands"]
  raise ValueError(f"no preset line {pair}")


class PresetDealer:
  pass                                                                       

  def __init__(self, hands: list[list[int]]):
    self.hands = [tuple(h) for h in hands]
    self.next_index = [0] * len(hands)

  def action(self, state) -> int:
    outcomes = [a for a, _ in state.chance_outcomes()]
    hand_idx = len(state.acpc_hand_histories())
    hand_actions = self.hands[hand_idx]
    pos = self.next_index[hand_idx]
    if pos >= len(hand_actions):
      raise ValueError(f"preset hand {hand_idx} exhausted")
    a = hand_actions[pos]
    if a not in outcomes:
      raise ValueError(f"preset action {a} not legal in hand {hand_idx}")
    self.next_index[hand_idx] = pos + 1
    return a


def state_dict(state) -> dict:
  return json.loads(str(state))


def hand_summary(state, h: int, player_id: int) -> dict:
  pass                                                                       
  sd = state_dict(state)
  hists = state.acpc_hand_histories()
  acpc = hists[h] if h < len(hists) else None
  prev = sd.get("prev_universal_poker_json") or ""
  info = {}
  if h == len(hists) - 1 and prev:
    up = json.loads(prev)
    info = {"board": up.get("board_cards"), "holes": up.get("player_hands"),
            "pot": up.get("pot_size")}
  return {"acpc": acpc, **info}


                                                                             
               
                                                                             
def main() -> int:
  if len(sys.argv) != 2:
    print(__doc__, file=sys.stderr)
    return 64
  episode = int(sys.argv[1])
  if not 0 <= episode < NUM_EPISODES:
    print("episode_index must be in 0..19", file=sys.stderr)
    return 64
  pair, player_id = episode // 2, episode % 2
  opp_id = 1 - player_id
  n_hands = int(os.environ.get("POKER_HANDS", "100"))
  start_hand = int(os.environ.get("POKER_START_HAND", "0"))
  stub = os.environ.get("POKER_STUB_OPPONENT") == "1"
  state_dir = pathlib.Path(os.environ.get("POKER_STATE_DIR", str(ROOT / "state")))
  if not state_dir.is_absolute():
    state_dir = ROOT / state_dir
  state_dir.mkdir(parents=True, exist_ok=True)
  ckpt = state_dir / f"ep{episode:02d}.json"
  Ctx.episode = episode

  game = pyspiel.load_game(REPEATED_POKER_GAME_STRING)
  state = game.new_initial_state()
  dealer = PresetDealer(load_preset(pair))

  player_model = StdioPlayerModel()
  opp_model = CodexOpponentModel(episode, stub)
  agents = {
      player_id: poker_agents.build_repeated_poker_rethink_agent(player_model),
      opp_id: poker_agents.build_repeated_poker_rethink_agent(opp_model),
  }
  models = {player_id: player_model, opp_id: opp_model}

  per_hand: list[dict] = []
                                                                            
  if start_hand > 0:
    prior_path = os.environ.get("POKER_PRIOR")
    if not prior_path:
      print("POKER_START_HAND>0 requires POKER_PRIOR", file=sys.stderr)
      return 64
    prior = json.loads(pathlib.Path(prior_path).read_text())
    if isinstance(prior, dict):
      prior = prior.get("perHand", [])
    prior = sorted(prior, key=lambda r: r["hand"])[:start_hand]
    if [r["hand"] for r in prior] != list(range(start_hand)):
      print("POKER_PRIOR must contain hands 0..START_HAND-1", file=sys.stderr)
      return 64
    for r in prior:
      if r.get("episode", episode) != episode:
        print("POKER_PRIOR is for a different episode", file=sys.stderr)
        return 64
      for a in r["actions"]:
        state.apply_action(a)
      hr = state_dict(state)["hand_returns"][r["hand"]]
      if hr[player_id] != r["playerChips"]:
        print(f"replay mismatch at hand {r['hand']}", file=sys.stderr)
        return 65
      per_hand.append(r)
                                                                            
                                                                              
    log(f"resumed episode {episode} at hand {start_hand} "
        f"({len(per_hand)} prior hands replayed)")

  def checkpoint():
    tmp = ckpt.with_suffix(".tmp")
    tmp.write_text(json.dumps({"episode": episode, "perHand": per_hand}))
    os.replace(tmp, ckpt)

  def history_len():
    return len(state.history())

  hand_start_hist = history_len()
  cur_hand = start_hand
  dec_counts = {"player": 0, "opponent": 0}                     
  hand_dealer: dict[int, int] = {}
  hand_decisions = {"player": 0, "opponent": 0}

  def finish_hand(h: int):
    nonlocal hand_start_hist
    sd = state_dict(state)
    ret = sd["hand_returns"][h]
    acts = list(state.history()[hand_start_hist:])
                                                                             
                                                                         
                                                                              
    hand_start_hist = history_len()
    ev = [e for e in COUNTER.events if e["hand"] == h]
    sm = hand_summary(state, h, player_id)
    rec = {
        "kind": "hand_result", "episode": episode, "pair": pair, "hand": h,
        "playerId": player_id,
                                                                              
        "playerIsButton": hand_dealer.get(h) == player_id,
        "playerChips": ret[player_id], "opponentChips": ret[opp_id],
        "actions": acts, **sm,
        "decisions": dict(hand_decisions),
        "illegal": {
            "playerRetries": sum(1 for e in ev if e["role"] == "player" and e["type"] == "retry"),
            "playerFallbacks": sum(1 for e in ev if e["role"] == "player" and e["type"] == "fallback"),
            "opponentRetries": sum(1 for e in ev if e["role"] == "opponent" and e["type"] == "retry"),
            "opponentFallbacks": sum(1 for e in ev if e["role"] == "opponent" and e["type"] == "fallback"),
        },
    }
    hand_decisions.update(player=0, opponent=0)
    per_hand.append(rec)
    checkpoint()
    emit(rec)

  try:
    while cur_hand < n_hands and not state.is_terminal():
      if state.is_chance_node():
        state.apply_action(dealer.action(state))
        continue
      cp = state.current_player()
      if cur_hand not in hand_dealer:
        hand_dealer[cur_hand] = state_dict(state)["dealer"]
      Ctx.hand = cur_hand
      Ctx.role = "player" if cp == player_id else "opponent"
      Ctx.legal = [state.action_to_string(cp, a) for a in state.legal_actions()]
      obs = {
          "serializedGameAndState": pyspiel.serialize_game_and_state(game, state),
          "currentPlayer": cp,
          "playerId": cp,
      }
      out = agents[cp](obs, {})
      if models[cp].fatal is not None:
        raise models[cp].fatal
      sub = out["submission"]
      if sub not in state.legal_actions():
        raise FatalBridgeError(f"agent returned non-legal submission {out}", 3)
      dec_counts[Ctx.role] += 1
      hand_decisions[Ctx.role] += 1
      state.apply_action(sub)
      if len(state.acpc_hand_histories()) > cur_hand:
        finish_hand(cur_hand)
        cur_hand += 1
  except FatalBridgeError as e:
    emit({"kind": "error", "episode": episode, "hand": Ctx.hand,
          "message": str(e), "completedHands": len(per_hand),
          "resume": {"POKER_START_HAND": len(per_hand),
                     "POKER_PRIOR": str(ckpt)}})
    log("FATAL:", e)
    return e.exit_code

  total = sum(r["playerChips"] for r in per_hand)
  hands = len(per_hand)
  ill = {k: sum(r["illegal"][k] for r in per_hand)
         for k in ("playerRetries", "playerFallbacks",
                   "opponentRetries", "opponentFallbacks")}
  emit({
      "kind": "terminal", "episode": episode, "pair": pair,
      "seat": {"playerId": player_id,
               "note": "player_id 0 in even episodes, 1 in odd (duplicate)"},
      "hands": hands,
      "playerChipDelta": total,
      "bbPer100": (total / BIG_BLIND) / hands * 100 if hands else None,
      "illegal": ill,
      "decisions": {k: sum(r.get("decisions", {}).get(k, 0) for r in per_hand)
                    for k in ("player", "opponent")},
      "opponent": {"model": CODEX_MODEL, "stub": stub},
      "presetLine": pair,
      "gameString": REPEATED_POKER_GAME_STRING,
      "perHand": per_hand,
  })
  return 0


if __name__ == "__main__":
  sys.exit(main())
