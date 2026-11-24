                                                                                                       

                                                                                                      
                                                               

                                                                                                                              
                                                                                                                         
                                                                                                                            
                                                                                                                         
                                                                                                                          
                                                     
   
import asyncio
import contextlib
import io
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))                                                  
SRC = os.environ.get("AGENTB_AMONG_US_SRC") or os.path.join(ROOT, "vendor", "among-us")                                        
sys.path.insert(0, SRC)
os.environ.setdefault("EXPERIMENT_PATH", os.environ.get("TMPDIR", "/tmp"))
os.environ["FLASK_ENABLED"] = "False"

import numpy as np              
from amongagents.agent.agent import Agent              
from amongagents.agent.neutral_prompts import CREWMATE_EXAMPLE, CREWMATE_PROMPT, IMPOSTOR_EXAMPLE, IMPOSTOR_PROMPT              
from amongagents.envs.configs.agent_config import ALL_RANDOM              
from amongagents.envs.configs.game_config import SEVEN_MEMBER_GAME              
from amongagents.envs.game import AmongUs              

WINNER_REASON = {1: "Impostors win! (Crewmates being outnumbered or tied to impostors))", 2: "Crewmates win! (Impostors eliminated)",
                 3: "Crewmates win! (All task completed)", 4: "Impostors win! (Time limit reached)"}


class NeedDecision(Exception):
    pass


def official_match(available_actions, output_action):
    pass                                                                                                                    
    action = None
    for action in available_actions:
        if repr(action) in output_action:
            return action, True
        elif "SPEAK: " in repr(action) and "SPEAK: " in output_action:
            message = output_action.split("SPEAK: ")[1]
            action.message = message
            return action, True
        else:
            action.message = '...'
    return action, False


class PlayerSeat(Agent):
    def __init__(self, player, queue, impostors, log):
        super().__init__(player)
        self.model = "agentb/player-seat"
        self.queue = queue
        self.impostors = impostors
        self.log = log
        self.room = None

    def system_prompt(self):
        if self.player.identity == "Impostor":
            return IMPOSTOR_PROMPT.format(name=self.player.name) + IMPOSTOR_EXAMPLE + f"List of impostors: {self.impostors}"
        return CREWMATE_PROMPT.format(name=self.player.name) + CREWMATE_EXAMPLE

    async def choose_action(self, timestep):
        available = self.player.get_available_actions()
        if not self.queue:
            phase = "Meeting phase" if len(available) == 1 or all(a.name == "VOTE" for a in available) else "Task phase"
            raise NeedDecision({"timestep": timestep, "phase": phase, "allInfo": self.player.all_info_prompt(), "system": self.system_prompt(),
                                "available": [repr(a) for a in available]})
        submitted = self.queue.pop(0)
                                                                                                                         
        pattern = r"^\[Condensed Memory\]((.|\n)*)\[Thinking Process\]((.|\n)*)\[Action\]((.|\n)*)$"
        match = re.search(pattern, submitted["action"])
        output_action = match.group(5).strip() if match else submitted["action"].strip()
        action, matched = official_match(available, output_action)
        self.room = submitted.get("room")
        self.log.append({"timestep": timestep, "submitted": submitted["action"], "chosen": repr(action), "matched": matched})
        return action

    def choose_observation_location(self, map):
        rooms = list(map)
        if self.room in rooms:
            return self.room
        return random.choice(rooms)                                                     


