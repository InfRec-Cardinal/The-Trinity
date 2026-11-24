import copy
from time import time

import networkx as nx
import numpy as np
from amongagents.envs.configs.task_config import task_config


class Task:
    def __init__(self, name, duration, task_type, location, map_graph):
        self.name = name
        self.max_duration = duration
        self.duration = duration
        self.location = location
        self.task_type = task_type
        self.is_completed = False
        self.assigned = False
        self.map_graph = map_graph

    def find_path(self, start, identity):
                                          
        if identity == "Impostor":
            return nx.shortest_path(self.map_graph, start, self.location)
        else:
            return nx.shortest_path(
                self.map_graph, start, self.location, weight="weight"
            )

    def __repr__(self):
        return f"{self.task_type}: {self.name} ({self.location})"

    def __str__(self):
        return self.__repr__()

    def assign_to(self, player):
        self.assigned = True
        self.assigned_player = player

    def do_task(self):
        self.duration -= 1

    def reset_task(self):
        self.duration = self.max_duration
        self.is_completed = False
        self.assigned = False
        self.assigned_player = None

    def check_completion(self):
        if self.is_completed:
            return True
        elif self.duration <= 0:
            self.is_completed = True
        return self.is_completed


class TaskAssignment:
    def __init__(self, map_graph, game_config):
        self.map_graph = map_graph
        self.game_config = game_config
        self.tasks = []
        for room in self.map_graph.nodes:
            task_names = self.map_graph.nodes[room]["tasks"]
            self.tasks.extend(
                [
                    Task(
                        task_name,
                        task_config[task_name]["duration"],
                        task_config[task_name]["task_type"],
                        room,
                        map_graph,
                    )                                                 
                    for task_name in task_names
                ]
            )
        self.short_tasks = [task for task in self.tasks if task.task_type == "short"]
        self.long_tasks = [task for task in self.tasks if task.task_type == "long"]
        self.common_tasks = [task for task in self.tasks if task.task_type == "common"]
        self.assigned_tasks = []

    def reset_task_assignments(self):
        for task in self.tasks:
            task.reset_task()
        self.assigned_tasks = []

    def assign_tasks_to_players(self, players):

        self.reset_task_assignments()
        num_common_tasks = self.game_config["num_common_tasks"]
        selected_common_tasks = np.random.choice(
            self.common_tasks, size=(num_common_tasks,)
        )
        common_tasks_for_players = [
            copy.deepcopy(selected_common_tasks) for _ in players
        ]
        num_short_tasks = self.game_config["num_short_tasks"]
        num_long_tasks = self.game_config["num_long_tasks"]

        for i, player in enumerate(players):
            common_tasks = common_tasks_for_players[i]
            available_short_tasks = [
                task for task in self.short_tasks if not task.assigned
            ]
            available_long_tasks = [
                task for task in self.long_tasks if not task.assigned
            ]
            short_tasks = np.random.choice(available_short_tasks, num_short_tasks)
            long_tasks = np.random.choice(available_long_tasks, num_long_tasks)
            if player.identity == "Impostor":
                all_tasks = common_tasks
            else:
                all_tasks = np.concatenate([common_tasks, short_tasks, long_tasks])
                self.assigned_tasks.extend(all_tasks)
            player.assign_tasks(all_tasks)

    def check_task_completion(self):
        all_tasks = 0
        completed_tasks = 0
        for task in self.assigned_tasks:
            if (
                task.assigned_player.is_alive
            ):                                                 
                all_tasks += 1
                if task.check_completion():
                    completed_tasks += 1
        return completed_tasks / all_tasks if all_tasks > 0 else 0
