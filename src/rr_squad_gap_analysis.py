
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/auction2027")
OUT = Path("data/processed/auction2027")

OUT.mkdir(parents=True, exist_ok=True)

AUCTION_PURSE = 27.05
MAX_SQUAD_SIZE = 25
MAX_OVERSEAS = 8

# ------------------------------------
# 1. LOAD RR RETAINED SQUAD
# ------------------------------------

squad = pd.read_csv(
    RAW / "rr_squad_2027.csv"
)

squad = squad[
    squad["status"].isin(["Retained", "Traded"])
].copy()

# ------------------------------------
# 2. PLAYER ROLE CLASSIFICATION
# ------------------------------------

ROLES = {
    "Yashasvi Jaiswal":
        ("Opener", "Indian", "Powerplay"),

    "Vaibhav Sooryavanshi":
        ("Opener", "Indian", "Powerplay"),

    "Aman Rao Perala":
        ("Opener", "Indian", "Powerplay"),

    "Riyan Parag":
        ("Middle Order", "Indian", "Middle"),

    "Dhruv Jurel":
        ("Wicketkeeper Batter", "Indian", "Middle, Death"),

    "Shubham Dubey":
        ("Finisher", "Indian", "Death"),

    "Ravindra Jadeja":
        ("Bowling All-rounder", "Indian", "Middle, Death"),

    "Donovan Ferreira":
        ("Batting All-rounder", "Overseas", "Middle, Death"),

    "Dasun Shanaka":
        ("Batting All-rounder", "Overseas", "Death"),

    "Lhuan-dre Pretorius":
        ("Wicketkeeper Batter", "Overseas", "Powerplay"),

    "Jofra Archer":
        ("Fast Bowler", "Overseas", "Powerplay, Death"),

    "Mohammed Shami":
        ("Fast Bowler", "Indian", "Powerplay"),

    "Nandre Burger":
        ("Fast Bowler", "Overseas", "Powerplay"),

    "Sandeep Sharma":
        ("Fast Bowler", "Indian", "Powerplay, Death"),

    "Brijesh Sharma":
        ("Fast Bowler", "Indian", "Powerplay, Death"),

    "Sushant Mishra":
        ("Fast Bowler", "Indian", "Powerplay"),

    "Ravi Bishnoi":
        ("Spinner", "Indian", "Middle"),

    "Yash Punja":
        ("Spinner", "Indian", "Middle"),

    "Manimaran Siddharth":
        ("Spinner", "Indian", "Powerplay, Middle")
}

squad["primary_role"] = squad["player_name"].map(
    lambda x: ROLES.get(
        x, ("Unknown", "Unknown", "Unknown")
    )[0]
)

squad["player_category"] = squad["player_name"].map(
    lambda x: ROLES.get(
        x, ("Unknown", "Unknown", "Unknown")
    )[1]
)

squad["preferred_phase"] = squad["player_name"].map(
    lambda x: ROLES.get(
        x, ("Unknown", "Unknown", "Unknown")
    )[2]
)

# ------------------------------------
# 3. SQUAD CAPACITY
# ------------------------------------

total_players = len(squad)

overseas_players = (
    squad["player_category"] == "Overseas"
).sum()

indian_players = (
    squad["player_category"] == "Indian"
).sum()

remaining_slots = MAX_SQUAD_SIZE - total_players

remaining_overseas = (
    MAX_OVERSEAS - overseas_players
)

# ------------------------------------
# 4. HISTORICAL WEAKNESSES
# ------------------------------------

gaps = [
    {
        "role": "Death Bowler",
        "historical_priority": 100,
        "updated_priority": 100,
        "reason": "Expensive death bowling and inconsistency"
    },
    {
        "role": "No. 4 Batter",
        "historical_priority": 95,
        "updated_priority": 95,
        "reason": "Middle-order instability"
    },
    {
        "role": "No. 5 Batter",
        "historical_priority": 95,
        "updated_priority": 95,
        "reason": "Middle-order scoring and wicket losses"
    },
    {
        "role": "Finisher",
        "historical_priority": 90,
        "updated_priority": 95,
        "reason": "Death batting weakness and Hetmyer release"
    },
    {
        "role": "Backup Fast Bowler",
        "historical_priority": 75,
        "updated_priority": 80,
        "reason": "Pace bowling depth"
    },
    {
        "role": "Powerplay Bowler",
        "historical_priority": 100,
        "updated_priority": 70,
        "reason": "Shami acquisition improves potential coverage"
    },
    {
        "role": "Batting All-rounder",
        "historical_priority": 70,
        "updated_priority": 65,
        "reason": "Additional batting depth"
    },
    {
        "role": "Bowling All-rounder",
        "historical_priority": 60,
        "updated_priority": 55,
        "reason": "Squad balance"
    },
    {
        "role": "Spinner",
        "historical_priority": 60,
        "updated_priority": 40,
        "reason": "Existing spin bowling options"
    },
    {
        "role": "Backup Wicketkeeper",
        "historical_priority": 40,
        "updated_priority": 30,
        "reason": "Existing wicketkeeping options"
    },
    {
        "role": "Backup Opener",
        "historical_priority": 30,
        "updated_priority": 20,
        "reason": "Strong existing opening combination"
    }
]

gaps = pd.DataFrame(gaps)

gaps = gaps.sort_values(
    "updated_priority",
    ascending=False,
    kind="stable"
).reset_index(drop=True)

gaps.insert(0, "rank", range(1, len(gaps) + 1))

# ------------------------------------
# 5. PROPOSED AUCTION ALLOCATION
# ------------------------------------

allocation = pd.DataFrame([
    ["Death Bowler", 8.00, 1],
    ["Middle Order Batter", 6.00, 1],
    ["Finisher", 5.00, 1],
    ["Fast Bowler", 3.50, 1],
    ["Batting All-rounder", 3.00, 1],
    ["Emerging Domestic Talent", 1.55, 1]
], columns=[
    "target_role",
    "allocated_budget_crore",
    "target_players"
])

# ------------------------------------
# 6. SAVE RESULTS
# ------------------------------------

squad.to_csv(
    OUT / "rr_retained_squad_roles.csv",
    index=False
)

gaps.to_csv(
    OUT / "rr_squad_requirements.csv",
    index=False
)

allocation.to_csv(
    OUT / "rr_proposed_auction_budget.csv",
    index=False
)

# ------------------------------------
# 7. DISPLAY RESULTS
# ------------------------------------

print("\n=== RR CURRENT SQUAD ===")

print("Total players:", total_players)
print("Indian players:", indian_players)
print("Overseas players:", overseas_players)

print("Remaining squad slots:", remaining_slots)
print("Remaining overseas slots:", remaining_overseas)

print("Auction purse:", AUCTION_PURSE, "crore")

print("\n=== ROLE DISTRIBUTION ===")
print(squad["primary_role"].value_counts())

print("\n=== RR SQUAD REQUIREMENTS ===")

print(gaps[[
    "rank",
    "role",
    "historical_priority",
    "updated_priority"
]].to_string(index=False))

print("\n=== PROPOSED AUCTION BUDGET ===")
print(allocation.to_string(index=False))

print("\nTotal allocated budget:",
      round(allocation["allocated_budget_crore"].sum(), 2))

print("Target purchases:",
      allocation["target_players"].sum())

print("\nUnknown player roles:",
      (squad["primary_role"] == "Unknown").sum())

print("\nSaved results to:", OUT)
