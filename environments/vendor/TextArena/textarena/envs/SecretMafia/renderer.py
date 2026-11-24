def create_board_str(game_state: dict) -> str:
    role_icons = {"Villager": "👨‍🌾 Villager ", "Mafia":    "😈 Mafia    ", "Doctor":   "🧑‍⚕️ Doctor   ", "Detective":"🕵️ Detective"}
    lines = []
    lines.append(f"┌─ SECRET MAFIA ─────────────── Phase: {game_state.get('phase', 'Unknown'):<15} | Day: {game_state.get('day_number', 0)} ──────────────┐")
    lines.append("│ Player Status                                                               │")
    lines.append("├────────────┬──────────────┬─────────────────────────────────────────────────┤")
    lines.append("│ Player ID  │   Status     │   Role                                          │")
    lines.append("├────────────┼──────────────┼─────────────────────────────────────────────────┤")
    for pid in sorted(game_state.get("player_roles", {})):
        alive = pid in set(game_state.get('alive_players', []))
        status = "🟢 Alive" if alive else "⚫️ Dead "
        role = role_icons.get(game_state.get("player_roles", {})[pid])                      
        lines.append(f"│ Player {pid:<3} │ {status:<12} │ {role:<42}    │")
    lines.append("└────────────┴──────────────┴──────────────────────────────────────────────┘")
    if game_state.get('phase', 'Unknown') in {"Day-Voting", "Night-Mafia"}:
        lines.append("\n🗳️ VOTES")
        if game_state.get("votes", {}):
            for voter, target in sorted(game_state.get("votes", {}).items()): lines.append(f" - Player {voter} ➜ Player {target}")
        else: lines.append(" - No votes have been cast yet.")
    if game_state.get("to_be_eliminated", None) is not None: lines.append(f"\n🪦 Player {game_state.get('to_be_eliminated', None)} is marked for elimination.")
    mafia_alive = sum(1 for pid in set(game_state.get('alive_players', [])) if game_state.get("player_roles", {})[pid] == "Mafia")
    village_alive = sum(1 for pid in set(game_state.get('alive_players', [])) if game_state.get("player_roles", {})[pid] != "Mafia")
    lines.append(f"\n🔍 Team Breakdown: 😈 Mafia: {mafia_alive} | 🧑‍🌾 Villagers: {village_alive}")
    return "\n".join(lines)
