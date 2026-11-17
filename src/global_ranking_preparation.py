
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/auction2027")
OUT = BASE / "global_rankings"

OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "whi/rri_ranked_evidence.csv",
    low_memory=False
)

# ----------------------------------
# 1. ADDITIONAL ELIGIBILITY REVIEW
# ----------------------------------

eligibility_review = [
    "Mohammad Amir",
    "Usama Mir"
]

retirement_review = [
    "Piyush Chawla",
    "KA Pollard",
    "Kieron Pollard"
]

review = df[
    df["canonical_name"].isin(
        eligibility_review + retirement_review
    )
].copy()

review.to_csv(
    OUT / "additional_eligibility_review.csv",
    index=False
)

df = df[
    ~df["canonical_name"].isin(
        eligibility_review + retirement_review
    )
].copy()

# ----------------------------------
# 2. WEIGHT SENSITIVITY
# ----------------------------------

score_columns = [
    "rri",
    "rri_whi60",
    "rri_pri60"
]

df["robust_rri"] = df[score_columns].mean(axis=1)

df["rri_min"] = df[score_columns].min(axis=1)

df["rri_max"] = df[score_columns].max(axis=1)

df["weight_sensitivity"] = (
    df["rri_max"] - df["rri_min"]
)

# ----------------------------------
# 3. SEPARATE BASELINE TYPES
# ----------------------------------

normal = df[
    df["baseline_category"] == "Normal"
].copy()

moderate = df[
    df["baseline_category"] == "Moderate"
].copy()

# ----------------------------------
# 4. CREATE PRIORITISED WATCHLISTS
# ----------------------------------

roles = {
    "Death Bowler": 20,
    "Middle Order Batter": 20,
    "Finisher": 20,
    "Powerplay Bowler": 15,
    "Middle Over Bowler": 15,
    "Backup Opener": 10
}

for baseline, data in [
    ("normal", normal),
    ("moderate", moderate)
]:

    for role, limit in roles.items():

        candidates = data[
            data["target_role"] == role
        ].copy()

        # Exclude known spinners from pace requirements.
        # Unknown styles remain under review.

        if role in [
            "Death Bowler",
            "Powerplay Bowler"
        ]:

            candidates = candidates[
                candidates["style"] != "Spin"
            ]

        candidates = candidates.sort_values(
            ["robust_rri", "balls_pressure"],
            ascending=[False, False]
        )

        candidates = candidates.drop_duplicates(
            "name_key"
        )

        top = candidates.head(limit).copy()

        top.insert(
            0, "screening_rank",
            range(1, len(top) + 1)
        )

        top["ranking_status"] = (
            "Provisional cross-league screening"
        )

        filename = role.lower().replace(" ", "_")

        top.to_csv(
            OUT / f"{baseline}_{filename}.csv",
            index=False
        )

        print(f"\n=== {baseline.upper()} | {role.upper()} ===")

        print(top[[
            "screening_rank",
            "canonical_name",
            "competition",
            "balls_pressure",
            "pri",
            "whi",
            "robust_rri",
            "style"
        ]].round(2).to_string(index=False))

# ----------------------------------
# 5. BOWLING STYLE REVIEW QUEUE
# ----------------------------------

style_review = df[
    (df["skill"] == "Bowling")
    & df["style"].isin(["Unknown", "Mixed"])
].copy()

style_review = style_review.sort_values(
    ["rr_role_priority", "robust_rri"],
    ascending=[False, False]
)

style_review = style_review.drop_duplicates(
    "name_key"
)

style_review[[
    "unified_player_id",
    "canonical_name",
    "competition",
    "target_role",
    "pri",
    "whi",
    "robust_rri",
    "qc_status"
]].to_csv(
    OUT / "prioritised_bowling_style_review.csv",
    index=False
)

# ----------------------------------
# 6. DOMESTIC TALENT PRESERVATION
# ----------------------------------

for skill in ["batting", "bowling"]:

    domestic = pd.read_csv(
        BASE / "global_scouting"
        / f"domestic_{skill}_watchlist.csv"
    )

    domestic.to_csv(
        OUT / f"domestic_{skill}_prospects.csv",
        index=False
    )

# ----------------------------------
# 7. SAVE MASTER DATA
# ----------------------------------

df.to_csv(
    OUT / "global_rri_master.csv",
    index=False
)

print("\n=== GLOBAL RANKING SUMMARY ===")

print("Unique prospects:", df["name_key"].nunique())

print("Normal baseline prospects:",
      normal["name_key"].nunique())

print("Moderate baseline prospects:",
      moderate["name_key"].nunique())

print("Bowlers requiring style review:",
      style_review["name_key"].nunique())

print("\nSaved results to:", OUT)
