
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/rr_official")
BASE = Path("data/processed/official")
FINAL = BASE / "final"
OUT = BASE / "scouting"

# -----------------------------------
# 1. LOAD DATA
# -----------------------------------

bat = pd.read_csv(
    FINAL / "final_batting_rankings.csv"
)

bowl = pd.read_csv(
    FINAL / "final_bowling_rankings.csv"
)

review = pd.read_csv(
    OUT / "eligibility_review_2027.csv"
)

mapping = pd.read_csv(
    RAW / "competition_team_player_mapping.csv"
)

# -----------------------------------
# 2. UPDATED PLAYER REGISTRY
# -----------------------------------

batters = bat[
    ["striker_id", "striker_name"]
].rename(columns={
    "striker_id": "player_id",
    "striker_name": "player_name"
})

bowlers = bowl[
    ["bowler_id", "bowler_name"]
].rename(columns={
    "bowler_id": "player_id",
    "bowler_name": "player_name"
})

players = pd.concat(
    [batters, bowlers],
    ignore_index=True
).drop_duplicates("player_id")

# Map IPL 2026 franchises

ipl = mapping[mapping["comp_id"] == 3298]

squads = (
    ipl.groupby("player_id")["team_name"]
    .agg(lambda x: ", ".join(sorted(set(x.dropna()))))
    .reset_index(name="ipl_2026_teams")
)

players = players.merge(
    squads,
    on="player_id",
    how="left",
    validate="one_to_one"
)

def squad_status(team):
    if pd.isna(team):
        return "No 2026 squad record"

    if "Rajasthan Royals" in team.split(", "):
        return "RR squad 2026"

    return "Other IPL franchise 2026"

players["squad_status_2026"] = (
    players["ipl_2026_teams"].apply(squad_status)
)

# -----------------------------------
# 3. PRESERVE ELIGIBILITY REVIEWS
# -----------------------------------

review_columns = [
    "player_id",
    "nationality",
    "age",
    "capped_status",
    "ipl_eligibility",
    "retention_status_2027",
    "auction_registered_2027",
    "availability_status",
    "verification_source",
    "verification_date",
    "recruitment_status"
]

players = players.merge(
    review[review_columns],
    on="player_id",
    how="left",
    validate="one_to_one"
)

for col in [
    "nationality",
    "capped_status",
    "ipl_eligibility",
    "retention_status_2027",
    "auction_registered_2027",
    "availability_status"
]:
    players[col] = players[col].fillna("Unverified")

players["recruitment_status"] = (
    players["recruitment_status"]
    .fillna("Needs verification")
)

# -----------------------------------
# 4. RECRUITMENT ELIGIBILITY
# -----------------------------------

def recruitment_decision(row):

    eligibility = str(
        row["ipl_eligibility"]
    ).strip().lower()

    retention = str(
        row["retention_status_2027"]
    ).strip().lower()

    availability = str(
        row["availability_status"]
    ).strip().lower()

    registered = str(
        row["auction_registered_2027"]
    ).strip().lower()

    verified = (
        pd.notna(row["verification_source"])
        and bool(str(row["verification_source"]).strip())
        and pd.notna(row["verification_date"])
        and bool(str(row["verification_date"]).strip())
    )

    if verified:
        if eligibility == "ineligible":
            return "Excluded - Ineligible"

        if retention == "retained":
            return "Excluded - Retained"

        if (
            eligibility == "eligible"
            and availability == "available"
            and registered == "yes"
        ):
            return "Confirmed auction candidate"

    if row["squad_status_2026"] == "RR squad 2026":
        return "Review RR retention status"

    return "Needs verification"

players["recruitment_status"] = players.apply(
    recruitment_decision,
    axis=1
)

players.to_csv(
    OUT / "updated_player_registry_2027.csv",
    index=False
)

# -----------------------------------
# 5. RR PHASE REQUIREMENTS
# -----------------------------------

BATTING_FIT = {
    "Powerplay": 40,
    "Middle": 100,
    "Death": 90
}

BOWLING_FIT = {
    "Powerplay": 100,
    "Middle": 60,
    "Death": 100
}

# -----------------------------------
# 6. GENERATE RECRUITMENT SCORES
# -----------------------------------

def shortlist(data, role, player_id, name, fit):

    data = data.merge(
        players.drop(columns="player_name"),
        left_on=player_id,
        right_on="player_id",
        how="left",
        validate="one_to_one"
    )

    data["rr_phase_fit"] = data["phase"].map(fit)

    data["recruitment_score"] = (
        0.80 * data["mean_pri"]
        + 0.20 * data["rr_phase_fit"]
    )

    data = data.sort_values(
        "recruitment_score",
        ascending=False
    )

    data.to_csv(
        OUT / f"rr_{role}_recruitment_all.csv",
        index=False
    )

    confirmed = data[
        data["recruitment_status"]
        == "Confirmed auction candidate"
    ]

    confirmed.to_csv(
        OUT / f"rr_{role}_confirmed_candidates.csv",
        index=False
    )

    watchlist = data[
        data["recruitment_status"]
        == "Needs verification"
    ]

    watchlist.to_csv(
        OUT / f"rr_{role}_verification_watchlist.csv",
        index=False
    )

    print(f"\n=== RR {role.upper()} RECRUITMENT ===")

    print("Total players:", len(data))
    print("Confirmed candidates:", len(confirmed))

    print("\nRecruitment status:")
    print(data["recruitment_status"].value_counts())

    print("\n=== TOP 20 PLAYERS TO VERIFY ===")

    columns = [
        name,
        "phase",
        "mean_pri",
        "rr_phase_fit",
        "recruitment_score",
        "squad_status_2026"
    ]

    print(
        watchlist[columns]
        .head(20)
        .round(2)
        .to_string(index=False)
    )

# -----------------------------------
# 7. EXECUTE
# -----------------------------------

shortlist(
    bat,
    "batting",
    "striker_id",
    "striker_name",
    BATTING_FIT
)

shortlist(
    bowl,
    "bowling",
    "bowler_id",
    "bowler_name",
    BOWLING_FIT
)

print("\nUnique players in registry:", len(players))
print("Results saved to:", OUT)
