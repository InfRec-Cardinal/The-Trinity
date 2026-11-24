def create_board_str(game_state: dict) -> str:
    pass                                                   
    gs = game_state
    
                 
    board_str = "🎰 ULTIMATE TEXAS HOLD'EM 🎰\n"
    board_str += "=" * 50 + "\n\n"
    
               
    board_str += f"💰 Chips: ${gs['chips']}\n"
    board_str += f"🎯 Round: {gs['current_round']}\n"
    board_str += f"📋 Phase: {gs['current_phase'].upper().replace('_', ' ')}\n\n"
    
                 
    if gs['player_hand']:
        hand_str = ", ".join([f"{card['rank']}{card['suit']}" for card in gs['player_hand']])
        board_str += f"🎴 Your hand: {hand_str}\n"
    
                     
    if gs['visible_community_cards']:
        comm_str = ", ".join([f"{card['rank']}{card['suit']}" for card in gs['visible_community_cards']])
        board_str += f"🃏 Community cards: {comm_str}\n"
    else:
        board_str += "🃏 Community cards: [Hidden]\n"
    
                                      
    if gs['current_phase'] == 'showdown':
        dealer_str = ", ".join([f"{card['rank']}{card['suit']}" for card in gs['dealer_hand']])
        board_str += f"👤 Dealer's hand: {dealer_str}\n"
    else:
        board_str += "👤 Dealer's hand: [Hidden]\n"
    
    board_str += "\n"
    
                  
    board_str += "💸 Current Bets:\n"
    board_str += f"   Ante: ${gs['ante_bet']}\n"
    board_str += f"   Blind: ${gs['blind_bet']}\n"
    board_str += f"   Play: ${gs['play_bet']}\n"
    board_str += f"   Total: ${gs['total_bet']}\n\n"
    
                   
    if gs['legal_actions'] and gs['current_phase'] != 'showdown':
        actions_str = ", ".join([f"[{action}]" for action in gs['legal_actions']])
        board_str += f"✅ Available actions: {actions_str}\n\n"
    
                 
    if gs.get('game_complete', False) or gs.get('winner'):
                                                  
        if gs.get('winner') == 'player':
            board_str += "🏆 GAME OVER - YOU WIN! 🏆\n"
        else:
            board_str += "💀 GAME OVER - DEALER WINS 💀\n"
    elif gs.get('chips', 0) <= 0:
        board_str += "💀 GAME OVER - OUT OF CHIPS 💀\n"
    elif gs.get('current_round', 0) >= 1000:
        board_str += "🏆 GAME OVER - 1000 ROUNDS COMPLETED! 🏆\n"
    elif gs['round_complete']:
        board_str += "🔄 Round complete - starting next round...\n"
    
    return board_str 