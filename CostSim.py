# CostSim.Py
import numpy as np
import random
import logging
from typing import Dict, Tuple, List
from gacha_system import GachaSimulator
from combine_system import CombineSystem
from config import (
    STRATEGIC_COMBINE_RULES,
    SIMULATION_BULK_PULLS,
    PITY_COMBINE_CONFIG,
    PRECISION_BULK_PULLS,
    PRECISION_THRESHOLD,
)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable


# ============================ GENERAL SETTINGS ============================

LOG_LEVEL = logging.WARNING  # Can be changed between WARNING, INFO, or DEBUG
RANDOM_SEED = None         # Set a fixed number for reproducible results
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")

# ============================ HELPER FUNCTIONS ==============================

def get_initial_inventory(valid_names: List[str]) -> Dict:
    """
    Asks the user about their initial inventory.
    Returns a dictionary in the format: {'HI': {10: 1, 9: 5}}
    """
    inventory = {}
    print("\n--- INITIAL INVENTORY (Optional) ---")
    while True:
        response = input("Would you like to add an initial inventory? (y/n): ").lower().strip()
        if response == 'n' or response == 'no' or response == '':
            return inventory  # Returns an empty inventory
        if response == 'y' or response == 'yes':
            break
    
    print("\nEnter the familiars you already own (e.g., HI, 9, 5).")
    print("Enter 'done' in the familiar name to stop.")
    
    while True:
        # 1. Get Name
        fam_name_input = input("  Familiar name (or 'done'): ").strip()
        if fam_name_input.lower() == 'done':
            break
        
        # 2. Validate Name (case-insensitive)
        real_fam_name = next((name for name in valid_names if name.lower() == fam_name_input.lower()), None)
        
        if not real_fam_name:
            print(f"Error: '{fam_name_input}' is not a valid familiar.")
            print(f"Valid options are: {valid_names}")
            continue
            
        # 3. Get Rarity
        try:
            rarity = int(input(f"  Rarity of {real_fam_name} (e.g., 8): "))
            if not (0 <= rarity <= 10):
                print("Error: Rarity must be between 0 and 10.")
                continue
        except ValueError:
            print("Error: Invalid input. Please enter a number.")
            continue
            
        # 4. Get Quantity
        try:
            qty = int(input(f"  Quantity of {real_fam_name} ({rarity}*): "))
            if qty < 0:
                print("Error: Quantity cannot be negative.")
                continue
        except ValueError:
            print("Error: Invalid input. Please enter a number.")
            continue
            
        # 5. Add to dictionary
        if real_fam_name not in inventory:
            inventory[real_fam_name] = {}
        inventory[real_fam_name][rarity] = qty
        print(f" -> Added: {qty}x {real_fam_name} ({rarity}*)\n")
        
    print("--- Initial inventory saved. ---")
    return inventory

def get_user_targets() -> Tuple[Dict[int, int], Dict[int, str]]:
    """
    Asks the user for quantity targets and combine methods per rarity.
    Returns:
        quantity_targets: dict {rarity: quantity}
        methods_per_rarity: dict {rarity: 'probabilistic' | 'guaranteed'}
    """
    print("\n--- DEFINE YOUR TARGETS ---")
    quantity_targets = {}
    methods_per_rarity = {}
    
    for rarity in [8, 9, 10]:
        while True:
            try:
                qty = int(input(f"Desired quantity of {rarity}* familiars: ") or 0)
                if qty < 0:
                    raise ValueError
                quantity_targets[rarity] = qty
                break
            except ValueError:
                print("Invalid input. Please enter a positive integer.")

    highest_desired_rarity = max((r for r, q in quantity_targets.items() if q > 0), default=0)

    if highest_desired_rarity > 0:
        print("\n--- DEFINE COMBINE METHODS ---")
        for stage_rarity in range(8, highest_desired_rarity + 1):
            if stage_rarity == 10 and 'probabilistic' not in STRATEGIC_COMBINE_RULES.get(10, {}):
                print(" -> For 10*, the only method is 100%.")
                methods_per_rarity[stage_rarity] = 'guaranteed'
                continue

            while True:
                method_input = input(f" -> Which method to use to create {stage_rarity}* (25 or 100)? ") or "100"
                if method_input == '25':
                    methods_per_rarity[stage_rarity] = 'probabilistic'
                    break
                elif method_input == '100':
                    methods_per_rarity[stage_rarity] = 'guaranteed'
                    break
                else:
                    print("Invalid input. Please enter 25 or 100.")
    
    return quantity_targets, methods_per_rarity


def check_targets_met(inventory: Dict, targets: Dict) -> bool:
    """Returns True if all rarity targets have been met."""
    for rarity, desired_qty in targets.items():
        if desired_qty == 0:
            continue
        current_qty = sum(f.get(rarity, 0) for f in inventory.values())
        if current_qty < desired_qty:
            return False
    return True


