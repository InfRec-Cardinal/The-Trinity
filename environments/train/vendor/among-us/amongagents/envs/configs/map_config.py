room_data = {
    "Cafeteria": {
        "tasks": ["Download Data", "Empty Garbage", "Fix Wiring"],
        "vent": ["Admin"],
        "special_actions": ["Emergency Button"],
        "players": [],
    },
    "Weapons": {
        "tasks": ["Accept Diverted Power", "Clear Asteroids", "Download Data"],
        "vent": ["Navigation"],
        "special_actions": [],
        "players": [],
    },
    "Navigation": {
        "tasks": [
            "Accept Diverted Power",
            "Chart Course",
            "Download Data",
            "Fix Wiring",
            "Stabilize Steering",
        ],
        "vent": ["Shields", "Weapons"],
        "special_actions": [],
        "players": [],
    },
    "O2": {
        "tasks": ["Clean O2 Filter", "Empty Chute", "Accept Diverted Power"],
        "vent": [],
        "special_actions": ["Oxygen Depleted"],
        "players": [],
    },
    "Shields": {
        "tasks": ["Accept Diverted Power", "Prime Shields"],
        "vent": ["Navigation"],
        "special_actions": [],
        "players": [],
    },
    "Communications": {
        "tasks": ["Accept Diverted Power", "Download Data"],
        "vent": [],
        "special_actions": ["Comms Sabotaged"],
        "players": [],
    },
    "Storage": {
        "tasks": ["Empty Garbage", "Empty Chute"],
        "vent": [],
        "special_actions": [],
        "players": [],
    },
    "Admin": {
        "tasks": ["Fix Wiring", "Swipe Card", "Upload Data"],
        "vent": ["Cafeteria"],
        "special_actions": ["Admin Map"],
        "players": [],
    },
    "Electrical": {
        "tasks": [
            "Calibrate Distributor",
            "Divert Power",
            "Download Data",
            "Fix Wiring",
        ],
        "vent": ["Medbay", "Security"],
        "special_actions": ["Fix Lights"],
        "players": [],
    },
    "Lower Engine": {
        "tasks": ["Accept Diverted Power", "Align Engine Output", "Fuel Engines"],
        "vent": ["Reactor"],
        "special_actions": [],
        "players": [],
    },
    "Security": {
        "tasks": ["Accept Diverted Power", "Fix Wiring"],
        "vent": [],
        "special_actions": ["Security Cameras"],
        "players": [],
    },
    "Reactor": {
        "tasks": ["Start Reactor", "Unlock Manifolds"],
        "vent": ["Upper Engine", "Lower Engine"],
        "special_actions": ["Reactor Meltdown"],
        "players": [],
    },
    "Upper Engine": {
        "tasks": ["Accept Diverted Power", "Align Engine Output", "Fuel Engines"],
        "vent": ["Reactor"],
        "special_actions": [],
        "players": [],
    },
    "Medbay": {
        "tasks": ["Inspect Sample", "Submit Scan"],
        "vent": ["Electrical", "Security"],
        "special_actions": ["Medbay Scan"],
        "players": [],
    },
}

                                                                                                      
                                                                            
vent_connections = [
    ("Reactor", "Lower Engine"),
    ("Upper Engine", "Reactor"),
    ("Electrical", "Security"),
    ("Upper Engine", "Lower Engine"),
    ("Electrical", "Medbay"),
    ("Navigation", "Shields"),
    ("Medbay", "Security"),
    ("Navigation", "Weapons"),
    ("Admin", "Cafeteria"),
]

connections = [
    ("Cafeteria", "Weapons"),
    ("Cafeteria", "Admin"),
    ("Cafeteria", "Upper Engine"),
    ("Cafeteria", "Medbay"),
    ("Weapons", "Navigation"),
    ("Weapons", "O2"),
    ("Navigation", "Shields"),
    ("O2", "Shields"),
    ("O2", "Admin"),
    ("Shields", "Communications"),
    ("Shields", "Storage"),
    ("Communications", "Storage"),
    ("Storage", "Admin"),
    ("Storage", "Electrical"),
    ("Storage", "Lower Engine"),
    ("Admin", "Electrical"),
    ("Electrical", "Lower Engine"),
    ("Lower Engine", "Security"),
    ("Lower Engine", "Reactor"),
    ("Lower Engine", "Upper Engine"),
    ("Security", "Reactor"),
    ("Security", "Upper Engine"),
    ("Reactor", "Upper Engine"),
    ("Upper Engine", "Medbay"),
    ("Medbay", "Cafeteria"),
]

map_coords = {
    "Cafeteria": {
        "coords": (
            405,
            50,
            447,
            7,
            582,
            7,
            647,
            70,
            647,
            195,
            589,
            250,
            458,
            250,
            405,
            198,
        ),
    },
    "Weapons": {
        "coords": (705, 107, 797, 107, 797, 163, 726, 163, 705, 147),
    },
    "Navigation": {
        "coords": (902, 214, 936, 214, 966, 238, 966, 268, 932, 298, 902, 298),
    },
    "O2": {
        "coords": (672, 212, 710, 212, 710, 262, 639, 262, 639, 240),
    },
    "Shields": {
        "coords": (719, 397, 796, 397, 796, 438, 756, 474, 719, 474),
    },
    "Communications": {
        "coords": (583, 481, 677, 481, 677, 526, 583, 526),
    },
    "Storage": {
        "coords": (433, 386, 463, 363, 546, 363, 546, 536, 475, 536, 433, 499),
    },
    "Admin": {
        "coords": (593, 304, 689, 304, 689, 365, 593, 365),
    },
    "Electrical": {
        "coords": (311, 326, 378, 326, 378, 412, 311, 412),
    },
    "Lower Engine": {
        "coords": (100, 367, 195, 367, 195, 460, 127, 460, 100, 442),
    },
    "Security": {
        "coords": (215, 229, 262, 229, 262, 315, 215, 315),
    },
    "Reactor": {
        "coords": (10, 225, 96, 225, 96, 311, 10, 311),
    },
    "Upper Engine": {
        "coords": (100, 108, 127, 90, 195, 90, 195, 170, 100, 170),
    },
    "Medbay": {
        "coords": (305, 181, 367, 181, 367, 270, 305, 270),
    },
}
