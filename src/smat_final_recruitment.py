
from pathlib import Path
import pandas as pd
import numpy as np
import re

BASE = Path("data/processed")
SMAT = BASE / "domestic/smat"
AUCTION = BASE / "auction2027"
OUT = SMAT / "final"

OUT.mkdir(parents=True, exist_ok=True)

# 1. Load data

bat = pd.read_csv(
    SMAT / "pri/external_batting_pri_ranked.csv"
)

bowl = pd.read_csv(
    SMAT / "pri/external_bowling_pri_ranked.csv"
)

balls = pd.read_csv(
    SMAT / "smat_pressure_deliveries.csv",
    low_memory=False
)

retention = pd.read_csv(
    "data/raw/auction2027/retention_list.csv"
)

mapping = pd.read_csv(
    BASE / "unified/consolidated_identity_mapping.csv",
    dtype=str
)

people = pd.read_csv(
    "data/raw/register/people.csv",
    dtype=str
)

names = pd.read_csv(
    "data/raw/register/names.csv",
    dtype=str
)

# 2. Standardise columns

bat = bat.rename(columns={
    "striker_id": "external_player_id",
    "striker_name": "player_name",
    "batting_pri": "pri"
})

bowl = bowl.rename(columns={
    "bowler_id": "external_player_id",
    "bowler_name": "player_name",
    "bowling_pri": "pri"
})

bat["skill"] = "Batting"
bowl["skill"] = "Bowling"
bowl["batting_role"] = "Bowler"

df = pd.concat([bat, bowl], ignore_index=True)
df = df[df["pri"].notna()].copy()

# 3. Assign recruitment roles

def role(row):

    if row["skill"] == "Bowling":
        return {
            "Death": "Death Bowler",
            "Powerplay": "Powerplay Bowler",
            "Middle": "Middle Over Bowler"
        }.get(row["phase"], "Other")

    if (
        row["phase"] == "Death"
        and row["batting_role"] in [
            "Middle Order", "Lower Middle Order"
        ]
    ):
        return "Finisher"

    if row["batting_role"] == "Middle Order":
        return "Middle Order Batter"

    if row["batting_role"] == "Opener":
        return "Backup Opener"

    return "Other"


df["target_role"] = df.apply(role, axis=1)

# 4. Weakness Handling Index

weights = {
    "Middle Order Batter": {
        "sr_pressure": (0.30, True),
        "dismissal_rate_pressure": (0.35, False),
        "boundary_pct_pressure": (0.15, True),
        "dot_pct_pressure": (0.20, False)
    },

    "Finisher": {
        "sr_pressure": (0.40, True),
        "dismissal_rate_pressure": (0.15, False),
        "boundary_pct_pressure": (0.30, True),
        "dot_pct_pressure": (0.15, False)
    },

    "Death Bowler": {
        "economy_pressure": (0.50, False),
        "wicket_rate_pressure": (0.30, True),
        "dot_pct_pressure": (0.20, True)
    },

    "Powerplay Bowler": {
        "economy_pressure": (0.30, False),
        "wicket_rate_pressure": (0.50, True),
        "dot_pct_pressure": (0.20, True)
    },

    "Middle Over Bowler": {
        "economy_pressure": (0.40, False),
        "wicket_rate_pressure": (0.40, True),
        "dot_pct_pressure": (0.20, True)
    }
}

df["whi"] = np.nan

groups = [
    "skill", "phase",
    "batting_role", "baseline_category"
]

for _, group in df.groupby(groups):

    if group["external_player_id"].nunique() < 5:
        continue

    target = group["target_role"].iloc[0]

    metrics = weights.get(target)

    if metrics is None:
        continue

    score = pd.Series(0.0, index=group.index)
    coverage = pd.Series(0.0, index=group.index)

    for metric, (weight, higher) in metrics.items():

        if metric not in group:
            continue

        values = pd.to_numeric(
            group[metric], errors="coerce"
        )

        if values.notna().sum() < 5:
            continue

        percentile = values.rank(
            pct=True,
            ascending=higher
        ) * 100

        score += percentile.fillna(0) * weight
        coverage += values.notna() * weight

    raw = score / coverage.replace(0, np.nan)

    confidence = (
        group["balls_pressure"]
        / (group["balls_pressure"] + 50)
    )

    whi = 50 + confidence * (raw - 50)

    df.loc[group.index, "whi"] = whi.where(
        coverage >= 0.80
    )

df["rri"] = 0.50 * df["pri"] + 0.50 * df["whi"]

# 5. Recent role-specific pressure evidence

balls["match_date"] = pd.to_datetime(
    balls["match_date"], errors="coerce"
)

recent = balls[
    balls["match_date"] >= "2022-01-01"
].copy()

recent_bat = recent[
    recent["batting_pressure_category"] == "High"
].groupby([
    "striker_id", "phase", "batting_role"
]).agg(
    recent_pressure_balls=("batter_ball", "sum"),
    recent_pressure_matches=("match_id", "nunique"),
    recent_runs=("batter_runs", "sum"),
    last_pressure_date=("match_date", "max")
).reset_index().rename(columns={
    "striker_id": "external_player_id"
})

