#!/usr/bin/env python3
                                                                                    

                                             

                                                                                                      
                                                                                                   
                                                                                                    
                    
   
import contextlib
import hashlib
import json
from pathlib import Path
import random
import sys
import textwrap

                                                                                                 
VENDORED_PACKAGE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(VENDORED_PACKAGE.parent))
with contextlib.redirect_stdout(sys.stderr):
    import textarena as ta
    from PIL import Image, ImageDraw, ImageFont
if Path(ta.__file__).resolve().parent != VENDORED_PACKAGE:
    raise RuntimeError("textarena did not resolve to the vendored package")

ACTION_CAP = 18


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


class Bridge:
    def __init__(self):
        self.env = None
        self.step_index = 0

    def init(self, command):
        self.task = command["taskId"]
        self.configuration = command["configuration"]
        self.seat = self.configuration["seat"]
        self.run_dir = Path(command["runDir"]).resolve()
        self.episode_path = Path(command["episodePath"])
        if self.episode_path.is_absolute() or ".." in self.episode_path.parts:
            raise ValueError("Invalid episode directory")
        if self.task != "colonel_blotto" or self.seat not in (0, 1):
            raise ValueError("Unsupported exact task configuration")
        self.bot_rng = random.Random(self.configuration["opponentSeed"])
        self.env = ta.make(env_id="ColonelBlotto-v0")
        self.env.reset(num_players=2, seed=self.configuration["seed"])
        schedule_rng = random.Random(self.configuration["opponentSeed"])
        identity = {"task": self.task, "seat": self.seat,
                    "opponentAllocationSchedule": [schedule_rng.randrange(6) for _ in range(9)]}
        self.configuration_identity = digest(identity)
                                                                                                 
                                                                                                           
        self.env.state.role_mapping = {pid: role.render(_pid=pid) if hasattr(role, "render") else role
                                       for pid, role in self.env.state.role_mapping.items()}
        self.step_index = 0
        self._advance_opponent()
        return self._observation()

    def _bot_action(self):
                                                                                             
        allocations = [[0, 11, 9], [9, 0, 11], [11, 9, 0], [8, 7, 5], [5, 8, 7], [7, 5, 8]]
        allocation = allocations[self.bot_rng.randrange(len(allocations))]
        return "[" + " ".join(f"{field}{units}" for field, units in zip("ABC", allocation)) + "]"

    def _advance_opponent(self):
        turns = 0
        while not self.env.state.done and self.env.state.current_player_id != self.seat:
            self.env.get_observation()                                           
            self.env.step(action=self._bot_action())
            turns += 1
            if turns > 3:
                raise ValueError("Opponent failed to yield a valid turn")

    def _public_text(self):
        state = self.env.state
        if state.done:
                                                                               
            state.current_player_id = self.seat
        pid, observations = self.env.get_observation()
        if pid != self.seat:
            raise ValueError("Private opponent observation cannot be returned")
        if isinstance(observations, str):
            return observations
        return "\n".join(f"[{'GAME' if entry[0] == -1 else 'Player ' + str(entry[0])}] {entry[1]}" for entry in observations)

    def _observation(self):
        state = self.env.state
        ended = bool(state.done)
        score = state.rewards.get(self.seat, 0) if ended else 0
        reason = state.game_info.get(self.seat, {}).get("reason") if ended else None
        text = self._public_text()
        text += f"\nEvaluated-seat actions used: {self.step_index}/{ACTION_CAP}."
        if ended:
            text += f"\nTerminal score: {score}. {reason or ''}"
                                                                       
        state_hash = digest({"game": state.game_state, "rewards": state.rewards, "done": ended,
                             "step": self.step_index, "seat": self.seat, "publicText": text})
        relative_frame = self.episode_path / "frames" / f"frame-{self.step_index:04d}.png"
        path = self.run_dir / relative_frame
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for line in text.splitlines():
            lines.extend(textwrap.wrap(line, width=86, break_long_words=True) or [""])
        font = ImageFont.load_default(size=15)
        image = Image.new("RGB", (820, max(180, 70 + 21 * len(lines))), "#f7f8fc")
        draw = ImageDraw.Draw(image)
        draw.text((18, 12), "Colonel Blotto — official engine", fill="#203859", font=font)
        for index, line in enumerate(lines):
            draw.text((18, 44 + index * 21), line, fill="#172339", font=font)
        image.save(path)
        return {"step": self.step_index, "publicText": text, "frame": None,
                "previewFrame": {"path": relative_frame.as_posix(),
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mimeType": "image/png"},
                "stateHash": state_hash, "configurationHash": self.configuration["configurationHash"],
                "configurationIdentityHash": self.configuration_identity,
                "reward": score, "info": {"evaluatedSeat": self.seat, "actionsUsed": self.step_index},
                "instance": {"caseId": self.configuration["id"], "sourceKind": "official"},
                "terminal": {"ended": ended, "outcome": "success" if ended and score > 0 else "failure" if ended else None,
                             "reason": reason, "score": score if ended else None}}

    def _apply(self, action):
        if self.env.state.done:
            raise ValueError("The episode already ended")
        if not isinstance(action, dict) or set(action) != {"action"} or not isinstance(action["action"], str):
            raise ValueError("Expected one public text action")
        self.env.step(action=action["action"])
        self.step_index += 1
        self._advance_opponent()
        if self.step_index >= ACTION_CAP and not self.env.state.done:
            self.env.state.set_winner(player_id=1 - self.seat, reason="Declared 18-action allowance exhausted before a native win.")
        return self._observation()

    def step(self, command):
        expected = command.get("expectedStep")
        if expected is not None and self.step_index != expected:
            raise ValueError("Action sequence mismatch")
        return self._apply(command["action"])


bridge = Bridge()
for line in sys.stdin:
    command = {}
    try:
        command = json.loads(line)
        with contextlib.redirect_stdout(sys.stderr):
            if command["command"] == "init":
                result = bridge.init(command)
            elif command["command"] == "step":
                result = bridge.step(command)
            elif command["command"] == "close":
                result = None
            else:
                raise ValueError("Unknown worker command")
        print(json.dumps({"id": command["id"], "ok": True, "result": result}), flush=True)
        if command["command"] == "close":
            break
    except Exception as error:
        print(json.dumps({"id": command.get("id"), "ok": False, "message": str(error)}), flush=True)
