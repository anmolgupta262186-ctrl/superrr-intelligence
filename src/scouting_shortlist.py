
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/official")
REL = BASE / "reliability"
OUT = BASE / "scouting"

availability = pd.read_csv(
    OUT / "player_availability_2027.csv"
)

# ---------------------------------
# 1. BATTING CANDIDATES
# ---------------------------------

bat = pd.read_csv(
    REL / "batting_consistency_eligible.csv"
)

bat = bat.merge(
    availability.drop(columns=["player_name"]),
    left_on="striker_id",
    right_on="player_id",
    how="left",
    validate="many_to_one"
)

bat = bat.sort_values(
    "sr_change",
    ascending=False
)

bat.to_csv(
    OUT / "batting_scouting_watchlist.csv",
    index=False
)

# ---------------------------------
# 2. BOWLING CANDIDATES
# ---------------------------------

bowl = pd.read_csv(
    REL / "bowling_comparison_eligible.csv"
)

bowl = bowl.merge(
    availability.drop(columns=["player_name"]),
    left_on="bowler_id",
    right_on="player_id",
    how="left",
    validate="many_to_one"
)

bowl = bowl.sort_values(
    "run_rate_improvement",
    ascending=False
)

bowl.to_csv(
    OUT / "bowling_scouting_watchlist.csv",
    index=False
)

# ---------------------------------
# 3. POTENTIAL CANDIDATES
# ---------------------------------

def show_watchlist(data, name_col, metric):
    subset = data[
        data["squad_status_2026"] ==
        "No 2026 squad record"
    ]

    print("\nPotential candidates to investigate:")
    print(
        subset[
            [name_col, "match_format", "phase",
             metric, "status_2027"]
        ].head(15).round(2).to_string(index=False)
    )

print("\n=== BATTING WATCHLIST ===")
show_watchlist(bat, "striker_name", "sr_change")

print("\n=== BOWLING WATCHLIST ===")
show_watchlist(
    bowl, "bowler_name", "run_rate_improvement"
)

print("\nFiles saved to:", OUT)
