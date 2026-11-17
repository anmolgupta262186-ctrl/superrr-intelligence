
from pathlib import Path
import pandas as pd
import re
import unicodedata

BASE = Path("data/processed/auction2027")
GLOBAL = BASE / "global_scouting"
OUT = BASE / "quality_control"

OUT.mkdir(parents=True, exist_ok=True)

players = pd.read_csv(
    GLOBAL / "global_scouting_master.csv"
)

retention = pd.read_csv(
    "data/raw/auction2027/retention_list.csv"
)

# ------------------------------------
# 1. NORMALISE PLAYER NAMES
# ------------------------------------

def normalize(name):

    name = unicodedata.normalize(
        "NFKD", str(name)
    )

    name = name.encode(
        "ascii", "ignore"
    ).decode("ascii").lower()

    return re.sub(r"[^a-z0-9]", "", name)


aliases = {
    "Lokesh Rahul": "KL Rahul",
    "R Shepherd": "Romario Shepherd",
    "N Burger": "Nandre Burger",
    "KH Pandya": "Krunal Pandya",
    "R Powell": "Rovman Powell",
    "J Overton": "Jamie Overton",
    "Nitish Reddy": "Nitish Kumar Reddy",
    "DA Payne": "David Payne",
    "SO Hetmyer": "Shimron Hetmyer",
    "MJ Owen": "Mitch Owen",
    "MW Short": "Matthew Short",
    "M Markande": "Mayank Markande",
    "M Theekshana": "Maheesh Theekshana",
    "M Shahrukh Khan": "Shahrukh Khan",
    "K Kartikeya": "Kumar Kartikeya",
    "Kumar Kartikeya Singh": "Kumar Kartikeya",
    "FazalHaq Farooqi": "Fazalhaq Farooqi",
}

alias_lookup = {
    normalize(k): v
    for k, v in aliases.items()
}

players["canonical_name"] = players[
    "player_name"
].apply(
    lambda x: alias_lookup.get(normalize(x), x)
)

players["name_key"] = players[
    "canonical_name"
].apply(normalize)

retention["name_key"] = retention[
    "player_name"
].apply(normalize)

# ------------------------------------
# 2. CHECK CONTRACTED PLAYERS
# ------------------------------------

contracted = set(
    retention[
        retention["status"].isin(
            ["Retained", "Traded"]
        )
    ]["name_key"]
)

released = set(
    retention[
        retention["status"] == "Released"
    ]["name_key"]
)

unavailable = set(
    retention[
        retention["status"].isin(
            ["Withdrawn", "Retired"]
        )
    ]["name_key"]
)

# ------------------------------------
# 3. ADDITIONAL MANUAL REVIEW
# ------------------------------------

retirement_review = {
    normalize(x) for x in [
        "Ambati Rayudu",
        "Dinesh Karthik",
        "Ravichandran Ashwin",
        "Dwayne Bravo",
        "Andre Russell",
        "Mohit Sharma",
        "Matthew Wade",
        "Tim Southee",
        "S Kaul",
        "N Wagner",
        "TD Astle"
    ]
}

eligibility_review = {
    normalize(x) for x in [
        "Imad Wasim",
        "Usman Tariq",
        "Zafar Gohar",
        "Hassan Khan",
        "Haider Ali",
        "Imran Tahir"
    ]
}

# ------------------------------------
# 4. QUALITY CONTROL
# ------------------------------------

def classify(row):

    key = row["name_key"]

    if key in contracted:
        return "Excluded - Contracted"

    if key in unavailable:
        return "Excluded - Unavailable"

    if key in retirement_review:
        return "Hold - Retirement verification"

    if key in eligibility_review:
        return "Hold - IPL eligibility verification"

    if key in released:
        return "Potential released target"

    return "Unverified global prospect"


players["qc_status"] = players.apply(
    classify, axis=1
)

# ------------------------------------
# 5. HANDLE DUPLICATE IDENTITIES
# ------------------------------------

identity_conflicts = (
    players.groupby("name_key")
    ["unified_player_id"]
    .nunique()
)

conflict_keys = set(
    identity_conflicts[
        identity_conflicts > 1
    ].index
)

players["identity_review"] = players[
    "name_key"
].isin(conflict_keys)

players.loc[
    players["identity_review"]
    & ~players["qc_status"].str.startswith("Excluded"),
    "qc_status"
] = "Hold - Duplicate identity review"

# ------------------------------------
# 6. SEPARATE RESULTS
# ------------------------------------

excluded = players[
    players["qc_status"].str.startswith("Excluded")
]

held = players[
    players["qc_status"].str.startswith("Hold")
]

clean = players[
    ~players["qc_status"].str.startswith(
        ("Excluded", "Hold")
    )
].copy()

# ------------------------------------
# 7. SAVE DATA
# ------------------------------------

for filename, data in [
    ("qc_master", players),
    ("qc_excluded", excluded),
    ("qc_pending_review", held),
    ("qc_scouting_pool", clean)
]:

    data.to_csv(
        OUT / f"{filename}.csv",
        index=False
    )

# ------------------------------------
# 8. DISPLAY RESULTS
# ------------------------------------

print("\n=== SCOUTING QUALITY CONTROL ===")

print(
    players[
        ["canonical_name", "qc_status"]
    ]
    .drop_duplicates()
    ["qc_status"]
    .value_counts()
)

print("\n=== EXCLUDED PLAYERS ===")

print(
    excluded[
        ["canonical_name", "qc_status"]
    ]
    .drop_duplicates()
    .to_string(index=False)
)

print("\n=== PLAYERS ON HOLD ===")

print(
    held[
        ["canonical_name", "qc_status"]
    ]
    .drop_duplicates()
    .to_string(index=False)
)

print("\n=== FINAL SCOUTING COVERAGE ===")

print(
    clean.groupby("target_role")
    ["name_key"]
    .nunique()
)

print(
    "\nRemaining unique prospects:",
    clean["name_key"].nunique()
)

print("\nSaved results to:", OUT)