recent_bowl = recent[
    recent["bowling_pressure_category"] == "High"
].groupby([
    "bowler_id", "phase"
]).agg(
    recent_pressure_balls=("is_legal", "sum"),
    recent_pressure_matches=("match_id", "nunique"),
    recent_runs=("bowler_runs", "sum"),
    last_pressure_date=("match_date", "max")
).reset_index().rename(columns={
    "bowler_id": "external_player_id"
})

recent_bat["skill"] = "Batting"
recent_bowl["skill"] = "Bowling"
recent_bowl["batting_role"] = "Bowler"

recent_stats = pd.concat(
    [recent_bat, recent_bowl],
    ignore_index=True
)

df = df.merge(
    recent_stats,
    on=[
        "external_player_id",
        "phase", "batting_role", "skill"
    ],
    how="left"
)

df["recent_pressure_balls"] = (
    df["recent_pressure_balls"].fillna(0)
)

df["recent_evidence"] = np.select(
    [
        (df["recent_pressure_balls"] >= 24)
        & (df["recent_pressure_matches"] >= 3),

        df["recent_pressure_balls"] > 0
    ],
    [
        "Recent supporting sample",
        "Limited recent sample"
    ],
    default="Historical evidence only"
)

# 6. Identity mapping

identity = mapping[[
    "external_player_id",
    "unified_player_id",
    "official_player_name"
]].dropna(subset=["external_player_id"])

identity = identity.drop_duplicates(
    "external_player_id"
)

df = df.merge(
    identity,
    on="external_player_id",
    how="left",
    validate="many_to_one"
)

df["unified_player_id"] = (
    df["unified_player_id"]
    .fillna("EXT_" + df["external_player_id"])
)

full_names = people.set_index(
    "identifier"
)["unique_name"].to_dict()

df["canonical_name"] = (
    df["official_player_name"]
    .combine_first(
        df["external_player_id"].map(full_names)
    )
    .fillna(df["player_name"])
)

# 7. IPL availability screening

def normalize(name):
    if pd.isna(name):
        return ""
    return re.sub(
        r"[^a-z0-9]", "", str(name).lower()
    )

retention["key"] = retention[
    "player_name"
].apply(normalize)

registry = pd.concat([
    people[["identifier", "name"]],
    people[["identifier", "unique_name"]]
    .rename(columns={"unique_name": "name"}),
    names[["identifier", "name"]]
]).dropna().drop_duplicates()

registry["key"] = registry["name"].apply(normalize)

unique_keys = registry.groupby(
    "key"
)["identifier"].nunique()

registry = registry[
    registry["key"].isin(
        unique_keys[unique_keys == 1].index
    )
]

aliases = registry.groupby(
    "identifier"
)["key"].agg(set).to_dict()

def availability(row):

    keys = set(aliases.get(
        row["external_player_id"], set()
    ))

    keys.add(normalize(row["canonical_name"]))

    matched = retention[
        retention["key"].isin(keys)
    ]

    if len(matched) > 1:
        return "Hold - Identity review"

    if matched.empty:
        return "Availability pending"

    record = matched.iloc[0]

    if record["status"] in [
        "Retained", "Traded",
        "Retired", "Withdrawn"
    ]:
        return "Excluded - " + record["status"]

    if record["status"] == "Released":
        return "Released - Registration pending"

    return "Hold - Retention review"

df["recruitment_status"] = df.apply(
    availability, axis=1
)

df["source"] = "Expanded SMAT"
df["competition"] = "Syed Mushtaq Ali Trophy"

# 8. Save complete domestic analysis

df.to_csv(
    OUT / "smat_complete_analysis.csv",
    index=False
)

scouting = df[
    df["rri"].notna()
    & ~df["recruitment_status"].str.startswith(
        ("Excluded", "Hold")
    )
].copy()

scouting.to_csv(
    OUT / "smat_recruitment_pool.csv",
    index=False
)

# 9. Domestic role-wise rankings

for (role, baseline), group in scouting.groupby(
    ["target_role", "baseline_category"]
):

    top = group.sort_values(
        ["rri", "recent_pressure_balls"],
        ascending=False
    ).drop_duplicates("unified_player_id")

    filename = (
        baseline + "_" + role
    ).lower().replace(" ", "_")

    top.to_csv(
        OUT / f"{filename}.csv",
        index=False
    )

    print(f"\n=== {role} | {baseline} ===")

    print(top[[
        "canonical_name",
        "pri", "whi", "rri",
        "recent_pressure_balls",
        "recent_evidence",
        "recruitment_status"
    ]].head(10).round(2).to_string(index=False))

# 10. Integrate global and domestic evidence

global_data = pd.read_csv(
    AUCTION / "pressure_validated"
    / "pressure_validated_master.csv",
    low_memory=False
)

# Replace overlapping SMAT ranking evidence
# rather than counting it twice.

global_data = global_data[
    global_data["competition"]
    != "Syed Mushtaq Ali Trophy"
].copy()

combined = pd.concat(
    [global_data, scouting],
    ignore_index=True
)

combined.to_csv(
    OUT / "combined_global_domestic_evidence.csv",
    index=False
)

print("\n=== FINAL SUMMARY ===")

print("SMAT ranked players:",
      df["unified_player_id"].nunique())

print("SMAT recruitment prospects:",
      scouting["unified_player_id"].nunique())

print("Combined player IDs:",
      combined["unified_player_id"].nunique())

print("\n=== RECENCY COVERAGE ===")
print(scouting["recent_evidence"].value_counts())

print("\nSaved results to:", OUT)
