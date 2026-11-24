import re


class Action:
    def __init__(self, name, current_location=None):
        self.name = name
        self.current_location = current_location

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def execute(self, env, player):
        return

    def action_text(self):
        return str(self)

    @staticmethod
    def can_execute_actions(env, player):
        return []


class MoveTo(Action):
    def __init__(self, current_location, new_location):
        super().__init__("MOVE", current_location=current_location)
        self.new_location = new_location

    def __repr__(self):
        return f"{self.name} from {self.current_location} to {self.new_location}"

    def execute(self, env, player):
        super().execute(env, player)
        player.location = self.new_location

    @staticmethod
    def can_execute_actions(env, player):
        if env.current_phase == "task":
            new_locations = env.map.get_adjacent_rooms(player.location)
            return [MoveTo(player.location, location) for location in new_locations]
        else:
            return []


class Vent(MoveTo):
    def __init__(self, current_location, new_location):
        super().__init__(current_location, new_location)
        self.name = "VENT"

    @staticmethod
    def can_execute_actions(env, player):
        if env.current_phase == "task":
            new_locations = env.map.get_adjacent_rooms_vent(player.location)
            return [Vent(player.location, location) for location in new_locations]
        else:
            return []


class CallMeeting(Action):
    def __init__(self, current_location):
        super().__init__("CALL MEETING", current_location=current_location)

    def __repr__(self):
        if self.current_location == "Cafeteria":
            return f"{self.name} using the emergency button at {self.current_location}"
        else:
            return f"REPORT DEAD BODY at {self.current_location}"

    def execute(self, env, player):
        super().execute(env, player)
        env.current_phase = "meeting"
        env.button_num += 1
        for player in env.players:
            if not player.is_alive and not player.reported_death:
                player.reported_death = True

    @staticmethod
    def can_execute_actions(env, player):
        if env.current_phase == "task":
            current_location = player.location
            players_in_the_same_room = env.map.get_players_in_room(
                current_location, include_new_deaths=True
            )
            other_players_in_the_same_room = [
                p for p in players_in_the_same_room if p != player
            ]
            if (
                current_location == "Cafeteria"
                and env.button_num < env.game_config["max_num_buttons"]
            ):
                return [CallMeeting(current_location=current_location)]
            else:
                for other_player in other_players_in_the_same_room:
                    if not other_player.is_alive and not other_player.reported_death:
                        return [CallMeeting(current_location=current_location)]
        return []


class Vote(Action):
    def __init__(self, current_location, other_player):
        super().__init__("VOTE", current_location=current_location)
        self.other_player = other_player

    def __repr__(self):
        return f"{self.name} {self.other_player.name}"

    def execute(self, env, player):
        super().execute(env, player)
        env.vote_info_one_round[player.name] = self.other_player.name
        env.votes[self.other_player] = env.votes.get(self.other_player, 0) + 1

    def can_execute_actions(env, player):
        if env.current_phase == "meeting" and env.discussion_rounds_left == 0:
            alive_players_excluding_self = [
                p for p in env.players if p.is_alive and p != player
            ]
            return [
                Vote(player.location, other_player)
                for other_player in alive_players_excluding_self
            ]
        else:
            return []


class Speak(Action):
    def __init__(self, current_location):
        super().__init__("SPEAK", current_location=current_location)
        self.message = "..."

    def provide_message(self, message):
        self.message = message

    def __repr__(self):
        return f"{self.name}: {self.message}"

    def execute(self, env, player):
        super().execute(env, player)
                              

    def can_execute_actions(env, player):
        if env.current_phase == "meeting" and env.discussion_rounds_left == 0:
            return []
                        
        if env.current_phase == "task":
            return []
        
        return [Speak(current_location=player.location)]


