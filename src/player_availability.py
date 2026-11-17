
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/rr_official")
RELIABILITY = Path("data/processed/official/reliability")
OUT = Path("data/processed/official/scouting")
OUT.mkdir(parents=True, exist_ok=True)

RR = "Rajasthan Royals"
IPL_2026_ID = 3298

# ------------------------------------
# 1. LOAD IPL 2026 SQUAD MAPPINGS
# ------------------------------------

mapping = pd.read_csv(
    RAW / "competition_team_player_mapping.csv"
)

ipl = mapping[
    mapping["comp_id"] == IPL_2026_ID
].copy()

# A player may appear in multiple team records
squads = (
    ipl.groupby("player_id", as_index=False)
    .agg(
        player_name=("player_name", "first"),
        ipl_2026_teams=(
            "team_name",
            lambda x: ", ".join(sorted(set(x.dropna())))
        )
    )
)

# ------------------------------------
# 2. BUILD PLAYER REGISTRY
# ------------------------------------

bat = pd.read_csv(
    RELIABILITY / "batting_consistency_eligible.csv"
)

bowl = pd.read_csv(
    RELIABILITY / "bowling_comparison_eligible.csv"
)

batters = bat[["striker_id", "striker_name"]].rename(
    columns={
        "striker_id": "player_id",
        "striker_name": "player_name"
    }
)

bowlers = bowl[["bowler_id", "bowler_name"]].rename(
    columns={
        "bowler_id": "player_id",
        "bowler_name": "player_name"
    }
)

registry = pd.concat(
    [batters, bowlers],
    ignore_index=True
).drop_duplicates("player_id")

registry = registry.drop(
    columns=["player_name"]
).merge(
    squads,
    on="player_id",
    how="left",
    validate="one_to_one"
)

# ------------------------------------
# 3. CLASSIFY IPL 2026 AFFILIATION
# ------------------------------------

def classify_2026(teams):
    if pd.isna(teams):
        return "No 2026 squad record"

    team_list = [t.strip() for t in teams.split(",")]

    if RR in team_list:
        return "RR squad 2026"

    return "Other IPL franchise 2026"


registry["squad_status_2026"] = (
    registry["ipl_2026_teams"].apply(classify_2026)
)

# ------------------------------------
# 4. CREATE 2027 AVAILABILITY TRACKER
# ------------------------------------

# Update these fields after official 2027
# retention, release and auction announcements.

registry["nationality"] = "Unknown"
registry["ipl_eligibility"] = "Unverified"
registry["capped_status"] = "Unknown"
registry["age"] = pd.NA

registry["status_2027"] = "Unverified"
registry["auction_registered_2027"] = "Unknown"

registry["availability_source"] = ""
registry["availability_verified_date"] = ""

# ------------------------------------
# 5. SAVE TRACKER
# ------------------------------------

tracker_file = OUT / "player_availability_2027.csv"

registry.to_csv(tracker_file, index=False)

print("\n=== IPL 2026 SQUAD STATUS ===")
print(registry["squad_status_2026"].value_counts())

print("\n=== PLAYER REGISTRY ===")
print("Total players:", len(registry))
print("Mapped to IPL 2026:", registry["ipl_2026_teams"].notna().sum())

print("\n=== 2027 AVAILABILITY ===")
print(registry["status_2027"].value_counts())

print("\nSaved:", tracker_file)
