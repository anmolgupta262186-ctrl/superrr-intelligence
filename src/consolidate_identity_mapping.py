
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/unified")

mapping = pd.read_csv(
    BASE / "player_identity_mapping.csv",
    dtype=str
)

register = pd.read_csv(
    BASE / "register_identity_matches.csv",
    dtype=str
)

official = pd.read_csv(
    "data/raw/rr_official/competition_team_player_mapping.csv",
    dtype=str
)

# ------------------------------------
# 1. REGISTER-SUPPORTED MATCHES
# ------------------------------------

supported = register[
    register["new_status"].isin([
        "Register alias match - review",
        "Existing match supported"
    ])
].copy()

# Remove ambiguous register mappings

supported = supported[
    ~supported["external_player_id"].duplicated(keep=False)
    & ~supported["official_player_id"].duplicated(keep=False)
]

lookup = supported.set_index(
    "external_player_id"
).to_dict("index")

# ------------------------------------
# 2. UPDATE PLAYER IDENTITIES
# ------------------------------------

for index, row in mapping.iterrows():

    if row["mapping_status"] == "Manually verified":
        continue

    ext_id = row["external_player_id"]

    if ext_id not in lookup:
        continue

    match = lookup[ext_id]

    official_id = match["official_player_id"]

    mapping.loc[index, "official_player_id"] = official_id

    mapping.loc[index, "official_player_name"] = (
        match["official_player_name"]
    )

    mapping.loc[index, "unified_player_id"] = (
        f"RR_{official_id}"
    )

    mapping.loc[index, "mapping_status"] = (
        "Register supported - provisional"
    )

# ------------------------------------
# 3. CHECK IDENTITY CONFLICTS
# ------------------------------------

matched = mapping[
    mapping["official_player_id"].notna()
]

conflicts = matched[
    matched["official_player_id"].duplicated(keep=False)
]

for index, row in conflicts.iterrows():

    mapping.loc[index, "official_player_id"] = None
    mapping.loc[index, "official_player_name"] = None

    mapping.loc[index, "unified_player_id"] = (
        "EXT_" + row["external_player_id"]
    )

    mapping.loc[index, "mapping_status"] = (
        "Conflicting mapping - review"
    )

# ------------------------------------
# 4. CREATE UPDATED REGISTRY
# ------------------------------------

official_registry = (
    official[["player_id", "player_name"]]
    .dropna()
    .drop_duplicates("player_id")
    .copy()
)

official_registry["unified_player_id"] = (
    "RR_" + official_registry["player_id"]
)

official_registry["data_source"] = "Official RR"

matched_ids = set(
    mapping["official_player_id"].dropna()
)

official_registry.loc[
    official_registry["player_id"].isin(matched_ids),
    "data_source"
] = "Both"

external_registry = mapping[
    mapping["official_player_id"].isna()
][[
    "unified_player_id",
    "external_player_id",
    "external_player_name"
]].rename(columns={
    "external_player_id": "player_id",
    "external_player_name": "player_name"
})

external_registry["data_source"] = "External"

unified = pd.concat(
    [official_registry, external_registry],
    ignore_index=True
)

# ------------------------------------
# 5. SAVE RESULTS
# ------------------------------------

mapping.to_csv(
    BASE / "consolidated_identity_mapping.csv",
    index=False
)

unified.to_csv(
    BASE / "consolidated_player_registry.csv",
    index=False
)

# ------------------------------------
# 6. VALIDATION
# ------------------------------------

print("\n=== CONSOLIDATED IDENTITY MAPPING ===")

print(mapping["mapping_status"].value_counts())

print("\n=== UNIFIED PLAYER REGISTRY ===")

print("Total registry records:", len(unified))

print(unified["data_source"].value_counts())

print("\nMapped external players:",
      mapping["official_player_id"].notna().sum())

print("Conflicting mappings:", len(conflicts))

print("Duplicate unified IDs:",
      unified["unified_player_id"].duplicated().sum())

print("\nSaved results to:", BASE)