class ViewMonitor(Action):
    def __init__(self, current_location):
        super().__init__("ViewMonitor", current_location=current_location)

    def __repr__(self):
        return f"VIEW MONITOR"

    def execute(self, env, player, choose_location):
        super().execute(env, player)
        message = (
            "Monitor Record: {" + "Location: " + choose_location + ", Observation: {"
        )
        if len(env.check_monitor(choose_location)) == 0:
            message += "No one here"
        else:
            for agent in env.players:
                if agent in env.check_monitor(choose_location):
                    message += "(" + agent.name + "): "

                    pattern = r"MOVE from ([\w\s]+) to ([\w\s]+)"
                    action = str(env.camera_record[agent.name])
                    match = re.match(pattern, action)
                    if match:
                        start_location = match.group(1)
                        end_location = match.group(2)
                        action = "enter " + end_location
                    message += action + ", "

                else:
                    pattern = r"MOVE from ([\w\s]+) to ([\w\s]+)"
                    action = str(env.camera_record[agent.name])
                    print("action", action)
                    match = re.match(pattern, action)
                    if match:
                        start_location = match.group(1)
                        end_location = match.group(2)
                        print("start_location", start_location)
                        print("choose_location", choose_location)
                        if start_location == choose_location:
                            message += "(" + agent.name + "): "
                            action = "leave " + start_location
                            message += action + ", "

        message += "}}"
        print(message)
        player.observation_history.append(message)
                              

    def can_execute_actions(env, player):
        available_tasks = []
        if player.location == "Security":
            return [ViewMonitor("Security")]
        else:
            return []


class CompleteTask(Action):
    def __init__(self, current_location, task):
        super().__init__("COMPLETE TASK", current_location=current_location)
        self.task = task

    def __repr__(self):
        return f"{self.name} - {self.task.name}"

    def action_text(self):
        return f"Seemingly doing task"

    def execute(self, env, player):
        super().execute(env, player)
        self.task.do_task()
                              

    def can_execute_actions(env, player):
        available_tasks = []
        if env.current_phase == "task":
            current_location = player.location

            for task in player.tasks:
                if task.location == current_location and not task.check_completion():
                    available_tasks.append(CompleteTask(current_location, task))

        return available_tasks


class Sabotage(Action):
    def __init__(self, current_location):
        super().__init__("SABOTAGE", current_location=current_location)

    def execute(self, env, player):
        super().execute(env, player)
                              


class Kill(Action):
    def __init__(self, current_location, other_player):
        super().__init__("KILL", current_location=current_location)
        self.other_player = other_player

    def __repr__(self):
        return f"{self.name} {self.other_player.name}"

    def execute(self, env, player):
        super().execute(env, player)
        self.other_player.is_alive = False
        player.kill_cooldown = env.game_config["kill_cooldown"]

    @staticmethod
    def can_execute_actions(env, player):
        if env.current_phase == "task" and player.kill_cooldown == 0:
            current_location = player.location
            other_players = env.map.get_players_in_room(current_location)
            other_players = [p for p in other_players if p.identity != player.identity]
            return [
                Kill(current_location=current_location, other_player=p)
                for p in other_players
            ]
        else:
            return []


class CompleteFakeTask(CompleteTask):
    def __init__(self, current_location, task):
        super().__init__(current_location, task)
        self.name = "COMPLETE FAKE TASK"

    def __repr__(self):
        return f"{self.name} - {self.task.name}"

    def action_text(self):
        return f"Seemingly doing task"

    def execute(self, env, player):
        super().execute(env, player)
        self.task.do_task()                                                       

    def can_execute_actions(env, player):
        available_tasks = []
        if env.current_phase == "task":
            current_location = player.location
            for task in player.tasks:
                if task.location == current_location and not task.check_completion():
                    available_tasks.append(CompleteFakeTask(current_location, task))

        return available_tasks


COMMON_ACTIONS = [MoveTo, CallMeeting, Vote, Speak, ViewMonitor]
CREWMATE_ACTIONS = [CompleteTask]
IMPOSTER_ACTIONS = [Sabotage, Vent, Kill, CompleteFakeTask]
