# CombineSystem.py
# Contains the class and logic for combining familiars.

import random
from typing import Dict, List, Tuple

# Import the required configurations
from config import (AUTO_COMBINE_RULES, STRATEGIC_COMBINE_RULES, PITY_COMBINE_CONFIG,
                    ACTIVE_FAMILIARS_PER_CATEGORY, NUM_ACTIVE_CATEGORIES)

class CombineSystem:
    """
    Manages the familiar combination operations.
    """
    
    def _get_familiars_by_category(self, all_active_familiars: List[str]) -> Dict[str, List[str]]:
        """
        Organizes the list of ACTIVE familiars into a dictionary sorted by category.
        """
        categories = {'A': [], 'B': [], 'C': []}
        category_letters = "ABC"
        for i, familiar in enumerate(all_active_familiars):
            category_index = i // ACTIVE_FAMILIARS_PER_CATEGORY
            if category_index < NUM_ACTIVE_CATEGORIES:
                category_letter = category_letters[category_index]
                categories[category_letter].append(familiar)
        return categories

    def auto_combine(self, inventory: Dict, all_familiars: List[str]) -> List[str]:
        """
        Executes all automatic combinations individually per familiar.
        """
        combination_logs = []
        while True:
            made_combination_this_round = False
            for familiar in all_familiars:
                for target_rarity, required_qty in AUTO_COMBINE_RULES.items():
                    source_rarity = target_rarity - 1
                    if inventory[familiar][source_rarity] >= required_qty:
                        num_combines = inventory[familiar][source_rarity] // required_qty
                        inventory[familiar][source_rarity] -= num_combines * required_qty
                        inventory[familiar][target_rarity] += num_combines
                        made_combination_this_round = True
                        combination_logs.append(f" -> {familiar}: {num_combines}x {target_rarity}* item(s) created.")
            if not made_combination_this_round:
                break
        return combination_logs

    def strategic_combine(self, inventory: Dict, credits: Dict, target_rarity: int, target_familiar: str, method: str) -> Tuple[bool, int, str, Dict]:
        """
        Attempts to execute a strategic combination with the correct rule (same familiar)
        and with fixed consumption logic to prevent the "phantom material" bug.
        """
        rules = STRATEGIC_COMBINE_RULES.get(target_rarity)
        if not rules: 
            return False, 0, "Invalid target rarity.", credits
        
        method_rules = rules.get(method)
        if not method_rules: 
            return False, 0, f"Method '{method}' not available.", credits

        source_rarity = rules['from']
        required_qty = method_rules['recipe']
        
        # 1. VERIFY if materials exist (without consuming anything yet)
        credit_key = (target_familiar, source_rarity)
        base_from_credit = credits.get(credit_key, 0)
        copies_in_inventory = inventory[target_familiar][source_rarity]
        
        total_available = base_from_credit + copies_in_inventory
        
        if total_available < required_qty:
            return False, 0, f"Insufficient materials for {target_familiar}. (Required: {required_qty}, Owned: {total_available})", credits
            
        # 2. CONSUME materials BEFORE the attempt
        if base_from_credit > 0:
            del credits[credit_key]
        
        qty_to_consume_from_inventory = required_qty - base_from_credit
        inventory[target_familiar][source_rarity] -= qty_to_consume_from_inventory

        # 3. EXECUTE the attempt and calculate result
        pity_points = 0
        success = False
        
        if method == "guaranteed":
            success = True
            pity_points = PITY_COMBINE_CONFIG["POINTS"][target_rarity].get('guaranteed_success', 0)
        
        elif method == "probabilistic":
            if random.random() < method_rules['success_chance']:
                success = True
                pity_points = PITY_COMBINE_CONFIG["POINTS"][target_rarity].get('prob_success', 0)
            else: # Failure
                success = False
                pity_points = PITY_COMBINE_CONFIG["POINTS"][target_rarity].get('prob_failure', 0)
                credits[credit_key] = 1

        # 4. UPDATE inventory with the outcome
        if success:
            inventory[target_familiar][target_rarity] += 1
            msg = f"SUCCESS! {target_familiar} was combined to {target_rarity}*. Gained {pity_points} points."
        else:
            msg = f"FAILURE! Sacrifice was lost, but {target_familiar} ({source_rarity}*) base was retained. Gained {pity_points} points."
            
        return success, pity_points, msg, credits
