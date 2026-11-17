
from pathlib import Path
from collections import defaultdict
import pandas as pd
import unicodedata
import re

RAW = Path("data/raw")
OUT = Path("data/processed/unified")

# ------------------------------------
# 1. LOAD DATA
# ------------------------------------

people = pd.read_csv(
    RAW / "register/people.csv",
    dtype=str
)

names = pd.read_csv(
    RAW / "register/names.csv",
    dtype=str
)

official = pd.read_csv(
    RAW / "rr_official/competition_team_player_mapping.csv",
    dtype={"player_id": str}
)

mapping = pd.read_csv(
    OUT / "player_identity_mapping.csv",
    dtype=str
)

# ------------------------------------
# 2. NORMALISE NAMES
# ------------------------------------

def normalize(name):

    name = unicodedata.normalize("NFKD", str(name))

    name = name.encode(
        "ascii", "ignore"
    ).decode("ascii").lower()

    name = re.sub(r"[^a-z0-9\s]", "", name)

    return " ".join(name.split())

# ------------------------------------
# 3. BUILD ALIAS REGISTRY
# ------------------------------------

aliases = pd.concat([
    people[["identifier", "name"]],

    people[
        ["identifier", "unique_name"]
    ].rename(columns={"unique_name": "name"}),

    names[["identifier", "name"]]

], ignore_index=True).dropna().drop_duplicates()

aliases["normalized"] = aliases["name"].apply(
    normalize
)

alias_index = defaultdict(set)

for row in aliases.itertuples(index=False):

    alias_index[row.normalized].add(
        row.identifier
    )

official_names = (
    official[["player_id", "player_name"]]
    .dropna()
    .drop_duplicates()
)

official_lookup = defaultdict(set)

# ------------------------------------
# 4. MATCH OFFICIAL PLAYERS
# ------------------------------------

for row in official_names.itertuples(index=False):

    normalized = normalize(row.player_name)

    candidates = alias_index.get(
        normalized, set()
    )

    if len(candidates) == 1:

        cricsheet_id = next(iter(candidates))

        official_lookup[cricsheet_id].add(
            row.player_id
        )

# ------------------------------------
# 5. IMPROVE EXISTING MAPPING
# ------------------------------------

official_name_lookup = (
    official_names.drop_duplicates("player_id")
    .set_index("player_id")["player_name"]
    .to_dict()
)

improved = []

for row in mapping.itertuples(index=False):

    external_id = row.external_player_id

    candidates = official_lookup.get(
        external_id, set()
    )

    if len(candidates) != 1:
        continue

    official_id = next(iter(candidates))

    if row.mapping_status == "Manually verified":
        continue

    if pd.notna(row.official_player_id):

        if row.official_player_id == official_id:
            status = "Existing match supported"
        else:
            status = "Conflicting identity - review"

    else:
        status = "Register alias match - review"

    improved.append({
        "external_player_id": external_id,
        "external_player_name": row.external_player_name,
        "official_player_id": official_id,
        "official_player_name": official_name_lookup.get(
            official_id
        ),
        "previous_status": row.mapping_status,
        "new_status": status,
        "source": "https://cricsheet.org/register/"
    })

results = pd.DataFrame(
    improved,
    columns=[
        "external_player_id",
        "external_player_name",
        "official_player_id",
        "official_player_name",
        "previous_status",
        "new_status",
        "source"
    ]
)

# ------------------------------------
# 6. VALIDATION
# ------------------------------------

results.to_csv(
    OUT / "register_identity_matches.csv",
    index=False
)

print("\n=== IMPROVED IDENTITY MAPPING ===")

print("Cricsheet people:", len(people))
print("Name aliases:", len(aliases))
print("Register-supported matches:", len(results))

print("\n=== MATCH STATUS ===")

print(results["new_status"].value_counts())

new_matches = results[
    results["new_status"] ==
    "Register alias match - review"
]

print("\n=== NEW POTENTIAL MATCHES ===")

print(
    new_matches[[
        "external_player_name",
        "official_player_name"
    ]].head(40).to_string(index=False)
)

print("\nSaved to:", OUT)
