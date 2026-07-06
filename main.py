# main.py

import random
from gacha_system import GachaSimulator
from combine_system import CombineSystem
from config import PITY_COMBINE_CONFIG, GACHA_CONFIG, STRATEGIC_COMBINE_RULES

def display_full_state(simulator: GachaSimulator):
    """Helper function to show the complete simulation state."""
    print("\n" + "="*40)
    print("CURRENT SIMULATION STATE")
    print(f" -> Diamonds Spent: {simulator.diamonds_spent:,}".replace(",", "."))
    print(f" -> Pull Pity: {simulator.pull_pity_counter} / {GACHA_CONFIG['PITY_PULLS_THRESHOLD']}")
    print(f" -> Combine Pity: {simulator.combine_pity_counter} / {PITY_COMBINE_CONFIG['THRESHOLD']}")
    
    if simulator.combine_credits:
        print(" -> Combine Credits (Base Retained):")
        for (familiar, rarity), qty in simulator.combine_credits.items():
            print(f"    - {qty}x {familiar} ({rarity}*)")

    print("="*40)

def display_inventory(simulator: GachaSimulator):
    """Shows the inventory in an organized and compact way."""
    print("\n--- YOUR INVENTORY ---")
    found_something = False
    # Extracts the category letter to group
    familiars_by_category = {}
    for f_name in simulator.familiars:
        # Finds the category by its order in the list, not by name
        index = simulator.familiars.index(f_name)
        category_index = index // simulator.config.get("FAMILIARS_PER_CATEGORY", 4) # Uses 4 as default
        category_letter = "ABC"[category_index]
        if category_letter not in familiars_by_category:
            familiars_by_category[category_letter] = []
        familiars_by_category[category_letter].append(f_name)

    for cat, fams in sorted(familiars_by_category.items()):
        for familiar in sorted(fams):
            items_of_this_familiar = []
            for rarity, quantity in simulator.inventory[familiar].items():
                if quantity > 0:
                    items_of_this_familiar.append(f"{quantity}x ({rarity}*)")
            
            if items_of_this_familiar:
                found_something = True
                # Shows the familiar name and category
                print(f"{familiar}: {', '.join(items_of_this_familiar)}")
    
    if not found_something:
        print("The inventory is empty.")
    print("-" * 22)

