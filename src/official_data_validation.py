
import pandas as pd
from pathlib import Path

BASE = Path("data/raw/rr_official")

balls = pd.read_csv(BASE / "ball_by_ball.csv")
matches = pd.read_csv(BASE / "matches.csv")
competitions = pd.read_csv(BASE / "competitions.csv")
players = pd.read_csv(
    BASE / "competition_team_player_mapping.csv"
)
playing = pd.read_csv(BASE / "playing_eleven.csv")

print("\n=== DATASET COVERAGE ===")

print("Total deliveries:", len(balls))
print("Total matches:", matches["match_id"].nunique())
print("Unique batters:", balls["striker_id"].nunique())
print("Unique bowlers:", balls["bowler_id"].nunique())
print("Mapped players:", players["player_id"].nunique())

print("\n=== COMPETITIONS ===")
print(competitions.to_string(index=False))

print("\n=== BATTING ORDER DISTRIBUTION ===")
print(
    balls["batting_order"]
    .value_counts()
    .sort_index()
)

print("\n=== OVER NUMBER RANGE ===")
print("Minimum:", balls["overid"].min())
print("Maximum:", balls["overid"].max())

print("\n=== RUNS DISTRIBUTION ===")
print(balls["runs"].value_counts().sort_index())

print("\n=== EXTRAS TYPES ===")
print(
    balls["extras_type"]
    .value_counts(dropna=False)
)

print("\n=== DISMISSAL TYPES ===")
print(
    balls["dismissal_type"]
    .value_counts(dropna=False)
)

print("\n=== MATCH DATA VALIDATION ===")

missing_matches = (
    set(balls["match_id"]) -
    set(matches["match_id"])
)

print("Deliveries with missing match records:",
      len(missing_matches))

print("Duplicate match IDs:",
      matches["match_id"].duplicated().sum())

print("\n=== PLAYER MAPPING VALIDATION ===")
print("Duplicate mapping rows:",
      players.duplicated().sum())

print("\n=== PLAYING ELEVEN ===")
print("Total records:", len(playing))
print("Unique players:", playing["player_id"].nunique())

print("\nValidation completed.")
