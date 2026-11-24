   
                              

                                                                            
                                                                                     

                                                              
                                                                
                                                                      
   

import os
import re
import random
import csv
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import textarena as ta
from textarena.envs.VendorNegotiation.renderer import (
    render_product_data_for_brand,
    render_product_data_for_vendor,
    render_current_state,
    render_final_results,
    render_no_deal
)


class VendorNegotiationEnv(ta.Env):
    pass                                              
    
                                                 
                                        
       
    
    def __init__(self,
                 num_products: int = 5,
                 max_rounds: int = 20,
                 error_allowance: int = 3,
                 brand_target_percentage: float = 0.8,
                 vendor_baseline_multiplier: float = 1.2,
                 num_simulations: int = 1000,
                 brand_role: Optional[str] = None,
                 vendor_role: Optional[str] = None,
                 product_list_path: Optional[str] = None,
                 seed: Optional[int] = None):
        pass                                                      
        
             
                                                                      
                                                                
                                                                              
                                                                                     
                                                                                       
                                                                        
                                                                        
                                                                         
                                                                                          
                                                 
           
        super().__init__()
        
        self.num_products = num_products
        self.max_rounds = max_rounds
        self.error_allowance = error_allowance
        self.brand_target_percentage = brand_target_percentage
        self.vendor_baseline_multiplier = vendor_baseline_multiplier
        self.num_simulations = num_simulations
        self.brand_role_name = brand_role or "default"
        self.vendor_role_name = vendor_role or "default"
        self.product_list_path = product_list_path or "data/product_list.csv"
        self.seed = seed
        
                                     
        self.all_products = self._load_product_data()
        
                                                          
        self.allowed_discounts = self._infer_allowed_discounts()
        self.brand_role_instructions = self._load_role_instructions("brand", self.brand_role_name)
        self.vendor_role_instructions = self._load_role_instructions("vendor", self.vendor_role_name)
        
                                           
        self.selected_products = []
        self.products = {}
        self.current_proposal = {}
        self.negotiation_history = []
        self.brand_target = 0.0
        self.vendor_baseline = 0.0

    def _load_product_data(self) -> Dict:
        pass                                                        
        if os.path.isabs(self.product_list_path):
            csv_path = self.product_list_path
        else:
            csv_path = os.path.join(os.path.dirname(__file__), self.product_list_path)

        products = defaultdict(lambda: {"data": {}})

        with open(csv_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                product_name = row["product"]

                                                                      
                discount_rate_raw = float(row["discount_rate"])
                discount_rate = int(discount_rate_raw) if discount_rate_raw.is_integer() else discount_rate_raw

                price_per_unit = int(row["price_per_unit"])
                cost_per_unit = int(row["cost_per_unit"])

                if "price" not in products[product_name]:
                    products[product_name]["price"] = price_per_unit
                    products[product_name]["cost"] = cost_per_unit

                                             
                data_entry = {}
                for key, val in row.items():
                    if key == "product":
                        continue
                                            
                    try:
                        num_val = float(val)
                        val = int(num_val) if num_val.is_integer() else num_val
                    except ValueError:
                        pass
                    data_entry[key] = val

                products[product_name]["data"][discount_rate] = data_entry

        return dict(products)

    def _infer_allowed_discounts(self) -> List[int]:
        pass                                                 
        if not self.all_products:
            return [0, 15, 20, 30]                    
        
                                                        
        all_discount_rates = set()
        for product_name, product_data in self.all_products.items():
            all_discount_rates.update(product_data['data'].keys())
        
                            
        return sorted(list(all_discount_rates))
    
    def _get_max_discount_rate(self) -> int:
        pass                                                       
        return max(self.allowed_discounts) if self.allowed_discounts else 30
    
    def _load_role_instructions(self, player_type: str, role_name: str) -> str:
        pass                                        
        role_path = os.path.join(
            os.path.dirname(__file__),
            "data",
            "roles",
            player_type,
            f"{role_name}.txt"
        )
        
        try:
            with open(role_path, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
                                                   
            default_path = os.path.join(
                os.path.dirname(__file__),
                "data",
                "roles",
                player_type,
                "default.txt"
            )
            with open(default_path, 'r') as f:
                return f.read().strip()
    
    def reset(self, num_players: int, seed: Optional[int] = None):
        pass                                         
        if num_players != 2:
            raise ValueError("VendorNegotiation requires exactly 2 players")
        
                         
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        elif self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
        
                                
        all_product_names = list(self.all_products.keys())
        self.selected_products = random.sample(all_product_names, min(self.num_products, len(all_product_names)))
        self.products = {name: self.all_products[name] for name in self.selected_products}
        
                                                       
        max_discount = self._get_max_discount_rate()
        self.brand_target = self.brand_target_percentage * sum(
            self.products[p]['data'][max_discount]['mean_sales'] for p in self.selected_products
        )
        self.vendor_baseline = self.vendor_baseline_multiplier * sum(
            self.products[p]['data'][0]['mean_profit'] for p in self.selected_products
        )
        
                                    
        self.state = ta.TwoPlayerState(
            num_players=num_players,
            max_turns=self.max_rounds,
            seed=seed,
            error_allowance=self.error_allowance
        )
        
                          
        self.current_proposal = {'discounts': None, 'proposer': None}
        self.negotiation_history = []
        self.conversation_history = []
        
        game_state = {
            'current_proposal': self.current_proposal,
            'negotiation_history': self.negotiation_history,
            'conversation_history': self.conversation_history
        }
        
                                   
        self.state.reset(
            game_state=game_state,
            player_prompt_function=self._generate_player_prompt,
            role_mapping={0: "Brand Specialist", 1: "Vendor"}
        )
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        pass                                       
                                     
        product_order = ", ".join(self.selected_products)
        initial_prompt = f"You are Player {player_id}.\n"
        
        if player_id == 0:                    
            prompt = f"""ROLE: Brand Specialist at E-commerce Platform
OBJECTIVE: Achieve total sales ≥ ${self.brand_target:.0f} ({self.brand_target_percentage*100:.0f}% of maximum possible)

{self.brand_role_instructions}

NEGOTIATION: Agree on discount rates for {self.num_products} products with Vendor

{render_product_data_for_brand(self.products, self.selected_products, self.allowed_discounts)}

PRODUCT ORDER: {product_order}

ACTIONS: There are two parts of an action, STRICTLY in this order.
1. Free-text communication to the other party to persuade them to agree to a deal favorable to you.
2. ALWAYS end with one of these bracketed actions:
- [Propose] X%, Y%, Z%, ... (follow product order above)
- [Accept]
- [Reject]

ROUNDS: {self.max_rounds} maximum
"""
        else:          
            prompt = f"""ROLE: Vendor
OBJECTIVE: Achieve total profit > ${self.vendor_baseline:.0f} (baseline at {self.vendor_baseline_multiplier} times profit at 0% discount)

You must NEVER reveal information about your profit and cost.
{self.vendor_role_instructions}

NEGOTIATION: Agree on discount rates for {self.num_products} products with Brand Specialist

{render_product_data_for_vendor(self.products, self.selected_products, self.allowed_discounts)}

PRODUCT ORDER: {product_order}

ACTIONS: There are two parts of an action, STRICTLY in this order.
1. Free-text communication to the other party to persuade them to agree to a deal favorable to you.
2. ALWAYS end with one of these bracketed actions:
- [Propose] X%, Y%, Z%, ... (follow product order above)
- [Accept]
- [Reject]

ROUNDS: {self.max_rounds} maximum
"""
        
        return initial_prompt + prompt
    
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pass                            
        current_pid = self.state.current_player_id
        
                        
        self.state.add_observation(
            from_id=current_pid,
            to_id=current_pid,
            message=f"Your action: {action}",
            observation_type=ta.ObservationType.PLAYER_ACTION
        )
        
                            
        if self._is_valid_action(action):
            self._process_valid_action(current_pid, action)
        
                                       
        deal_accepted = self._check_deal_accepted()
        max_turns_reached = self.state.turn >= self.max_rounds - 1
        
        if deal_accepted or max_turns_reached:
            self._end_game(deal_accepted)
        
                                               
        return self.state.step()
    
    def _is_valid_action(self, action: str) -> bool:
        pass                              
        action = action.strip()
        
                                
        has_propose = "[Propose]" in action
        has_accept = "[Accept]" in action
        has_reject = "[Reject]" in action
        
        action_count = sum([has_propose, has_accept, has_reject])
        
                                                            
        if action_count == 0:
                                                      
            return True
        elif action_count > 1:
            self.state.set_invalid_move("Multiple actions detected. Use only one action per turn")
            return False
        
                           
        if has_propose:
            if not self._is_valid_proposal(action):
                return False
        
                                
        if has_accept or has_reject:
            if self.current_proposal['discounts'] is None:
                action_type = "accept" if has_accept else "reject"
                self.state.set_invalid_move(f"No current proposal to {action_type}")
                return False
            
            if self.current_proposal['proposer'] == self.state.current_player_id:
                action_type = "accept" if has_accept else "reject"
                self.state.set_invalid_move(f"You cannot {action_type} your own proposal")
                return False
        
        return True
    
    def _is_valid_proposal(self, action: str) -> bool:
        pass                               
        try:
            discounts = self._extract_proposal_discounts(action)
            if discounts is None:
                product_order = ", ".join(self.selected_products)
                self.state.set_invalid_move(f"Invalid proposal format. Use: [Propose] X%, Y%, Z%, ... following order: {product_order}")
                return False
            
                                             
            if set(discounts.keys()) != set(self.selected_products):
                missing = set(self.selected_products) - set(discounts.keys())
                extra = set(discounts.keys()) - set(self.selected_products)
                msg = "Proposal must include all products. "
                if missing:
                    msg += f"Missing: {', '.join(missing)}. "
                if extra:
                    msg += f"Extra: {', '.join(extra)}."
                self.state.set_invalid_move(msg)
                return False
            
                                             
            for product, discount in discounts.items():
                if discount not in self.allowed_discounts:
                    self.state.set_invalid_move(
                        f"Invalid discount {discount}% for {product}. "
                        f"Allowed: {', '.join(str(d) + '%' for d in self.allowed_discounts)}"
                    )
                    return False
            
            return True
        except Exception as e:
            self.state.set_invalid_move(f"Error parsing proposal: {str(e)}")
            return False
    
    def _extract_proposal_discounts(self, action: str) -> Optional[Dict[str, int]]:
        pass                                                    
                                                                        
           
        try:
                                           
            if "[Propose]" not in action:
                return None
            
            proposal_text = action.split("[Propose]")[1].strip()
            
                                                                      
            positional_pattern = r'(\d+)%'
            positional_matches = re.findall(positional_pattern, proposal_text)
            
            if not positional_matches:
                return None
            
                                               
            if len(positional_matches) != len(self.selected_products):
                return None
            
                                      
            discounts = {}
            for i, discount_str in enumerate(positional_matches):
                discounts[self.selected_products[i]] = int(discount_str)
            
            return discounts
        except Exception:
            return None
    
    def _process_valid_action(self, player_id: int, action: str):
        pass                         
        action = action.strip()
        
        if "[Propose]" in action:
            self._process_proposal(player_id, action)
        elif "[Accept]" in action:
            self._process_accept(player_id, action)
        elif "[Reject]" in action:
            self._process_reject(player_id, action)
        else:
                                                        
            self._process_conversation(player_id, action)
    
    def _process_conversation(self, player_id: int, action: str):
        pass                                 
                                        
        self.conversation_history.append({
            'player': player_id,
            'message': action,
            'round': self.state.turn + 1
        })
        self.state.game_state['conversation_history'] = self.conversation_history
        
                                   
        self._record_action(player_id, 'conversation', None)
        
                               
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=f"Player {player_id}: {action}",
            observation_type=ta.ObservationType.GAME_MESSAGE
        )
    
    def _process_proposal(self, player_id: int, action: str):
        pass                     
        discounts = self._extract_proposal_discounts(action)
        
                                                           
        conversation_part = action.split("[Propose]")[0].strip()
        if conversation_part:
                                          
            self.conversation_history.append({
                'player': player_id,
                'message': conversation_part,
                'round': self.state.turn + 1
            })
            self.state.game_state['conversation_history'] = self.conversation_history
        
                                 
        self.current_proposal = {'discounts': discounts, 'proposer': player_id}
        self.state.game_state['current_proposal'] = self.current_proposal
        
                           
        self._record_action(player_id, 'propose', discounts)
        
                               
        proposal_str = ", ".join(f"{p}:{d}%" for p, d in discounts.items())
        message = f"Player {player_id} proposed: {proposal_str}"
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _process_accept(self, player_id: int, action: str):
        pass                           
                                                          
        conversation_part = action.split("[Accept]")[0].strip()
        if conversation_part:
                                          
            self.conversation_history.append({
                'player': player_id,
                'message': conversation_part,
                'round': self.state.turn + 1
            })
            self.state.game_state['conversation_history'] = self.conversation_history
        
        self._record_action(player_id, 'accept', None)
        
        message = f"Player {player_id} accepted the proposal"
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _process_reject(self, player_id: int, action: str):
        pass                          
                                                          
        conversation_part = action.split("[Reject]")[0].strip()
        if conversation_part:
                                          
            self.conversation_history.append({
                'player': player_id,
                'message': conversation_part,
                'round': self.state.turn + 1
            })
            self.state.game_state['conversation_history'] = self.conversation_history
        
        self._record_action(player_id, 'reject', None)
        
        message = f"Player {player_id} rejected the proposal"
        
                        
        self.current_proposal = {'discounts': None, 'proposer': None}
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=message,
            observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION
        )
    
    def _record_action(self, player_id: int, action_type: str, discounts: Optional[Dict]):
        pass                           
        self.negotiation_history.append({
            'player': player_id,
            'type': action_type,
            'discounts': discounts,
            'round': self.state.turn + 1
        })
        
        self.state.game_state['negotiation_history'] = self.negotiation_history
    
    def _check_deal_accepted(self) -> bool:
        pass                                              
        if self.current_proposal['discounts'] is None:
            return False
        
        if self.negotiation_history:
            last_action = self.negotiation_history[-1]
            if (last_action['type'] == 'accept' and 
                last_action['player'] != self.current_proposal['proposer']):
                return True
        
        return False
    
    def _end_game(self, deal_accepted: bool):
        pass                                      
        if deal_accepted:
            self._finalize_accepted_deal()
        else:
            self._handle_no_deal()
        
        self.state.done = True
    
    def _finalize_accepted_deal(self):
        pass                                                        
        agreed_discounts = self.current_proposal['discounts']
        
                                    
        simulation_results = self._calculate_actual_sales(agreed_discounts)
        
                          
        total_sales = sum(r['avg_sales'] for r in simulation_results.values())
        total_profit = sum(r['avg_profit'] for r in simulation_results.values())
        
                              
        brand_won = total_sales >= self.brand_target
        vendor_won = total_profit > self.vendor_baseline
        
                          
        results_str = render_final_results(
            simulation_results,
            agreed_discounts,
            brand_won,
            vendor_won,
            self.brand_target,
            self.vendor_baseline,
            self.num_simulations
        )
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=results_str,
            observation_type=ta.ObservationType.GAME_ADMIN
        )
        
                     
        self._set_final_rewards(brand_won, vendor_won)
    
    def _calculate_actual_sales(self, agreed_discounts: Dict[str, int]) -> Dict[str, Dict[str, float]]:
        pass                                                                    
                                      
        all_simulations = {
            product: {
                'units': [],
                'sales': [],
                'profit': []
            } for product in agreed_discounts.keys()
        }
        
                                                
        for product_name, discount in agreed_discounts.items():
            product_data = self.products[product_name]['data'][discount]
            
                                          
            units_samples = np.maximum(0, np.random.normal(
                product_data['mean_units'],
                product_data['std_units'],
                size=self.num_simulations
            ))
            
                                     
            price = self.products[product_name]['price']
            cost = self.products[product_name]['cost']
            discount_multiplier = 1 - (discount / 100)
            
            sales_samples = units_samples * price * discount_multiplier
            profit_samples = units_samples * (price * discount_multiplier - cost)
            
            all_simulations[product_name]['units'] = units_samples
            all_simulations[product_name]['sales'] = sales_samples
            all_simulations[product_name]['profit'] = profit_samples
        
                              
        results = {}
        for product_name in agreed_discounts.keys():
            units_array = all_simulations[product_name]['units']
            sales_array = all_simulations[product_name]['sales']
            profit_array = all_simulations[product_name]['profit']
            
            results[product_name] = {
                'discount': agreed_discounts[product_name],
                'avg_units': float(np.mean(units_array)),
                'avg_sales': float(np.mean(sales_array)),
                'avg_profit': float(np.mean(profit_array))
            }
        
        return results
    
    def _handle_no_deal(self):
        pass                                        
        results_str = render_no_deal(self.brand_target, self.vendor_baseline)
        
        self.state.add_observation(
            from_id=ta.GAME_ID,
            to_id=-1,
            message=results_str,
            observation_type=ta.ObservationType.GAME_ADMIN
        )
        
                           
        self._set_final_rewards(False, False)
    
    def _set_final_rewards(self, brand_won: bool, vendor_won: bool):
        pass                                            
        if brand_won and vendor_won:
                             
            self.state.set_draw(reason="Both players achieved their objectives")
        elif brand_won and not vendor_won:
                       
            self.state.set_winner(player_id=0, reason="Brand Specialist achieved sales target")
        elif vendor_won and not brand_won:
                        
            self.state.set_winner(player_id=1, reason="Vendor achieved profit target")
        else:
                              
            self.state.set_draw(reason="Neither player achieved their objective")
    
    def get_observation(self):
        pass                                     
        player_id = self.state.current_player_id
        observation = self.state.get_current_player_observation()
        
                                       
        state_info = render_current_state(
            self.current_proposal,
            self.negotiation_history,
            self.state.turn + 1,
            self.max_rounds,
            self.conversation_history,
            self.products,
            self.brand_target,
            self.vendor_baseline,
            player_id
        )
        
        observation.append((ta.GAME_ID, state_info, ta.ObservationType.GAME_BOARD))
        
        return player_id, observation
    
    def get_board_str(self) -> str:
        pass                                             
        if getattr(self.state, "done", False):
                                               
            if self.current_proposal['discounts'] is not None and self._check_deal_accepted():
                                                                        
                agreed_discounts = self.current_proposal['discounts']
                simulation_results = self._calculate_actual_sales(agreed_discounts)
                
                                  
                total_sales = sum(r['avg_sales'] for r in simulation_results.values())
                total_profit = sum(r['avg_profit'] for r in simulation_results.values())
                
                                      
                brand_won = total_sales >= self.brand_target
                vendor_won = total_profit > self.vendor_baseline
                
                return render_final_results(
                    simulation_results,
                    agreed_discounts,
                    brand_won,
                    vendor_won,
                    self.brand_target,
                    self.vendor_baseline,
                    self.num_simulations
                )
            else:
                         
                return render_no_deal(self.brand_target, self.vendor_baseline)
        
                      
        return render_current_state(
            self.current_proposal,
            self.negotiation_history,
            self.state.turn + 1,
            self.max_rounds,
            self.conversation_history
        )