def main_menu():
    """Function that manages the interactive menu."""
    simulator = GachaSimulator()
    combiner = CombineSystem()
    print("Welcome to the Gacha and Combine Simulator!")

    while True:
        display_full_state(simulator)

        print("\nWhat would you like to do?")
        print("  --- Gacha ---")
        print("  1. Pull 1x")
        print("  2. Pull 11x")
        print("  --- Combination ---")
        print("  3. Auto Combine (Low Rarities)")
        print("  4. Chain Combine (Strategic)")
        print("  --- Others ---")
        print("  5. View Inventory")
        print("  6. Exit")
        print("  --- Tests ---")
        print("  7. Mass Pull (Fast Forward Time)")
        
        choice = input("Choose an option: ")

        if choice == '1':
            result = simulator.pull_one()
            print(f"\nYou obtained: {result[0]} ({result[1]}*)")
        
        elif choice == '2':
            results = simulator.pull_eleven()
            print("\nYou obtained the following familiars:")
            for familiar, rarity in results:
                print(f"  - {familiar} ({rarity}*)")

        elif choice == '3':
            print("\nExecuting automatic combinations...")
            logs = combiner.auto_combine(simulator.inventory, simulator.familiars)
            if not logs:
                print("No automatic combination was possible.")
            else:
                for log in logs:
                    print(log)
        
        elif choice == '4':
            try:
                print("\n--- Chain Combine ---")
                target_familiar = input(f"What is the name of the target familiar (e.g., {simulator.familiars[0]})? ")
                target_rarity = int(input("What is the final target rarity (8, 9, or 10)? "))

                # Validates familiar name (case-insensitive)
                real_familiar = next((f for f in simulator.familiars if f.lower() == target_familiar.lower()), None)
                if not real_familiar:
                    print("Error: Invalid familiar name.")
                    continue
                
                # Asks for methods for each stage of the chain
                methods = {}
                for r in range(8, target_rarity + 1):
                    if r == 10 and 'probabilistic' not in STRATEGIC_COMBINE_RULES.get(10, {}):
                        print(" -> For 10*, the only method is 100%.")
                        methods[r] = 'guaranteed'
                        continue
                    while True:
                        m_input = input(f" -> Which method to use for the {r}* stage (25 or 100)? ")
                        if m_input == '25':
                            methods[r] = 'probabilistic'
                            break
                        elif m_input == '100':
                            methods[r] = 'guaranteed'
                            break
                        else:
                            print("Invalid input.")

                # Starts the crafting "bot"
                print(f"\nStarting chain combine for {real_familiar} -> {target_rarity}*...")
                general_attempts = 0
                while general_attempts < 100: # Safety limit against infinite loops
                    made_progress = False
                    
                    # The bot works from bottom to top: tries to create 8*, then 9*, etc.
                    for stage_target_rarity in range(8, target_rarity + 1):
                        stage_method = methods[stage_target_rarity]
                        
                        success, points, msg, updated_credits = combiner.strategic_combine(
                            simulator.inventory, simulator.combine_credits, stage_target_rarity, real_familiar, stage_method
                        )
                        
                        # If the attempt was possible (did not return insufficient materials error)
                        if "insufficient" not in msg.lower():
                            print(msg) # Shows step result
                            simulator.combine_credits = updated_credits
                            simulator.combine_pity_counter += points
                            made_progress = True
                            
                            # Checks combine pity
                            if simulator.combine_pity_counter >= PITY_COMBINE_CONFIG["THRESHOLD"]:
                                num_pities = simulator.combine_pity_counter // PITY_COMBINE_CONFIG["THRESHOLD"]
                                simulator.combine_pity_counter %= PITY_COMBINE_CONFIG["THRESHOLD"]
                                for _ in range(num_pities):
                                    reward = random.choice(simulator.familiars)
                                    simulator.inventory[reward][PITY_COMBINE_CONFIG["REWARD_RARITY"]] += 1
                                    print(f"--- COMBINE PITY REACHED! Reward: 1x {reward} 7*! ---")
                            
                            break # If an action was taken, stops and restarts analysis from scratch
                    
                    if made_progress:
                        general_attempts += 1
                        continue # Goes back to the beginning of the loop to try the next step
                    else:
                        # If the entire loop ran and there was no progress, no more materials are available
                        print("\nProcess finished: There are no more materials to continue the combination.")
                        break
                
            except ValueError:
                print("Invalid input. Please enter a number for the rarity.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        elif choice == '5':
            display_inventory(simulator)

        elif choice == '6':
            print("Thank you for using the simulator!")
            break

        elif choice == '7':
            print("\n--- Mass Pull ---")
            print("  1. By number of pulls")
            print("  2. By amount of diamonds")
            sub_choice = input("Choose the method: ")
            
            try:
                pulls_to_do = 0
                if sub_choice == '1':
                    pulls_to_do = int(input("How many pulls do you want to perform? "))

                elif sub_choice == '2':
                    diamond_amount = int(input("How many diamonds do you want to spend? "))
                    # Calculate number of pulls BEFORE calling the function
                    pulls_to_do = diamond_amount // simulator.config["SINGLE_PULL_COST"]
                else:
                    print("Invalid option.")
                
                if pulls_to_do > 0:
                    print(f"Executing {pulls_to_do:,} pulls...".replace(",", "."))
                    # Calls the OPTIMIZED function
                    simulator.optimized_bulk_pull(num_pulls=pulls_to_do)
                    print("Mass pulls completed!")

            except ValueError:
                print("Invalid input. Please enter a number.")
            except Exception as e:
                print(f"An error occurred: {e}")

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main_menu()
