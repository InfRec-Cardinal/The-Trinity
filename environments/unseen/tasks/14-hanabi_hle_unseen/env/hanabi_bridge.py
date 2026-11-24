                                                                                         
                                                                                           
                                                                                  
                                                                
import json, sys
from hanabi_learning_environment import rl_env
from hanabi_learning_environment.agents.simple_agent import SimpleAgent

PROTO = sys.stdout
sys.stdout = sys.stderr
n, seed, h0 = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
env = rl_env.HanabiEnv(config={"colors": 5, "ranks": 5, "players": n, "max_information_tokens": 8, "max_life_tokens": 3, "seed": seed})
partners = {p: SimpleAgent({"players": n}) for p in range(n) if p != h0}
obs = env.reset()
turn = 0

def emit(o):
    PROTO.write(json.dumps(o) + "\n"); PROTO.flush()

done = False
while not done:
    cp = obs["current_player"]; po = obs["player_observations"][cp]
    if cp == h0:
        pyobs = po["pyhanabi"]
        legal = [str(m) for m in pyobs.legal_moves()]
        assert len(legal) == len(po["legal_moves"])
        text = (f"You are player {h0} of {n} (the official observation shows your own hand first, as 'Cur player'; other hands follow in seat order).\n"
                f"Turn {turn}.\n{str(pyobs)}\nLast moves (most recent first): {[str(m) for m in pyobs.last_moves()][:2*n]}\n"
                "Legal moves:\n" + "\n".join(f"{i}: {s}" for i, s in enumerate(legal)))
        emit({"kind": "player_request", "turn": turn, "message": text, "legalCount": len(legal)})
        line = sys.stdin.readline()
        if not line: raise SystemExit("player stream closed")
        idx = json.loads(line).get("move")
        invalid = not (isinstance(idx, int) and 0 <= idx < len(legal))
        if invalid: idx = 0                                                      
        action = po["legal_moves"][idx]
    else:
        action = partners[cp].act(po)
    obs, reward, done, _ = env.step(action)
    turn += 1
st = env.state
emit({"kind": "terminal", "score": st.score(), "fireworks": [f for f in st.fireworks()], "lifeTokens": st.life_tokens(),
      "informationTokens": st.information_tokens(), "turns": turn, "deckSize": st.deck_size()})
