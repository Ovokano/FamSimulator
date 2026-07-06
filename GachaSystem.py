# gacha_system.py
# Contains the class and all logic to simulate the pull system and game state.

import numpy as np
import random
from typing import Dict, List, Tuple

# Modules
from config import (
    GACHA_CONFIG,
    MAX_RARITY,
    FAMILIAR_NAMES,
    NUM_ACTIVE_CATEGORIES,
    ACTIVE_FAMILIARS_PER_CATEGORY,
    TOTAL_FAMILIARS_PER_CATEGORY_IN_LIST
)


class GachaSimulator:
    """
    Manages the state and actions of the gacha system (pulls).
    """
    
    def __init__(self):
        self.config = GACHA_CONFIG
        self.diamonds_spent: int = 0
        self.pull_pity_counter: int = 0
        self.combine_pity_counter: int = 0
        self.combine_credits: Dict[Tuple[str, int], int] = {}
        self.familiars: List[str] = self._generate_familiar_list()
        self.inventory: Dict[str, Dict[int, int]] = {
            familiar: {rarity: 0 for rarity in range(MAX_RARITY + 1)}
            for familiar in self.familiars
        }
        self.rarities_list: List[int] = list(self.config["DROP_RATES"].keys())
        self.rarities_weights: List[float] = list(self.config["DROP_RATES"].values())

    def _generate_familiar_list(self) -> List[str]:
        full_list = FAMILIAR_NAMES
        active_familiars = []
        for i in range(NUM_ACTIVE_CATEGORIES):
            block_start = i * TOTAL_FAMILIARS_PER_CATEGORY_IN_LIST
            block_end = block_start + ACTIVE_FAMILIARS_PER_CATEGORY
            active_familiars.extend(full_list[block_start:block_end])
        if not active_familiars:
            raise ValueError("No familiars were selected. Check the configurations in config.py")
        return active_familiars

    def _pull_single_familiar(self, silent: bool = False) -> Tuple[str, int]:
        self.pull_pity_counter += 1
        drawn_familiar = random.choice(self.familiars)
        drawn_rarity = random.choices(self.rarities_list, weights=self.rarities_weights, k=1)[0]
        
        if self.pull_pity_counter >= self.config["PITY_PULLS_THRESHOLD"]:
            if not silent:
                print(f"--- PULL PITY REACHED AT {self.pull_pity_counter} PULLS! ---")
            drawn_rarity = self.config["PITY_PULLS_REWARD_RARITY"]
            self.pull_pity_counter = 0
            
        return drawn_familiar, drawn_rarity

    def pull_one(self, silent: bool = False) -> Tuple[str, int]:
        self.diamonds_spent += self.config["SINGLE_PULL_COST"]
        familiar, rarity = self._pull_single_familiar(silent=silent)
        self.inventory[familiar][rarity] += 1
        return familiar, rarity

    def pull_eleven(self, silent: bool = False) -> List[Tuple[str, int]]:
        self.diamonds_spent += self.config["MULTI_PULL_COST"]
        results = []
        for _ in range(self.config["MULTI_PULL_QTY"]):
            familiar, rarity = self._pull_single_familiar(silent=silent)
            self.inventory[familiar][rarity] += 1
            results.append((familiar, rarity))
        return results
    
    def optimized_bulk_pull(self, num_pulls: int):
        """
        Executes a batch of pulls in a massively optimized way using NumPy.
        """
        if num_pulls <= 0:
            return

        # 1. Cost Calculation
        # Calculates how many multi-pull packages are needed and applies package pricing.
        num_packages = np.ceil(num_pulls / self.config["MULTI_PULL_QTY"])
        batch_cost = num_packages * self.config["MULTI_PULL_COST"]
        self.diamonds_spent += batch_cost

        # 2. Mathematical Pity Calculation (instantaneous)
        counted_pulls = self.pull_pity_counter + num_pulls
        triggered_pities = counted_pulls // self.config["PITY_PULLS_THRESHOLD"]
        if triggered_pities > 0:
            # ASSUMPTION: The pity reward is a random familiar of the correct rarity tier
            for _ in range(triggered_pities):
                reward_familiar = random.choice(self.familiars)
                self.inventory[reward_familiar][self.config["PITY_PULLS_REWARD_RARITY"]] += 1
        self.pull_pity_counter = counted_pulls % self.config["PITY_PULLS_THRESHOLD"]

        # 3. Vectorized Random Sampling (extremely fast)
        # Draws ALL familiars at once
        familiar_indices = np.random.randint(0, len(self.familiars), size=num_pulls)
        # Draws ALL rarities at once
        drawn_rarities = np.random.choice(self.rarities_list, size=num_pulls, p=self.rarities_weights)

        # 4. Inventory Update
        # This loop runs in native Python, but the slow random sampling logic is already completed.
        for i in range(num_pulls):
            drawn_familiar = self.familiars[familiar_indices[i]]
            drawn_rarity = drawn_rarities[i]
            self.inventory[drawn_familiar][drawn_rarity] += 1
