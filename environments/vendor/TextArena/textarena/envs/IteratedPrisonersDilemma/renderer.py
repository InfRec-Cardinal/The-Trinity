def create_board_str(game_state: dict) -> str:
    raise NotImplementedError
    lines = []
    phase_str = "🗣️ Communication Phase" if not game_state.get("is_decision_phase", False) else "🎯 Decision Phase"
    lines.append(f"╭── Iterated Prisoner's Dilemma ─────────────────────╮")
    lines.append(f"│ Round: {game_state.get('current_round', 1):<2} | Turn: {game_state.get('current_comm_turn', 0):<2} | Phase: {phase_str:<20}│")
    lines.append(f"╰────────────────────────────────────────────────────╯")
    lines.append("┌─ 📊 SCORES ─────────────────────┐")
    lines.append(f"│ Player 0: {game_state.get('scores', {}).get(0, 0):<3} pts               │")
    lines.append(f"│ Player 1: {game_state.get('scores', {}).get(1, 0):<3} pts               │")
    lines.append("└─────────────────────────────────┘")
    if game_state.get('history', []):
        lines.append("┌─ 📜 ROUND HISTORY ────────────────────────────────────┐")
        lines.append("│ Round │ Player 0     │ Player 1     │ Outcome         │")
        lines.append("├───────┼──────────────┼──────────────┼─────────────────┤")
        for round_info in game_state.get('history', []):
            d0 = round_info["decisions"].get(0, "?").capitalize()
            d1 = round_info["decisions"].get(1, "?").capitalize()
            if d0 == d1 == "Cooperate":                 outcome = "Both Cooperated"
            elif d0 == d1 == "Defect":                  outcome = "Both Defected"
            elif d0 == "Cooperate" and d1 == "Defect":  outcome = "P0 Sucker"
            elif d0 == "Defect" and d1 == "Cooperate":  outcome = "P1 Sucker"
            else:                                       outcome = "Unknown"
            lines.append(f"│ {round_info.get("round", "?"):^5} │ {d0:<12} │ {d1:<12} │ {outcome:<8} │")
        lines.append("└───────────────────────────────────────────────────────┘")
    return "\n".join(lines)
