
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/domestic/smat")

df = pd.read_csv(
    BASE / "smat_clean_deliveries.csv",
    low_memory=False
)

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num"]
).reset_index(drop=True)

KEYS = ["match_id", "innings"]

group = df.groupby(KEYS, sort=False)

# ------------------------------------
# 1. PRE-DELIVERY MATCH STATE
# ------------------------------------

df["score_before"] = (
    group["total_runs"].cumsum()
    - df["total_runs"]
)

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

df["current_rr"] = (
    6 * df["score_before"]
    / df["legal_balls_before"].replace(0, np.nan)
)

# ------------------------------------
# 2. CHASE TARGET
# ------------------------------------

first_innings = (
    df[df["innings"] == 1]
    .groupby("match_id")["total_runs"]
    .sum()
    .add(1)
    .rename("calculated_target")
    .reset_index()
)

df = df.merge(
    first_innings,
    on="match_id",
    how="left",
    validate="many_to_one"
)

# Prefer the recorded target where available

df["target"] = (
    df["target_runs"]
    .fillna(df["calculated_target"])
)

# ------------------------------------
# 3. DATA QUALITY FLAGS
# ------------------------------------

innings_balls = (
    df.groupby(KEYS)["is_legal"]
    .transform("sum")
)

df["unusual_innings"] = innings_balls > 120

# Compare recorded and reconstructed targets

df["target_mismatch"] = (
    (df["innings"] == 2)
    & df["target_runs"].notna()
    & df["calculated_target"].notna()
    & (df["target_runs"] != df["calculated_target"])
    & (~df["revised_match"])
)

df["uncertain_match"] = (
    df["revised_match"]
    | df["unusual_innings"]
    | df["target_mismatch"]
    | (df["balls_per_over"] != 6)
)

df["uncertain_match"] = (
    df.groupby("match_id")["uncertain_match"]
    .transform("max")
)

# ------------------------------------
# 4. REQUIRED RUN RATE
# ------------------------------------

df["runs_required"] = (
    df["target"] - df["score_before"]
).where(df["innings"] == 2)

df["valid_chase"] = (
    (df["innings"] == 2)
    & (~df["uncertain_match"])
    & (df["balls_remaining"] > 0)
    & (df["runs_required"] > 0)
    & df["target"].notna()
)

df["required_rr"] = (
    6 * df["runs_required"]
    / df["balls_remaining"].replace(0, np.nan)
).where(df["valid_chase"])

df["rr_gap"] = (
    df["required_rr"] - df["current_rr"]
)

# ------------------------------------
# 5. BATTING PRESSURE
# ------------------------------------

df["wicket_pressure"] = (
    df["wickets_remaining"] <= 6
).astype(int)

df["severe_wicket_pressure"] = (
    df["wickets_remaining"] <= 4
).astype(int)

df["chase_pressure"] = (
    df["valid_chase"]
    & (df["required_rr"] >= 10)
).astype(int)

df["scoring_gap"] = (
    df["valid_chase"]
    & (df["rr_gap"] >= 2)
    & (df["legal_balls_before"] >= 30)
).astype(int)

df["close_chase"] = (
    df["valid_chase"]
    & (df["balls_remaining"] <= 30)
    & df["required_rr"].between(6, 15)
).astype(int)

df["knockout_pressure"] = (
    df["knock_out"] == 1
).astype(int)

df["batting_pressure_score"] = (
    df["wicket_pressure"]
    + df["severe_wicket_pressure"]
    + df["chase_pressure"]
    + df["scoring_gap"]
    + df["close_chase"]
    + df["knockout_pressure"]
)

# ------------------------------------
# 6. BOWLING PRESSURE
# ------------------------------------

df["aggressive_opposition"] = (
    (df["current_rr"] >= 10)
    & (df["legal_balls_before"] >= 12)
).astype(int)

df["powerplay_pressure"] = (
    (df["phase"] == "Powerplay")
    & (df["legal_balls_before"] >= 24)
    & (df["wickets_before"] == 0)
).astype(int)

df["middle_pressure"] = (
    (df["phase"] == "Middle")
    & (df["legal_balls_before"] >= 60)
    & (df["wickets_before"] <= 2)
).astype(int)

df["difficult_defence"] = (
    df["valid_chase"]
    & (df["required_rr"] <= 8)
    & (df["wickets_remaining"] >= 5)
).astype(int)

df["established_lineup"] = (
    (df["phase"] == "Death")
    & (df["wickets_before"] <= 3)
).astype(int)

df["bowling_pressure_score"] = (
    df["aggressive_opposition"]
    + df["powerplay_pressure"]
    + df["middle_pressure"]
    + df["difficult_defence"]
    + df["established_lineup"]
    + df["close_chase"]
    + df["knockout_pressure"]
)

# ------------------------------------
# 7. PRESSURE CLASSIFICATION
# ------------------------------------

for role in ["batting", "bowling"]:

    score = df[f"{role}_pressure_score"]

    df[f"{role}_pressure_category"] = np.select(
        [
            score == 0,
            score == 1,
            score >= 2
        ],
        [
            "Normal",
            "Moderate",
            "High"
        ],
        default="Uncertain"
    )

    df.loc[
        df["uncertain_match"],
        f"{role}_pressure_category"
    ] = "Uncertain"

# ------------------------------------
# 8. SAVE DATA
# ------------------------------------

df.to_csv(
    BASE / "smat_pressure_deliveries.csv",
    index=False
)

# ------------------------------------
# 9. VALIDATION
# ------------------------------------

print("\n=== EXTERNAL PRESSURE ENGINE ===")

print("Total deliveries:", len(df))
print("Total matches:", df["match_id"].nunique())

print("\n=== BATTING PRESSURE ===")
print(df["batting_pressure_category"].value_counts())

print("\n=== BOWLING PRESSURE ===")
print(df["bowling_pressure_category"].value_counts())

print("\n=== BATTING PRESSURE BY PHASE ===")
print(pd.crosstab(
    df["phase"],
    df["batting_pressure_category"]
))

print("\n=== BOWLING PRESSURE BY PHASE ===")
print(pd.crosstab(
    df["phase"],
    df["bowling_pressure_category"]
))

print("\n=== BATTING PRESSURE BY LEAGUE ===")
print(pd.crosstab(
    df["league"],
    df["batting_pressure_category"]
))

print("\n=== BOWLING PRESSURE BY LEAGUE ===")
print(pd.crosstab(
    df["league"],
    df["bowling_pressure_category"]
))

print("\n=== BATTING PRESSURE BY ROLE ===")
print(pd.crosstab(
    df["batting_role"],
    df["batting_pressure_category"]
))

print("\n=== DATA QUALITY ===")

print("Valid chase deliveries:", df["valid_chase"].sum())

print(
    "Uncertain matches:",
    df.loc[df["uncertain_match"], "match_id"].nunique()
)

print(
    "Target mismatch matches:",
    df.loc[df["target_mismatch"], "match_id"].nunique()
)

print(
    "Unusual innings matches:",
    df.loc[df["unusual_innings"], "match_id"].nunique()
)

print("\nSaved:", BASE / "smat_pressure_deliveries.csv")
