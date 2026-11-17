
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/official/scouting")

players = pd.read_csv(
    BASE / "player_availability_2027.csv"
)

# Avoid overwriting completed manual reviews
OUTPUT = BASE / "eligibility_review_2027.csv"

if OUTPUT.exists():
    raise SystemExit(
        "Review file already exists. "
        "Preserving existing verification work."
    )

review = players[
    [
        "player_id",
        "player_name",
        "ipl_2026_teams",
        "squad_status_2026"
    ]
].copy()

review["nationality"] = "Unverified"
review["age"] = pd.NA
review["capped_status"] = "Unverified"

review["ipl_eligibility"] = "Unverified"
review["retention_status_2027"] = "Unverified"
review["auction_registered_2027"] = "Unverified"

review["availability_status"] = "Unverified"
review["verification_source"] = ""
review["verification_date"] = ""

# Only confirmed, eligible auction candidates qualify
review["recruitment_status"] = "Needs verification"

review.to_csv(OUTPUT, index=False)

print("\n=== ELIGIBILITY REVIEW CREATED ===")

print("Total players:", len(review))

print("\n2026 squad classifications:")
print(review["squad_status_2026"].value_counts())

print("\n2027 eligibility:")
print(review["recruitment_status"].value_counts())

print("\nSaved:", OUTPUT)
