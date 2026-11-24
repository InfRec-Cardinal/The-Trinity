import re

import networkx as nx


class GetBestPath:
    def __init__(self, network):
        self.network = network

    def get_path(self, from_location, to_location, identity):
        pass                                      
        if identity == "Impostor":
            path = nx.shortest_path(self.network, from_location, to_location)
        else:
            path = nx.shortest_path(
                self.network, from_location, to_location, weight="weight"
            )
        path_str = "->".join(path)
        instruction = (
            "Now, write your response with [Condensed Memory], [Thinking Process], and [Action]. "
            "Make sure action is chosen from the available actions. Case sensitive."
        )
        return f"{path_str}\n{instruction}"


class AgentResponse:
    valid_actions = [
        "VOTE",
        "MOVE",
        "SPEAK",
        "CALL MEETING",
        "KILL",
        "VENT",
        "REPORT DEAD BODY",
        "VIEW MONITOR",
        "COMPLETE TASK",
        "COMPLETE FAKE TASK",
    ]

    def __init__(self, condensed_memory, thinking_process, action):
        self.condensed_memory = condensed_memory
        self.thinking_process = thinking_process
        self.action = action

        if action not in self.valid_actions:
            raise ValueError(f"Invalid action: {action}")
