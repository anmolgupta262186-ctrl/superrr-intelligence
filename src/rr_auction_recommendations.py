
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed")
PERF = BASE / "unified/performance"
AUCTION = BASE / "auction2027"

OUT = AUCTION / "recommendations"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD DATA
# ------------------------------------

bat = pd.read_csv(
    PERF / "unified_batting_performance.csv",
    low_memory=False
)

bowl = pd.read_csv(
    PERF / "unified_bowling_performance.csv",
    low_memory=False
)

availability = pd.read_csv(
    AUCTION / "filtered_scouting_registry.csv"
)

requirements = pd.read_csv(
    AUCTION / "rr_squad_requirements.csv"
)

mapping = pd.read_csv(
    BASE / "unified/consolidated_identity_mapping.csv",
    dtype=str
)

priorities = requirements.set_index(
    "role"
)["updated_priority"].to_dict()

# ------------------------------------
# 2. OFFICIAL BATTING POSITIONS
# ------------------------------------

official = pd.read_csv(
    BASE / "official/clean_deliveries.csv",
    dtype={"striker_id": str},
    low_memory=False
)

official["unified_player_id"] = (
    "RR_" + official["striker_id"]
)

official["batting_role"] = np.select(
    [
        official["batting_order"].between(1, 2),
        official["batting_order"] == 3,
        official["batting_order"].between(4, 5),
        official["batting_order"].between(6, 7),
        official["batting_order"] >= 8
    ],
    [
        "Opener",
        "Top Order",
        "Middle Order",
        "Lower Middle Order",
        "Lower Order"
    ],
    default="Unknown"
)

role_counts = (
    official.groupby([
        "unified_player_id",
        "match_format",
        "phase",
        "batting_role"
    ], as_index=False)["batter_ball"]
    .sum()
)

role_counts = role_counts.sort_values(
    "batter_ball",
    ascending=False
)

dominant_roles = role_counts.drop_duplicates([
    "unified_player_id",
    "match_format",
    "phase"
])

dominant_roles = dominant_roles.rename(
    columns={"batting_role": "inferred_role"}
)

bat = bat.merge(
    dominant_roles[[
        "unified_player_id",
        "match_format",
        "phase",
        "inferred_role"
    ]],
    on=[
        "unified_player_id",
        "match_format",
        "phase"
    ],
    how="left"
)

bat["batting_role"] = (
    bat["batting_role"]
    .fillna(bat["inferred_role"])
    .fillna("Unknown")
)

# ------------------------------------
# 3. CLASSIFY RECRUITMENT ROLES
# ------------------------------------

def batting_role(row):

    role = row["batting_role"]
    phase = row["phase"]

    if (
        role in ["Middle Order", "Lower Middle Order"]
        and phase == "Death"
    ):
        return "Finisher"

    if role == "Middle Order":
        return "Middle Order Batter"

    if role == "Opener":
        return "Backup Opener"

    return "Other Batting Role"


def bowling_role(row):

    if row["phase"] == "Death":
        return "Death Bowler"

    if row["phase"] == "Powerplay":
        return "Powerplay Bowler"

    if row["phase"] == "Middle":
        return "Middle Over Bowler"

    return "Other Bowling Role"


bat["target_role"] = bat.apply(
    batting_role, axis=1
)

bowl["target_role"] = bowl.apply(
    bowling_role, axis=1
)

bat["skill"] = "Batting"
bowl["skill"] = "Bowling"

# ------------------------------------
# 4. RR SQUAD PRIORITIES
# ------------------------------------

ROLE_PRIORITY = {
    "Death Bowler": priorities["Death Bowler"],

    "Middle Order Batter": max(
        priorities["No. 4 Batter"],
        priorities["No. 5 Batter"]
    ),

    "Finisher": priorities["Finisher"],

    "Powerplay Bowler":
        priorities["Powerplay Bowler"],

    "Middle Over Bowler": 40,

    "Backup Opener": priorities["Backup Opener"]
}

# ------------------------------------
# 5. COMBINE PERFORMANCE EVIDENCE
# ------------------------------------

combined = pd.concat(
    [bat, bowl],
    ignore_index=True
)

combined = combined[
    combined["pri"].notna()
].copy()

combined = combined[
    combined["target_role"].isin(ROLE_PRIORITY)
].copy()

combined["rr_role_priority"] = (
    combined["target_role"].map(ROLE_PRIORITY)
)

# ------------------------------------
# 6. AVAILABLE PLAYER FILTER
# ------------------------------------

