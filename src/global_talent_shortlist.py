
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/auction2027")
REC = BASE / "recommendations"
OUT = BASE / "global_scouting"

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD ALL SCOUTING DATA
# ------------------------------------

released = pd.read_csv(
    REC / "released_player_recommendations.csv"
)

pending = pd.read_csv(
    REC / "unverified_talent_watchlist.csv"
)

domestic_bat = pd.read_csv(
    REC / "indian_domestic_batting_prospects.csv"
)

domestic_bowl = pd.read_csv(
    REC / "indian_domestic_bowling_prospects.csv"
)

released["scouting_pool"] = "Released IPL Player"
pending["scouting_pool"] = "Unverified Prospect"

players = pd.concat(
    [released, pending],
    ignore_index=True
)

players = players[
    players["pri"].notna()
].copy()

# ------------------------------------
# 2. SAFETY FILTER
# ------------------------------------

status = players[
    "final_availability_status"
].fillna("Needs verification")

players = players[
    ~status.str.startswith("Excluded")
    & (status != "Existing RR squad")
].copy()

# ------------------------------------
# 3. ROLE-SPECIFIC SCOUTING
# ------------------------------------

ROLE_LIMITS = {
    "Death Bowler": 10,
    "Middle Order Batter": 10,
    "Finisher": 10,
    "Powerplay Bowler": 10,
    "Middle Over Bowler": 10,
    "Backup Opener": 5
}

columns = [
    "player_name",
    "source",
    "competition",
    "baseline_category",
    "balls_pressure",
    "pri",
    "recruitment_score",
    "scouting_pool",
    "final_availability_status"
]

all_shortlists = []

for role, limit in ROLE_LIMITS.items():

    candidates = players[
        players["target_role"] == role
    ].copy()

    candidates = candidates.sort_values(
        ["pri", "balls_pressure"],
        ascending=[False, False]
    )

    candidates = candidates.drop_duplicates([
        "unified_player_id",
        "comparison_group"
    ])

    # Rank separately by competition,
    # source and baseline category.

    candidates["group_rank"] = (
        candidates.groupby("comparison_group")
        .cumcount() + 1
    )

    shortlist = candidates[
        candidates["group_rank"] <= limit
    ].copy()

    all_shortlists.append(shortlist)

    filename = role.lower().replace(" ", "_")

    shortlist.to_csv(
        OUT / f"global_{filename}.csv",
        index=False
    )

    print(f"\n{'=' * 65}")
    print(f"GLOBAL {role.upper()}")
    print("=" * 65)

    print(
        "Unique candidates:",
        candidates["unified_player_id"].nunique()
    )

    for group, data in shortlist.groupby(
        "comparison_group"
    ):

        print("\nComparison:", group)

        print(
            data[[
                "group_rank",
                "player_name",
                "balls_pressure",
                "pri",
                "scouting_pool"
            ]].round(2).to_string(index=False)
        )

# ------------------------------------
# 4. DOMESTIC TALENT DISCOVERY
# ------------------------------------

for skill, data, name in [
    ("batting", domestic_bat, "striker_name"),
    ("bowling", domestic_bowl, "bowler_name")
]:

    data = data[
        data["target_role"].isin(ROLE_LIMITS)
    ].copy()

    data.to_csv(
        OUT / f"domestic_{skill}_watchlist.csv",
        index=False
    )

    print(f"\n=== DOMESTIC {skill.upper()} ===")

    print(data[[
        name,
        "target_role",
        "final_availability_status"
    ]].to_string(index=False))

# ------------------------------------
# 5. DUAL-SKILL PROSPECTS
# ------------------------------------

batters = players[
    players["skill"] == "Batting"
].copy()

bowlers = players[
    players["skill"] == "Bowling"
].copy()

dual_ids = (
    set(batters["unified_player_id"])
    & set(bowlers["unified_player_id"])
)

dual_skill = players[
    players["unified_player_id"].isin(dual_ids)
].copy()

dual_skill = dual_skill.sort_values([
    "player_name",
    "skill",
    "pri"
], ascending=[True, True, False])

dual_skill.to_csv(
    OUT / "dual_skill_prospects.csv",
    index=False
)

print("\n=== POTENTIAL ALL-ROUNDERS ===")

print(
    dual_skill[[
        "player_name",
        "unified_player_id"
    ]]
    .drop_duplicates()
    ["player_name"]
    .to_string(index=False)
)

# ------------------------------------
# 6. MASTER SCOUTING DATASET
# ------------------------------------

players.to_csv(
    OUT / "global_scouting_master.csv",
    index=False
)

master_shortlist = pd.concat(
    all_shortlists,
    ignore_index=True
)

master_shortlist.to_csv(
    OUT / "global_role_shortlists.csv",
    index=False
)

# ------------------------------------
# 7. FINAL SUMMARY
# ------------------------------------

print("\n=== GLOBAL SCOUTING SUMMARY ===")

print(
    "Total unique players:",
    players["unified_player_id"].nunique()
)

print(
    "Released IPL prospects:",
    released["unified_player_id"].nunique()
)

print(
    "Unverified prospects:",
    pending["unified_player_id"].nunique()
)

print(
    "Potential dual-skill players:",
    len(dual_ids)
)

print("\n=== ROLE-WISE TALENT COVERAGE ===")

print(
    players.groupby("target_role")
    ["unified_player_id"]
    .nunique()
    .sort_values(ascending=False)
)

print("\nSaved results to:", OUT)