class OpponentSeat(Agent):
    pass                                                                                                                       

    def __init__(self, player, game, seed, index, impostors):
        super().__init__(player)
        self.model = "agentb/seeded-heuristic"
        self.game = game
        self.rng = random.Random(seed * 1009 + index * 7919)
        self.impostors = impostors
        self.suspects = {}
        self.seen = 0
        self.last_kill_room = None
        self.last_task_room = "Cafeteria"
        self.meeting_key = None
        self.meeting_statement = ""

    def absorb(self):
        for message in self.player.observation_history[self.seen:]:
            for p in self.game.players:
                if p.name in message and p is not self.player:
                    if "KILL" in message:
                        self.suspects[p.name] = self.suspects.get(p.name, 0) + 10
                    elif "VENT" in message:
                        self.suspects[p.name] = self.suspects.get(p.name, 0) + 6
                    elif "SPEAK" in message and "suspect" in message:
                        for q in self.game.players:
                            if q.name in message.split("suspect", 1)[1]:
                                self.suspects[q.name] = self.suspects.get(q.name, 0) + 1
        self.seen = len(self.player.observation_history)

    def choose_observation_location(self, map):
        return self.rng.choice(sorted(map))

    async def choose_action(self, timestep):
        self.absorb()
        if self.game.current_phase == "task":
            self.last_task_room = self.player.location
        avail = self.player.get_available_actions()
        names = [a.name for a in avail]
        impostor = self.player.identity == "Impostor"
        alive = [p for p in self.game.players if p.is_alive and p is not self.player]
        if "SPEAK" in names:
            speak = next(a for a in avail if a.name == "SPEAK")
                                                                                                                              
                                                                                                                              
                                                                                                                               
            if self.meeting_key != self.game.timestep:
                self.meeting_key = self.game.timestep
                top = max(self.suspects.items(), key=lambda kv: kv[1], default=None)
                others = [p for p in alive if not (impostor and p.name in self.impostors)]
                if impostor:
                    room = self.last_task_room if self.rng.random() < 0.6 else self.rng.choice(sorted(self.game.map.ship_map.nodes))
                else:
                    room = self.last_task_room
                if top and top[1] >= 6 and not (impostor and top[0] in self.impostors):
                    target = top[0]
                elif others and self.rng.random() < 0.3:
                    target = self.rng.choice(sorted(p.name for p in others))
                else:
                    target = None
                self.meeting_statement = f"I was in {room} doing my tasks." + (f" I suspect {target}." if target else " I have no strong evidence yet.")
            speak.provide_message(self.meeting_statement)
            return speak
        if "VOTE" in names:
            votes = [a for a in avail if a.name == "VOTE"]
            if impostor:
                pool = [a for a in votes if a.other_player.name not in self.impostors] or votes
                return max(pool, key=lambda a: self.suspects.get(a.other_player.name, 0) + self.rng.random())
            return max(votes, key=lambda a: self.suspects.get(a.other_player.name, 0) + 2 * self.rng.random())
        room = self.game.map.get_players_in_room(self.player.location)
        others = [p for p in room if p is not self.player and p.is_alive]
        if impostor:
            kills = [a for a in avail if a.name == "KILL"]
            crew_here = [p for p in others if p.identity == "Crewmate"]
            if kills and len(crew_here) == 1 and self.rng.random() < 0.6:
                self.last_kill_room = self.player.location
                return kills[0]
            vents = [a for a in avail if a.name == "VENT"]
            if vents and self.last_kill_room == self.player.location and self.rng.random() < 0.7:
                return self.rng.choice(vents)
            fakes = [a for a in avail if a.name == "COMPLETE FAKE TASK"]
            if fakes and self.rng.random() < 0.35:
                return fakes[0]
            moves = [a for a in avail if a.name == "MOVE"]
            if moves:
                return self.rng.choice(moves)
            return avail[-1]
        bodies = [p for p in self.game.map.get_players_in_room(self.player.location, include_new_deaths=True) if not p.is_alive and not p.reported_death]
        reports = [a for a in avail if a.name == "CALL MEETING"]
        if reports and (bodies or "REPORT" in repr(reports[0])):
            return reports[0]
        top = max(self.suspects.values(), default=0)
        button = [a for a in avail if a.name == "CALL MEETING" and "emergency" in repr(a)]
        if button and top >= 10:
            return button[0]
        tasks = [a for a in avail if a.name == "COMPLETE TASK"]
        if tasks:
            return tasks[0]
        pending = [t for t in self.player.tasks if not t.check_completion()]
        moves = [a for a in avail if a.name == "MOVE"]
        if pending and moves:
            target = min(pending, key=lambda t: len(t.find_path(self.player.location, identity=self.player.identity)))
            path = target.find_path(self.player.location, identity=self.player.identity)
            if len(path) > 1:
                for a in moves:
                    if a.new_location == path[1]:
                        return a
        if top >= 10 and moves:
            path_home = [a for a in moves if a.new_location == "Cafeteria"]
            if path_home:
                return path_home[0]
        return self.rng.choice(moves) if moves else avail[-1]


