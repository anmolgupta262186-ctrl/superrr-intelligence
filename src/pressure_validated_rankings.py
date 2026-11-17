
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/auction2027")
OUT = BASE / "pressure_validated"

OUT.mkdir(parents=True, exist_ok=True)

# 1. Load pressure audit and screened pool

df = pd.read_csv(
    BASE / "pressure_audit/complete_pressure_audit.csv",
    low_memory=False
)

screened = pd.read_csv(
    BASE / "global_rankings/global_rri_master.csv",
    low_memory=False
)

df = df[
    df["name_key"].isin(screened["name_key"])
].copy()

df = df[df["rri"].notna()].copy()

# 2. Check minimum evidence

df = df[
    df["audit_evidence_strength"].isin([
        "Strong", "Moderate"
    ])
].copy()

# 3. Classify pressure evidence

def classify(row):

    if row["pressure_audit_status"] == (
        "Strong positive pressure signal"
    ):
        return "Tier A - Positive pressure evidence"

    if row["pressure_audit_status"] == (
        "Pressure decline - review"
    ):
        return "Tier C - Pressure decline"

    return "Tier B - Mixed pressure evidence"

df["pressure_tier"] = df.apply(
    classify, axis=1
)

# 4. Preserve our original recruitment formula

df["final_rri"] = (
    0.50 * df["pri"]
    + 0.50 * df["whi"]
)

# 5. Recruitment roles

roles = {
    "Death Bowler": 10,
    "Middle Order Batter": 10,
    "Finisher": 10,
    "Powerplay Bowler": 10,
    "Middle Over Bowler": 10,
    "Backup Opener": 5
}

shortlists = []

for baseline in ["Normal", "Moderate"]:

    for role, limit in roles.items():

        candidates = df[
            (df["target_role"] == role)
            & (df["baseline_category"] == baseline)
        ].copy()

        # Pace bowling requirement

        if role in [
            "Death Bowler", "Powerplay Bowler"
        ]:

            candidates = candidates[
                candidates["style"] != "Spin"
            ]

        # Prioritise positive pressure evidence

        candidates = candidates.sort_values(
            ["pressure_tier", "final_rri",
             "balls_pressure"],
            ascending=[True, False, False]
        )

        candidates = candidates.drop_duplicates(
            "name_key"
        )

        top = candidates.head(limit).copy()

        top.insert(
            0, "rank", range(1, len(top) + 1)
        )

        shortlists.append(top)

        filename = role.lower().replace(" ", "_")

        top.to_csv(
            OUT / f"{baseline.lower()}_{filename}.csv",
            index=False
        )

        print(f"\n=== {baseline.upper()} | {role.upper()} ===")

        print(top[[
            "rank",
            "canonical_name",
            "competition",
            "pri",
            "whi",
            "final_rri",
            "pressure_tier",
            "style"
        ]].round(2).to_string(index=False))

# 6. Save all evaluated evidence

df.to_csv(
    OUT / "pressure_validated_master.csv",
    index=False
)

final = pd.concat(
    shortlists, ignore_index=True
)

final.to_csv(
    OUT / "pressure_validated_shortlists.csv",
    index=False
)

# 7. Preserve Indian domestic talent

for skill in ["batting", "bowling"]:

    domestic = pd.read_csv(
        BASE / "pressure_audit"
        / f"domestic_{skill}_pressure_review.csv"
    )

    domestic.to_csv(
        OUT / f"domestic_{skill}_watchlist.csv",
        index=False
    )

# 8. Final summary

print("\n=== FINAL PRESSURE SUMMARY ===")

print("Unique evaluated candidates:",
      df["name_key"].nunique())

print("Unique shortlisted candidates:",
      final["name_key"].nunique())

print("\n=== PRESSURE TIERS ===")

print(
    df.groupby("pressure_tier")
    ["name_key"].nunique()
)

print("\nSaved results to:", OUT)