def count_rarity(inventory: Dict, rarity: int) -> int:
    """Counts how many familiars exist of a specific rarity."""
    return sum(f.get(rarity, 0) for f in inventory.values())


# ============================ MAIN LOGIC ================================

def choose_best_candidate(simulator: GachaSimulator, rarity_to_create: int, source_rarity: int) -> str:
    """
    Chooses the best candidate for combination based on:
      - Available credits
      - Number of copies
      - Priority given to new familiars
    """
    def score_candidate(fam: str) -> int:
        has_credit = (fam, source_rarity) in simulator.combine_credits
        copies = simulator.inventory[fam][source_rarity]
        new_bonus = 10 if simulator.inventory[fam][rarity_to_create] == 0 else 0
        return copies + has_credit + new_bonus

    return max(simulator.familiars, key=score_candidate, default=None)


def try_strategic_combine(simulator: GachaSimulator, combiner: CombineSystem,
                          targets: Dict, methods: Dict) -> bool:
    """Executes strategic combine attempts."""
    for target_rarity in sorted(targets.keys(), reverse=True):
        current_qty = count_rarity(simulator.inventory, target_rarity)
        if current_qty >= targets.get(target_rarity, 0):
            continue

        rarity_to_create = target_rarity
        while rarity_to_create >= 8:
            method = methods.get(rarity_to_create)
            if not method:
                break

            source_rarity = STRATEGIC_COMBINE_RULES[rarity_to_create]['from']
            candidate = choose_best_candidate(simulator, rarity_to_create, source_rarity)

            if not candidate:
                rarity_to_create -= 1
                continue

            success, points, msg, updated_credits = combiner.strategic_combine(
                simulator.inventory, simulator.combine_credits,
                rarity_to_create, candidate, method
            )

            if "insufficient" not in msg.lower():
                simulator.combine_credits = updated_credits
                simulator.combine_pity_counter += points
                logging.debug(f"Combine {rarity_to_create}* with {candidate} ({method}) - {msg}")
                return True  # Progress was made

            rarity_to_create -= 1
    return False


def try_auto_combine(simulator: GachaSimulator, combiner: CombineSystem) -> bool:
    """Executes default automatic combinations."""
    if combiner.auto_combine(simulator.inventory, simulator.familiars):
        logging.debug("Automatic combination executed.")
        return True
    return False


def try_pull_materials(simulator: GachaSimulator, targets: Dict, precision_mode: bool) -> None:
    """Executes pulls to obtain new materials."""
    if precision_mode:
        simulator.optimized_bulk_pull(PRECISION_BULK_PULLS)
        logging.debug("Pulling materials in precision mode.")
    else:
        simulator.optimized_bulk_pull(SIMULATION_BULK_PULLS)
        logging.debug("Pulling materials in fast mode.")


def process_pity(simulator: GachaSimulator) -> None:
    """Manages the pity system for guaranteed rewards."""
    if simulator.combine_pity_counter >= PITY_COMBINE_CONFIG["THRESHOLD"]:
        num_pities = simulator.combine_pity_counter // PITY_COMBINE_CONFIG["THRESHOLD"]
        simulator.combine_pity_counter %= PITY_COMBINE_CONFIG["THRESHOLD"]
        for _ in range(num_pities):
            reward = random.choice(simulator.familiars)
            simulator.inventory[reward][PITY_COMBINE_CONFIG["REWARD_RARITY"]] += 1
        logging.debug(f"{num_pities} pity reward(s) processed.")


