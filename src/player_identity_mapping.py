
from pathlib import Path
from collections import defaultdict
import pandas as pd
import unicodedata
import re

OFFICIAL = Path("data/raw/rr_official")
EXTERNAL = Path("data/processed/external")
OUT = Path("data/processed/unified")

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD PLAYER REGISTRIES
# ------------------------------------

official = pd.read_csv(
    OFFICIAL / "competition_team_player_mapping.csv",
    dtype={"player_id": str}
)

external = pd.read_csv(
    EXTERNAL / "external_players.csv",
    dtype={"player_id": str}
)

official = official[
    ["player_id", "player_name"]
].dropna().drop_duplicates()

external = external.dropna(
    subset=["player_id", "player_name"]
).drop_duplicates("player_id")

# ------------------------------------
# 2. NORMALISE PLAYER NAMES
# ------------------------------------

def normalize(name):

    name = unicodedata.normalize(
        "NFKD", str(name)
    )

    name = name.encode(
        "ascii", "ignore"
    ).decode("ascii")

    name = name.lower()

    name = re.sub(r"[^a-z0-9\s]", "", name)

    return " ".join(name.split())


def name_signature(name):

    parts = normalize(name).split()

    if len(parts) < 2:
        return None

    first_initial = parts[0][0]
    surname = parts[-1]

    return first_initial, surname


official["normalized_name"] = (
    official["player_name"].apply(normalize)
)

external["normalized_name"] = (
    external["player_name"].apply(normalize)
)

# ------------------------------------
# 3. CREATE SEARCH INDEXES
# ------------------------------------

exact_index = defaultdict(set)
initial_index = defaultdict(set)

official_names = (
    official.drop_duplicates("player_id")
    .set_index("player_id")["player_name"]
    .to_dict()
)

for row in official.itertuples(index=False):

    exact_index[row.normalized_name].add(
        row.player_id
    )

    signature = name_signature(row.player_name)

    if signature:

        initial_index[signature].add(
            row.player_id
        )

external_name_counts = (
    external["normalized_name"].value_counts()
)

# ------------------------------------
# 4. MANUAL VERIFICATION FILE
# ------------------------------------

manual_file = OUT / "manual_identity_mapping.csv"

if not manual_file.exists():

    pd.DataFrame(columns=[
        "external_player_id",
        "official_player_id",
        "verification_source"
    ]).to_csv(manual_file, index=False)

manual = pd.read_csv(
    manual_file,
    dtype=str
).dropna(subset=[
    "external_player_id",
    "official_player_id",
    "verification_source"
])

if manual["external_player_id"].duplicated().any():
    raise ValueError("Duplicate manual player mappings")

manual_map = (
    manual.set_index("external_player_id")
    ["official_player_id"].to_dict()
)

# ------------------------------------
# 5. MATCH PLAYER IDENTITIES
# ------------------------------------

results = []

for row in external.itertuples(index=False):

    external_id = row.player_id
    external_name = row.player_name
    normalized = row.normalized_name

    mapped_id = None
    candidates = set()

    if external_id in manual_map:

        mapped_id = manual_map[external_id]

        if mapped_id not in official_names:
            raise ValueError(
                f"Unknown official ID: {mapped_id}"
            )

        status = "Manually verified"

    else:

        exact_candidates = exact_index.get(
            normalized, set()
        )

        signature = name_signature(external_name)

        initial_candidates = initial_index.get(
            signature, set()
        )

        if (
            len(exact_candidates) == 1
            and external_name_counts[normalized] == 1
        ):

            mapped_id = next(iter(exact_candidates))
            status = "Exact name match"

        else:

            candidates = (
                exact_candidates | initial_candidates
            )

            if len(candidates) == 1:
                status = "Initial match - review"

            elif len(candidates) > 1:
                status = "Ambiguous - review"

            else:
                status = "No official match"

    unified_id = (
        f"RR_{mapped_id}"
        if mapped_id is not None
        else f"EXT_{external_id}"
    )

    results.append({
        "unified_player_id": unified_id,

        "external_player_id": external_id,
        "external_player_name": external_name,

        "official_player_id": mapped_id,
        "official_player_name": official_names.get(
            mapped_id
        ),

        "mapping_status": status,

        "candidate_ids": "|".join(
            sorted(candidates)
        ),

        "candidate_names": "|".join(
            official_names[x]
            for x in sorted(candidates)
        )
    })

mapping = pd.DataFrame(results)

# ------------------------------------
# 6. CHECK CONFLICTING MAPPINGS
# ------------------------------------

matched = mapping[
    mapping["official_player_id"].notna()
]

conflicts = matched[
    matched["official_player_id"].duplicated(
        keep=False
    )
]

if not conflicts.empty:

    mapping.loc[
        conflicts.index, "mapping_status"
    ] = "Conflicting mapping - review"

    mapping.loc[
        conflicts.index, "official_player_id"
    ] = None

    mapping.loc[
        conflicts.index, "official_player_name"
    ] = None

    mapping.loc[
        conflicts.index, "unified_player_id"
    ] = (
        "EXT_" +
        mapping.loc[
            conflicts.index, "external_player_id"
        ]
    )

# ------------------------------------
# 7. SAVE MAPPING RESULTS
# ------------------------------------

mapping.to_csv(
    OUT / "player_identity_mapping.csv",
    index=False
)

review = mapping[
    mapping["mapping_status"].str.contains(
        "review", case=False
    )
].copy()

review.to_csv(
    OUT / "identity_review_required.csv",
    index=False
)

# ------------------------------------
# 8. CREATE UNIFIED PLAYER REGISTRY
# ------------------------------------

official_registry = (
    official.drop_duplicates("player_id")[
        ["player_id", "player_name"]
    ].copy()
)

official_registry["unified_player_id"] = (
    "RR_" + official_registry["player_id"]
)

official_registry["data_source"] = "Official RR"

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

matched_ids = set(
    mapping["official_player_id"].dropna()
)

unified.loc[
    unified["unified_player_id"].isin(
        {"RR_" + x for x in matched_ids}
    ),
    "data_source"
] = "Both"

unified.to_csv(
    OUT / "unified_player_registry.csv",
    index=False
)

# ------------------------------------
# 9. DISPLAY VALIDATION
# ------------------------------------

print("\n=== PLAYER IDENTITY MAPPING ===")

print("Official players:",
      official["player_id"].nunique())

print("External players:",
      external["player_id"].nunique())

print("\n=== MAPPING STATUS ===")
print(mapping["mapping_status"].value_counts())

print("\n=== SAMPLE EXACT MATCHES ===")

print(
    mapping[
        mapping["mapping_status"] == "Exact name match"
    ][[
        "external_player_name",
        "official_player_name"
    ]].head(20).to_string(index=False)
)

print("\n=== INITIAL MATCHES TO VERIFY ===")

print(
    review[[
        "external_player_name",
        "candidate_names",
        "mapping_status"
    ]].head(30).to_string(index=False)
)

print("\n=== UNIFIED REGISTRY ===")
print("Total registry records:", len(unified))
print(unified["data_source"].value_counts())

print("\nFiles saved to:", OUT)
