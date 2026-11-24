from typing import Dict, Any


def get_board_str(game_state: Dict[str, Any], current_player_id: int) -> str:
    pass                                                           
    lines = []
    
                                                  
    lines.append("=" * 60)
    lines.append("GAME PHASES & ACTIONS:")
    lines.append("-" * 60)
    lines.append("1. PLANT: [Plant] <field#> (must plant 1st card, may plant 2nd), [Pass], [Harvest] <field#>")
    lines.append("2. DRAW_TRADE: [Trade] <offer> for <want>, [Accept] Trade<#>, [Pass], [EndTrading], [Harvest] <field#> (will rotate turns)")
    lines.append("3. PLANT_MANDATORY: [Plant] <bean> <field#>, [Harvest] <field#>, [Pass]")
    lines.append("4. DRAW: [Draw], [Harvest] <field#>")
    lines.append("")
    lines.append("BEAN TYPES & PAYOUTS (coins:beans_needed):")
    lines.append("-" * 60)
    
                                                                                
    bean_types = {
        "Blue": {"count": 20, "payouts": {1: 4, 2: 6, 3: 8, 4: 10}},
        "Chili": {"count": 18, "payouts": {1: 3, 2: 6, 3: 8, 4: 9}},
        "Stink": {"count": 16, "payouts": {1: 3, 2: 5, 3: 7, 4: 8}},
        "Green": {"count": 14, "payouts": {1: 3, 2: 5, 3: 6, 4: 7}},
        "Soy": {"count": 12, "payouts": {1: 2, 2: 4, 3: 6, 4: 7}},
        "BlackEyed": {"count": 10, "payouts": {1: 2, 2: 4, 3: 5, 4: 6}},
        "Red": {"count": 8, "payouts": {1: 2, 2: 3, 3: 4, 4: 5}},
        "Garden": {"count": 6, "payouts": {2: 2, 3: 3}}
    }
    
    for bean_type, config in bean_types.items():
        payouts_str = ", ".join([f"{coins}:{beans}" for coins, beans in config["payouts"].items()])
        lines.append(f"{bean_type:10} ({config['count']:2} cards): {payouts_str}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("CURRENT GAME STATE")
    lines.append("=" * 60)
    
                                 
    current_phase = game_state["current_phase"]
    lines.append(f"Phase: {current_phase.upper()}")
    lines.append(f"Deck Cycles: {game_state['deck_cycles']}/3")
    lines.append(f"Cards in Deck: {len(game_state['deck'])}")
    lines.append("")
    
                            
    if game_state["face_up_cards"]:
        lines.append(f"FACE-UP CARDS: {', '.join(game_state['face_up_cards'])}")
        lines.append("")
    
                   
    if game_state["active_trades"]:
        lines.append("ACTIVE TRADES:")
        for trade_id, trade in game_state["active_trades"].items():
            status = trade["status"]
            if trade["target"] is None:
                            
                lines.append(f"  Trade{trade_id} ({status}): Player{trade['proposer']} offers '{trade['offer']}' for '{trade['want']}' (open to all)")
            else:
                                
                lines.append(f"  Trade{trade_id} ({status}): Player{trade['proposer']} offers '{trade['offer']}' for '{trade['want']}' with Player{trade['target']}")
        lines.append("")
    
                        
    lines.append("PLAYERS:")
    lines.append("-" * 60)
    
    for player_id, player in game_state["players"].items():
                       
        player_marker = " >>> " if player_id == current_player_id else "     "
        lines.append(f"{player_marker}Player {player_id} - {player['coins']} coins")
        
                                                                           
        hand = player["hand"]
        if player_id == current_player_id:
            if hand:
                hand_str = f"Hand ({len(hand)}): [{', '.join(hand)}]"
            else:
                hand_str = "Hand: Empty"
        else:
                                                                          
            hand_str = f"Hand: {len(hand)} cards"
        lines.append(f"     {hand_str}")
        
                
        lines.append("     Fields:")
        for field_num, field in enumerate(player["fields"]):
            if field:
                bean_type, count = field
                lines.append(f"       Field {field_num + 1}: {count} {bean_type}")
            else:
                lines.append(f"       Field {field_num + 1}: Empty")
        
                                   
        mandatory = game_state["mandatory_plants"][player_id]
        if mandatory:
            lines.append(f"     Must Plant: {', '.join(mandatory)}")
        
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def render_player_summary(game_state: Dict[str, Any], player_id: int) -> str:
    pass                                         
    player = game_state["players"][player_id]
    lines = []
    
    lines.append(f"Player {player_id} Summary:")
    lines.append(f"Coins: {player['coins']}")
    lines.append(f"Hand: {len(player['hand'])} cards")
    
            
    for field_num, field in enumerate(player["fields"]):
        if field:
            bean_type, count = field
            lines.append(f"Field {field_num + 1}: {count} {bean_type}")
        else:
            lines.append(f"Field {field_num + 1}: Empty")
    
    return "\n".join(lines)


def render_trade_summary(active_trades: Dict[int, Dict[str, Any]]) -> str:
    pass                                    
    if not active_trades:
        return "No active trades"
    
    lines = ["Active Trades:"]
    for trade_id, trade in active_trades.items():
        lines.append(f"Trade{trade_id}: Player{trade['proposer']} → Player{trade['target']}")
        lines.append(f"  Offers: {trade['offer']}")
        lines.append(f"  Wants: {trade['want']}")
        lines.append(f"  Status: {trade['status']}")
    
    return "\n".join(lines)


def render_harvest_calculation(bean_type: str, bean_count: int) -> str:
    pass                                         
                                        
    bean_payouts = {
        "Blue": {1: 4, 2: 6, 3: 8, 4: 10},
        "Chili": {1: 3, 2: 6, 3: 8, 4: 9},
        "Stink": {1: 3, 2: 5, 3: 7, 4: 8},
        "Green": {1: 3, 2: 5, 3: 6, 4: 7},
        "Soy": {1: 2, 2: 4, 3: 6, 4: 7},
        "BlackEyed": {1: 2, 2: 4, 3: 5, 4: 6},
        "Red": {1: 2, 2: 3, 3: 4, 4: 5},
        "Garden": {2: 2, 3: 3}
    }
    
    if bean_type not in bean_payouts:
        return f"Unknown bean type: {bean_type}"
    
    payouts = bean_payouts[bean_type]
    coins_earned = 0
    
                                                              
    for coins, beans_needed in sorted(payouts.items(), reverse=True):
        if bean_count >= beans_needed:
            coins_earned = coins
            break
    
    return f"Harvesting {bean_count} {bean_type} beans → {coins_earned} coins"
