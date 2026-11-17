
from pathlib import Path
import pandas as pd

BASE = Path("data/processed")
RAW = Path("data/raw/auction2027")
OUT = BASE / "auction2027"

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD PLAYER PERFORMANCE
# ------------------------------------

bat = pd.read_csv(
    BASE / "unified/performance/unified_batting_performance.csv"
)

bowl = pd.read_csv(
    BASE / "unified/performance/unified_bowling_performance.csv"
)

mapping = pd.read_csv(
    BASE / "unified/consolidated_identity_mapping.csv",
    dtype=str
)

registry = pd.read_csv(
    BASE / "unified/consolidated_player_registry.csv",
    dtype=str
)

# ------------------------------------
# 2. INCLUDE SMAT TALENT WATCHLISTS
# ------------------------------------

def load_smat(role, player_id, name):

    df = pd.read_csv(
        BASE / f"external/emerging_talent/smat_{role}_watchlist.csv",
        dtype={player_id: str}
    )

    df = df.merge(
        mapping[
            ["external_player_id", "unified_player_id"]
        ],
        left_on=player_id,
        right_on="external_player_id",
        how="left",
        validate="many_to_one"
    )

    df["unified_player_id"] = (
        df["unified_player_id"]
        .fillna("EXT_" + df[player_id])
    )

    return df.rename(columns={
        name: "player_name"
    })

smat_bat = load_smat(
    "batting", "striker_id", "striker_name"
)

smat_bowl = load_smat(
    "bowling", "bowler_id", "bowler_name"
)

# ------------------------------------
# 3. CREATE COMPLETE SCOUTING POOL
# ------------------------------------

columns = ["unified_player_id", "player_name"]

players = pd.concat([
    bat[columns],
    bowl[columns],
    smat_bat[columns],
    smat_bowl[columns]
], ignore_index=True)

players = players.drop_duplicates(
    "unified_player_id"
).copy()

canonical_names = registry.set_index(
    "unified_player_id"
)["player_name"]

players["player_name"] = (
    players["unified_player_id"]
    .map(canonical_names)
    .fillna(players["player_name"])
)

# ------------------------------------
# 4. LOAD ELIGIBILITY INFORMATION
# ------------------------------------

eligibility = pd.read_csv(
    RAW / "player_eligibility.csv",
    dtype=str
)

players = players.merge(
    eligibility.drop(columns=["player_name"]),
    on="unified_player_id",
    how="left",
    validate="one_to_one"
)

# ------------------------------------
# 5. LOAD RETENTION INFORMATION
# ------------------------------------

retention = pd.read_csv(
    RAW / "retention_list.csv",
    dtype=str
)

def normalize(name):
    return " ".join(str(name).lower().split())

players["name_key"] = (
    players["player_name"].apply(normalize)
)

retention["name_key"] = (
    retention["player_name"].apply(normalize)
)

# Do not automatically join ambiguous names

retention = retention[
    ~retention["name_key"].duplicated(keep=False)
].copy()

retention = retention.rename(columns={
    "source": "retention_source",
    "status": "retention_status"
})

players = players.merge(
    retention[[
        "name_key",
        "franchise",
        "retention_status",
        "retention_source"
    ]],
    on="name_key",
    how="left",
    validate="many_to_one"
)

# ------------------------------------
# 6. ELIGIBILITY FILTER
# ------------------------------------

def classify(row):

    eligibility = normalize(row["ipl_eligibility"])
    retired = normalize(row["retirement_status"])
    registered = normalize(row["auction_registered"])

    retention = normalize(row["retention_status"])
    franchise = normalize(row["franchise"])

    eligibility_verified = (
        pd.notna(row["source"])
        and bool(str(row["source"]).strip())
    )

    retention_verified = (
        pd.notna(row["retention_source"])
        and bool(str(row["retention_source"]).strip())
    )

    if eligibility_verified:

        if eligibility == "ineligible":
            return "Excluded - IPL ineligible"

        if retired == "retired":
            return "Excluded - Retired"

    if retention_verified:

        if retention in ["retained", "traded"]:

            if franchise in ["rajasthan royals", "rr"]:
                return "Existing RR squad"

            return "Excluded - Contracted"

    if eligibility_verified and eligibility == "eligible":

        if retention_verified and retention == "released":

            if registered == "yes":
                return "Confirmed auction candidate"

            return "Potential auction candidate"

    return "Needs verification"

players["recruitment_status"] = players.apply(
    classify,
    axis=1
)

# ------------------------------------
# 7. SAVE RESULTS
# ------------------------------------

players.to_csv(
    OUT / "complete_scouting_registry.csv",
    index=False
)

excluded = players[
    players["recruitment_status"].str.startswith(
        "Excluded"
    )
]

excluded.to_csv(
    OUT / "excluded_players.csv",
    index=False
)

potential = players[
    players["recruitment_status"].isin([
        "Potential auction candidate",
        "Confirmed auction candidate"
    ])
]

potential.to_csv(
    OUT / "auction_candidates.csv",
    index=False
)

pending = players[
    players["recruitment_status"] ==
    "Needs verification"
]

pending.to_csv(
    OUT / "verification_pending.csv",
    index=False
)

# ------------------------------------
# 8. DISPLAY RESULTS
# ------------------------------------

print("\n=== COMPLETE SCOUTING POOL ===")
print("Unique players:", len(players))

print("\n=== RECRUITMENT STATUS ===")
print(players["recruitment_status"].value_counts())

print("\nExcluded players:", len(excluded))
print("Auction prospects:", len(potential))
print("Pending verification:", len(pending))

print("\nSaved results to:", OUT)