def run_simulation(targets: Dict, methods: Dict, initial_inventory: Dict) -> Tuple[int, Dict]:
    """
    Runs a full simulation with the final optimized AI loop.
    """
    simulator = GachaSimulator()
    combiner = CombineSystem()

    if initial_inventory:
        logging.info("Loading initial inventory...")
        for familiar, rarities in initial_inventory.items():
            if familiar in simulator.inventory:
                for rarity, qty in rarities.items():
                    simulator.inventory[familiar][rarity] = qty
            else:
                logging.warning(f"Familiar '{familiar}' from initial inventory is not active in this simulation. Skipping.")

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
        np.random.seed(RANDOM_SEED)

    highest_target_rarity = max((r for r, q in targets.items() if q > 0), default=0)

    while not check_targets_met(simulator.inventory, targets):
        made_progress = False

        # The AI tries the best possible action, starting from the hardest combine
        for rarity_to_create in range(highest_target_rarity, 7, -1):
            method_to_use = methods.get(rarity_to_create)
            if not method_to_use: 
                continue
            
            # Checks if items of this rarity still need to be created
            if count_rarity(simulator.inventory, rarity_to_create) >= targets.get(rarity_to_create, 0):
                # If target is met for this rarity, only continue if it's a required material for a higher tier
                is_material_needed = any(count_rarity(simulator.inventory, r) < targets.get(r, 0) for r in range(rarity_to_create + 1, 11))
                if not is_material_needed:
                    continue

            source_rarity = STRATEGIC_COMBINE_RULES[rarity_to_create]['from']
            required_qty = STRATEGIC_COMBINE_RULES[rarity_to_create][method_to_use]['recipe']

            # 1. Find ALL viable candidates
            viable_candidates = [
                fam for fam in simulator.familiars
                if (simulator.inventory[fam][source_rarity] + 
                    (1 if (fam, source_rarity) in simulator.combine_credits else 0)) >= required_qty
            ]
            if not viable_candidates: 
                continue

            # 2. Among viable ones, choose the BEST (prioritizing diversification)
            new_candidates = [c for c in viable_candidates if simulator.inventory[c][rarity_to_create] == 0]
            best_candidate = new_candidates[0] if new_candidates else viable_candidates[0]

            # 3. Execute the action
            success, points, msg, updated_credits = combiner.strategic_combine(
                simulator.inventory, simulator.combine_credits,
                rarity_to_create, best_candidate, method_to_use
            )
            
            simulator.combine_credits = updated_credits
            simulator.combine_pity_counter += points
            made_progress = True
            logging.debug(f"Action: Combine {rarity_to_create}* with {best_candidate} - {msg}")
            break
        
        if made_progress:
            process_pity(simulator)
            continue

        if try_auto_combine(simulator, combiner):
            continue

        current_qty = count_rarity(simulator.inventory, highest_target_rarity)
        target_qty = targets.get(highest_target_rarity, 0)
        precision_mode = target_qty > 0 and (current_qty / target_qty) >= PRECISION_THRESHOLD
        
        try_pull_materials(simulator, targets, precision_mode)

    return simulator.diamonds_spent, simulator.inventory


# ============================ MAIN EXECUTION ==============================

if __name__ == "__main__":
    
    # 1. Load valid names (just for the input validation)
    try:
        valid_names = GachaSimulator().familiars
    except Exception as e:
        print(f"Fatal error loading configuration: {e}")
        exit()

    # 2. Ask for targets ONCE
    quantity_targets, methods_per_rarity = get_user_targets()
    
    # 3. Ask for initial inventory ONCE
    initial_inventory = get_initial_inventory(valid_names)

    if not any(quantity_targets.values()):
        print("\nNo targets defined. Shutting down.")
        exit(0)

    # 4. Ask for the number of simulations ONCE
    while True:
        try:
            num_simulations = int(input("How many times do you want to run the simulation? ") or 1)
            if num_simulations <= 0: 
                raise ValueError
            break
        except ValueError:
            print("Invalid input. Enter a positive integer greater than zero.")

    # 5. Run simulations ONCE
    all_results = []
    print("\nStarting simulations... This might take some time.\n")

    for _ in tqdm(range(num_simulations), desc="Simulating"):
        cost, final_inventory = run_simulation(quantity_targets, methods_per_rarity, initial_inventory)
        all_results.append((cost, final_inventory))

    # 6. Process and display final results ONCE
    costs_np = np.array([res[0] for res in all_results])

    print("\n" + "=" * 60)
    print("--- FINAL SIMULATION RESULTS ---")
    print("=" * 60)

    for rarity, qty in quantity_targets.items():
        if qty > 0:
            method = methods_per_rarity[rarity].replace("probabilistic", "25%").replace("guaranteed", "100%")
            print(f"  - {qty}x Familiar {rarity}* ({method} method)")

    print(f"\nBased on {num_simulations} simulations:")
    print(f"  - Average Cost: {np.mean(costs_np):,.0f} diamonds".replace(",", "."))
    print(f"  - Lowest Sim Cost: {np.min(costs_np):,.0f} diamonds".replace(",", "."))
    print(f"  - Highest Sim Cost: {np.max(costs_np):,.0f} diamonds".replace(",", "."))
    print(f"  - Median: {np.median(costs_np):,.0f} diamonds".replace(",", "."))
    print(f"  - Standard Deviation: {np.std(costs_np):,.0f} diamonds".replace(",", "."))
    
    # Representative result extraction
    highest_target_rarity = max((r for r, q in quantity_targets.items() if q > 0), default=0)
    if highest_target_rarity > 0 and all_results:
        average_cost = np.mean(costs_np)
        representative_result = min(all_results, key=lambda x: abs(x[0] - average_cost))
        representative_inventory = representative_result[1]
        
        print(f"\nExample of Result (from the simulation with the cost closest to the average):")
        print(f"Familiars obtained with {highest_target_rarity}*:")
        
        familiars_found = False
        for familiar, rarities in sorted(representative_inventory.items()):
            qty = rarities.get(highest_target_rarity, 0)
            if qty > 0:
                print(f"  - {familiar}: {qty}x ({highest_target_rarity}*)")
                familiars_found = True
        
        if not familiars_found:
            print(f"  - No familiar reached rarity {highest_target_rarity}* in this simulation.")
    
    print("=" * 60)