def run(instance, actions):
    seed, seat = instance["seed"], instance["seat"]
    random.seed(seed)
    np.random.seed(seed)
    queue = [dict(a) for a in actions]
    decisions = []
    game = AmongUs(game_config=SEVEN_MEMBER_GAME, agent_config=ALL_RANDOM, game_index=seed)

    def initialize_agents():
        np.random.choice(len(game.players))                                                                                    
        game.list_of_impostors = [p.name for p in game.players if p.identity == "Impostor"]
        game.agents = []
        for i, player in enumerate(game.players):
            if i == seat:
                game.agents.append(PlayerSeat(player, queue, list(game.list_of_impostors), decisions))
            else:
                game.agents.append(OpponentSeat(player, game, seed, i, list(game.list_of_impostors)))
    game.initialize_agents = initialize_agents

    need = None
    with contextlib.redirect_stdout(io.StringIO()):
        game.initialize_game()
        code = game.check_game_over()

        async def loop():
            nonlocal code
            while not code:
                await game.game_step()
                code = game.check_game_over()
        try:
            asyncio.run(loop())
        except NeedDecision as stop:
            need = stop.args[0]
    if queue:
        raise ValueError("actions submitted after the episode ended")
    me = game.players[seat]
    state = {"timestep": game.timestep, "phase": game.current_phase, "seatIdentity": me.identity, "seatAlive": me.is_alive,
             "identities": [p.identity for p in game.players], "alive": [p.is_alive for p in game.players], "locations": [p.location for p in game.players],
             "taskCompletion": game.task_assignment.check_task_completion(), "buttons": game.button_num, "decisions": decisions,
             "importantLog": [str(e.get("action")) if isinstance(e, dict) else str(e) for e in game.important_activity_log][-20:]}
    if need is not None:
        text = (need["system"] + "\n\n" + need["allInfo"] + f"\nPhase: {need['phase']}. Return your output.\n\n"
                "Submit your output as text. An answer in the output format above is parsed by its [Action] section, exactly as the released agent does; a bare action such as "
                "\"MOVE from Cafeteria to Weapons\", \"VOTE Player 3: blue\" or \"SPEAK: <your statement>\" is matched directly. VIEW MONITOR may name a room. Text matching no available action falls back to the last listed action, as in the released agent.")
        last = decisions[-1] if decisions else None
        info = {"timestep": need["timestep"], "phase": need["phase"], "available": need["available"], "lastSubmissionMatched": last["matched"] if last else None}
        return {"ok": True, "state": state, "text": text, "reward": 0, "info": info, "terminal": {"ended": False, "outcome": None, "reason": None}}
    seat_side_wins = (code in (1, 4)) == (me.identity == "Impostor")
    terminal = {"ended": True, "outcome": "success" if seat_side_wins else "failure", "reason": WINNER_REASON[code], "score": 1 if seat_side_wins else 0,
                "evaluation": {"winnerCode": code, "winnerReason": WINNER_REASON[code], "seatIdentity": me.identity, "seatAlive": me.is_alive, "timesteps": game.timestep,
                               "seatDecisions": len(decisions), "unmatchedSubmissions": sum(1 for d in decisions if not d["matched"]),
                               "identities": state["identities"], "taskCompletion": state["taskCompletion"]}}
    text = (f"GAME OVER at timestep {game.timestep}: {WINNER_REASON[code]} You were {me.name} ({me.identity}). "
            f"Your side {'wins' if seat_side_wins else 'loses'}.")
    return {"ok": True, "state": state, "text": text, "reward": 1 if seat_side_wins else 0, "info": {"winnerCode": code}, "terminal": terminal}


def session(request_fifo, response_fifo, idle_seconds):
    pass                                                                                                                   
    import select
    instance = json.loads(os.environ["AGENTB_INSTANCE"])
    actions = []
    req = open(request_fifo, "r")                                                                                   
    resp = open(response_fifo, "w")

    def emit(out):
        resp.write(json.dumps(out) + "\n")
        resp.flush()

    def safe_run():
        try:
            return run(instance, list(actions))
        except Exception as error:
            return {"ok": False, "message": f"{type(error).__name__}: {error}"}
    emit(safe_run())
    while True:
        ready, _, _ = select.select([req], [], [], idle_seconds)
        if not ready:
            return
        line = req.readline()
        if not line:
            return
        actions.append(json.loads(line))
        out = safe_run()
        if not out.get("ok"):
            actions.pop()
        emit(out)


def main():
    if len(sys.argv) >= 3:
        session(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 90.0)
        return
    request = json.loads(sys.stdin.read())
    try:
        out = run(request["instance"], request.get("actions", []))
    except Exception as error:                                                     
        out = {"ok": False, "message": f"{type(error).__name__}: {error}"}
    sys.stdout.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