columns = [
    "unified_player_id",
    "final_availability_status",
    "ipl_2027_franchise",
    "ipl_2027_status"
]

combined = combined.merge(
    availability[columns],
    on="unified_player_id",
    how="left",
    validate="many_to_one"
)

combined = combined[
    ~combined["final_availability_status"]
    .fillna("")
    .str.startswith("Excluded")
]

combined = combined[
    combined["final_availability_status"]
    != "Existing RR squad"
].copy()

# ------------------------------------
# 7. PROVISIONAL RECRUITMENT SCORE
# ------------------------------------

# Only use currently available evidence.
# Do not invent age or recent-form scores.

combined["recruitment_score"] = (
    0.50 * combined["pri"]
    + 0.50 * combined["rr_role_priority"]
)

# Keep comparison types separate

combined["comparison_group"] = (
    combined["source"].astype(str)
    + " | "
    + combined["competition"].astype(str)
    + " | "
    + combined["baseline_category"].astype(str)
)

combined = combined.sort_values(
    "recruitment_score",
    ascending=False
)

# ------------------------------------
# 8. RELEASED PLAYER WATCHLIST
# ------------------------------------

released = combined[
    combined["final_availability_status"]
    == "Potential released target"
].copy()

pending = combined[
    combined["final_availability_status"]
    .fillna("")
    .str.startswith("Needs")
].copy()

released.to_csv(
    OUT / "released_player_recommendations.csv",
    index=False
)

pending.to_csv(
    OUT / "unverified_talent_watchlist.csv",
    index=False
)

# ------------------------------------
# 9. INCLUDE SMAT TALENT WATCHLISTS
# ------------------------------------

for skill, player_id, name in [
    ("batting", "striker_id", "striker_name"),
    ("bowling", "bowler_id", "bowler_name")
]:

    smat = pd.read_csv(
        BASE / "external/emerging_talent"
        / f"smat_{skill}_watchlist.csv",
        dtype={player_id: str}
    )

    smat = smat.merge(
        mapping[[
            "external_player_id",
            "unified_player_id"
        ]],
        left_on=player_id,
        right_on="external_player_id",
        how="left",
        validate="many_to_one"
    )

    smat["unified_player_id"] = (
        smat["unified_player_id"]
        .fillna("EXT_" + smat[player_id])
    )

    smat = smat.merge(
        availability[columns],
        on="unified_player_id",
        how="left",
        validate="many_to_one"
    )

    smat = smat[
        ~smat["final_availability_status"]
        .fillna("")
        .str.startswith("Excluded")
    ]

    smat = smat[
        smat["final_availability_status"]
        != "Existing RR squad"
    ].copy()

    if skill == "batting":

        smat["target_role"] = smat.apply(
            batting_role, axis=1
        )

    else:

        smat["target_role"] = smat.apply(
            bowling_role, axis=1
        )

    smat["rr_role_priority"] = (
        smat["target_role"].map(ROLE_PRIORITY)
    )

    smat["evidence_type"] = (
        "Absolute pressure performance"
    )

    smat.to_csv(
        OUT / f"indian_domestic_{skill}_prospects.csv",
        index=False
    )

    print(f"\n=== DOMESTIC {skill.upper()} PROSPECTS ===")

    print(
        smat[[
            name,
            "target_role",
            "final_availability_status"
        ]].to_string(index=False)
    )

# ------------------------------------
# 10. ROLE-SPECIFIC RECOMMENDATIONS
# ------------------------------------

for role in ROLE_PRIORITY:

    candidates = released[
        released["target_role"] == role
    ].copy()

    candidates = candidates.drop_duplicates([
        "unified_player_id",
        "comparison_group"
    ])

    filename = role.lower().replace(" ", "_")

    candidates.to_csv(
        OUT / f"{filename}_targets.csv",
        index=False
    )

    print(f"\n=== {role.upper()} ===")

    if candidates.empty:
        print("No qualifying released players.")
        continue

    for group, data in candidates.groupby(
        "comparison_group"
    ):

        print("\nComparison:", group)

        print(
            data[[
                "player_name",
                "competition",
                "balls_pressure",
                "pri",
                "recruitment_score"
            ]]
            .head(10)
            .round(2)
            .to_string(index=False)
        )

# ------------------------------------
# 11. FINAL SUMMARY
# ------------------------------------

print("\n=== RR RECOMMENDATION SUMMARY ===")

print(
    "Released players with relevant PRI:",
    released["unified_player_id"].nunique()
)

print(
    "Unverified players with relevant PRI:",
    pending["unified_player_id"].nunique()
)

print("\nSaved results to:", OUT)
