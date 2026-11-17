
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path("data/raw/rr_official")
BASE = Path("data/processed/official")

df = pd.read_csv(
    BASE / "clean_deliveries.csv",
    dtype={"season": str},
    low_memory=False
)

matches = pd.read_csv(RAW / "matches.csv")

# -----------------------------------
# 1. MATCH CONTEXT
# -----------------------------------

df = df.merge(
    matches[["match_id", "knock_out"]],
    on="match_id",
    how="left",
    validate="many_to_one"
)

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num"]
).reset_index(drop=True)

KEYS = ["match_id", "innings"]

# -----------------------------------
# 2. ESTIMATED TEAM RUNS
# -----------------------------------

extras = df["extras_type"].fillna("none")

# Scenario A: one run for wides and no-balls
extra_a = extras.isin(
    ["wide", "Overstep", "other"]
).astype(int)

# Scenario B: alternative extras assumptions
extra_b = extra_a.copy()

extra_b += extras.isin(
    ["byes", "legbyes"]
).astype(int)

extra_b += df["extras_2_runs"].fillna(0)

df["estimated_runs_a"] = (
    df["batter_runs"] + extra_a
)

df["estimated_runs_b"] = (
    df["batter_runs"] + extra_b
)

# -----------------------------------
# 3. PRE-DELIVERY MATCH STATE
# -----------------------------------

group = df.groupby(KEYS, sort=False)

df["wickets_before"] = (
    group["team_wicket"].cumsum()
    - df["team_wicket"]
)

df["legal_balls_before"] = (
    group["is_legal"].cumsum()
    - df["is_legal"]
)

df["wickets_remaining"] = (
    10 - df["wickets_before"]
).clip(lower=0)

df["balls_remaining"] = (
    120 - df["legal_balls_before"]
).clip(lower=0)

for s in ["a", "b"]:

    col = f"estimated_runs_{s}"

    df[f"score_before_{s}"] = (
        group[col].cumsum() - df[col]
    )

    df[f"current_rr_{s}"] = (
        6 * df[f"score_before_{s}"]
        / df["legal_balls_before"].replace(0, np.nan)
    )

# -----------------------------------
# 4. ESTIMATED CHASE TARGETS
# -----------------------------------

first = df[df["innings"] == 1]

targets = (
    first.groupby("match_id", as_index=False)
    .agg(
        target_a=("estimated_runs_a", "sum"),
        target_b=("estimated_runs_b", "sum")
    )
)

targets["target_a"] += 1
targets["target_b"] += 1

df = df.merge(
    targets,
    on="match_id",
    how="left",
    validate="many_to_one"
)

# Exclude revised matches from estimated chase metrics
df["revised_match"] = df[
    [
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target"
    ]
].notna().any(axis=1)

df["valid_chase"] = (
    (df["innings"] == 2)
    & (~df["revised_match"])
    & (df["balls_remaining"] > 0)
    & df["target_a"].notna()
)

for s in ["a", "b"]:

    df[f"runs_required_{s}"] = (
        df[f"target_{s}"]
        - df[f"score_before_{s}"]
    ).clip(lower=0)

    df[f"required_rr_{s}"] = (
        6 * df[f"runs_required_{s}"]
        / df["balls_remaining"].replace(0, np.nan)
    ).where(df["valid_chase"])

# -----------------------------------
# 5. PRESSURE INDICATORS
# -----------------------------------

df["wicket_pressure"] = (
    df["wickets_remaining"] <= 6
).astype(int)

df["severe_wicket_pressure"] = (
    df["wickets_remaining"] <= 4
).astype(int)

df["knockout_pressure"] = (
    df["knock_out"] == 1
).astype(int)

df["established_lineup"] = (
    (df["phase"] == "Death")
    & (df["wickets_before"] <= 3)
).astype(int)

# -----------------------------------
# 6. ROLE-SPECIFIC PRESSURE SCORES
# -----------------------------------

# -----------------------------------
# 6. ROLE-SPECIFIC PRESSURE SCORES
# -----------------------------------

for s in ["a", "b"]:

    required = df[f"required_rr_{s}"]
    current = df[f"current_rr_{s}"]

    # BATTING PRESSURE

    chase_pressure = (
        df["valid_chase"]
        & (required >= 10)
    ).astype(int)

    scoring_gap = (
        df["valid_chase"]
        & ((required - current) >= 2)
        & (df["legal_balls_before"] >= 30)
    ).astype(int)

    close_chase = (
        df["valid_chase"]
        & (df["balls_remaining"] <= 30)
        & required.between(6, 15)
    ).astype(int)

    df[f"batting_pressure_{s}"] = (
        df["wicket_pressure"]
        + df["severe_wicket_pressure"]
        + chase_pressure
        + scoring_gap
        + close_chase
        + df["knockout_pressure"]
    )

    # BOWLING PRESSURE

    aggressive_opposition = (
        (current >= 10)
        & (df["legal_balls_before"] >= 12)
    ).astype(int)

    powerplay_pressure = (
        (df["phase"] == "Powerplay")
        & (df["legal_balls_before"] >= 24)
        & (df["wickets_before"] == 0)
    ).astype(int)

    middle_pressure = (
        (df["phase"] == "Middle")
        & (df["legal_balls_before"] >= 60)
        & (df["wickets_before"] <= 2)
    ).astype(int)

    difficult_defence = (
        df["valid_chase"]
        & (required > 0)
        & (required <= 8)
        & (df["wickets_remaining"] >= 5)
    ).astype(int)

    df[f"bowling_pressure_{s}"] = (
        aggressive_opposition
        + powerplay_pressure
        + middle_pressure
        + difficult_defence
        + df["established_lineup"]
        + close_chase
        + df["knockout_pressure"]
    )



# -----------------------------------
# 7. ROBUST PRESSURE CLASSIFICATION
# -----------------------------------

for role in ["batting", "bowling"]:

    a = df[f"{role}_pressure_a"]
    b = df[f"{role}_pressure_b"]

    df[f"{role}_pressure_category"] = np.select(
        [
            (a == 0) & (b == 0),
            (a == 1) & (b == 1),
            (a >= 2) & (b >= 2)
        ],
        [
            "Normal",
            "Moderate",
            "High"
        ],
        default="Uncertain"
    )

    # Revised matches have incomplete pressure context
    df.loc[
        df["revised_match"],
        f"{role}_pressure_category"
    ] = "Uncertain"

# -----------------------------------
# 8. SAVE RESULTS
# -----------------------------------

df.to_csv(
    BASE / "match_state_pressure.csv",
    index=False
)

# -----------------------------------
# 9. VALIDATION
# -----------------------------------

print("\n=== ADVANCED PRESSURE ENGINE ===")

print("Total deliveries:", len(df))
print("Total matches:", df["match_id"].nunique())

print("\n=== BATTING PRESSURE ===")
print(df["batting_pressure_category"].value_counts())

print("\n=== BOWLING PRESSURE ===")
print(df["bowling_pressure_category"].value_counts())

print("\n=== BATTING PRESSURE BY PHASE ===")
print(
    pd.crosstab(
        df["phase"],
        df["batting_pressure_category"]
    )
)

print("\n=== BOWLING PRESSURE BY PHASE ===")
print(
    pd.crosstab(
        df["phase"],
        df["bowling_pressure_category"]
    )
)

print("\n=== MATCH CONTEXT ===")
print("Valid chase deliveries:", df["valid_chase"].sum())
print("Revised match deliveries:", df["revised_match"].sum())
print("Knockout deliveries:", df["knockout_pressure"].sum())

print("\nSaved:", BASE / "match_state_pressure.csv")
