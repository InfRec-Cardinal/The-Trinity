import networkx as nx
from amongagents.envs.configs.map_config import connections, room_data, vent_connections


class Map:
    def __init__(
        self,
        room_data=room_data,
        connections=connections,
        vent_connections=vent_connections,
    ):
                            
        self.ship_map = nx.Graph()
        self.players = []

                                                                         
        for room_name, details in room_data.items():
            self.ship_map.add_node(
                room_name,
                tasks=details["tasks"],
                vent=details["vent"],
                special_actions=details["special_actions"],
                players=details["players"],
            )

                                          
        for room1, room2 in vent_connections:
            self.ship_map.add_edge(room1, room2, connection_type="vent", weight=100)

                                   
        for room1, room2 in connections:
            self.ship_map.add_edge(room1, room2, connection_type="corridor", weight=1)

    def get_adjacent_rooms(self, room_name):
        pass                                                                    
                                         

                                           
                                                 
           
                                               
        if room_name not in self.ship_map:
            return "Room does not exist."

                                                                               
        adjacent_rooms = [
            adj_room
            for adj_room, attributes in self.ship_map[room_name].items()
            if attributes["connection_type"] == "corridor"
        ]
        return adjacent_rooms

    def get_adjacent_rooms_vent(self, room_name):
        pass                                                                    
                                         

                                           
                                                 
           
                                               
        if room_name not in self.ship_map:
            return "Room does not exist."

                                                                               
        adjacent_rooms = [
            adj_room
            for adj_room, attributes in self.ship_map[room_name].items()
            if attributes["connection_type"] == "vent"
        ]
        return adjacent_rooms

    def get_players_in_room(self, room_name, include_new_deaths=False):
        players = self.ship_map.nodes[room_name]["players"]
        alive_players = [player for player in players if player.is_alive]
        if include_new_deaths:
            unreported_death_players = [
                player
                for player in players
                if (not player.reported_death and not player.is_alive)
            ]
            return alive_players + unreported_death_players
        else:
            return alive_players

    def reset(self):
        pass                                                              
           
        for room in self.ship_map.nodes:
            self.ship_map.nodes[room]["players"] = []

    def add_player(self, player):
        pass                                            

                                     
           
        self.ship_map.nodes[player.location]["players"].append(player)
        self.players.append(player)


class Spaceship:
    def __init__(self, map):
        self.map = map

    def send_messages(self, player, action, room):
        messages = "Message: " + player.name + action + room
        for player in self.map.ship_map.nodes[room]["players"]:
            player.receive(messages)
