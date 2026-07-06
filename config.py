# config.py
# This file contains all game rules and constants.

# --- COST SIMULATION CONTROLES ---
# Use these variables to define the current simulation rules.
MAX_RARITY = 10 # Defines the maximum size of the pulls inventory. DO NOT CHANGE THIS VALUE
SIMULATION_BULK_PULLS = 1100 # Size of the pull batch the simulator will perform at once when materials are needed.
PRECISION_BULK_PULLS = 110 # Smaller batch to be used when the simulation is close to the target.
PRECISION_THRESHOLD = 0.5     # Percentage of the target to activate precision mode

# --- FAMILIARS DATABASE ---
# The complete list with all 12 possible names.
NUM_ACTIVE_CATEGORIES = 3 # Maximum 3
ACTIVE_FAMILIARS_PER_CATEGORY = 4 # Maximum 4
FAMILIAR_NAMES = [
    # --- Attribute Category ---
    "HI", "TI", "JE", "A",
    # --- Battle Category ---
    "KU", "PE", "SHA", "PO",
    # --- Weapon Category ---
    "NA", "RU", "RION", "MUS"
]
TOTAL_FAMILIARS_PER_CATEGORY_IN_LIST = 4 # Constant that defines the structure of the list above. DO NOT CHANGE THIS VALUE. (Unless you add a fifth familiar to each category)

# --- GACHA ---
GACHA_CONFIG = {
    "SINGLE_PULL_COST": 500,
    "MULTI_PULL_COST": 5000,
    "MULTI_PULL_QTY": 11,
    "DROP_RATES": { 0: 0.5228, 1: 0.2612, 2: 0.1274, 3: 0.0520, 4: 0.0214, 5: 0.0121, 6: 0.0023, 7: 0.0007, 8: 0.0001 },
    "PITY_PULLS_THRESHOLD": 300,
    "PITY_PULLS_REWARD_RARITY": 6,
}

# --- COMBINATION ---
AUTO_COMBINE_RULES = {
    1: 2, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3
}

STRATEGIC_COMBINE_RULES = {
    8: {
        'from': 7,
        'probabilistic': {'recipe': 2, 'sacrifice': 1, 'success_chance': 0.25},
        'guaranteed':      {'recipe': 5}
    },
    9: {
        'from': 8,
        'probabilistic': {'recipe': 2, 'sacrifice': 1, 'success_chance': 0.25},
        'guaranteed':      {'recipe': 5}
    },
    10: {
        'from': 9,
        'guaranteed':      {'recipe': 2}
    }
}

PITY_COMBINE_CONFIG = {
    "THRESHOLD": 300,
    "REWARD_RARITY": 7,
    "POINTS": {
        8:  {'prob_success': 516, 'prob_failure': 48, 'guaranteed_success': 516},
        9:  {'prob_success': 900, 'prob_failure': 172, 'guaranteed_success': 900},
        10: {'guaranteed_success': 0}
    }
}
