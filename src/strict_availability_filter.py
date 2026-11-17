
from pathlib import Path
from collections import defaultdict
import pandas as pd
import unicodedata
import re

RAW = Path("data/raw/auction2027")
BASE = Path("data/processed")
OUT = BASE / "auction2027"

# -----------------------------------
# 1. LOAD DATA
# -----------------------------------

players = pd.read_csv(
    OUT / "complete_scouting_registry.csv",
    dtype=str
)

retention = pd.read_csv(
    RAW / "retention_list.csv",
    dtype=str
)

mapping = pd.read_csv(
    BASE / "unified/consolidated_identity_mapping.csv",
    dtype=str
)

people = pd.read_csv(
    "data/raw/register/people.csv",
    dtype=str
)

names = pd.read_csv(
    "data/raw/register/names.csv",
    dtype=str
)

# -----------------------------------
# 2. NORMALISE NAMES
# -----------------------------------

def normalize(name):

    if pd.isna(name):
        return ""

    name = unicodedata.normalize("NFKD", str(name))

    name = name.encode(
        "ascii", "ignore"
    ).decode("ascii").lower()

    return re.sub(r"[^a-z0-9]", "", name)

# -----------------------------------
# 3. KNOWN NAME VARIATIONS
# -----------------------------------

aliases = {
    "Patrick Cummins": "Pat Cummins",
    "Namboori Tilak Varma": "Tilak Varma",
    "Vaibhav Suryavanshi": "Vaibhav Sooryavanshi",
    "Nehal Wadera": "Nehal Wadhera",
    "Rasikh Salam": "Rasikh Dar",
    "George Lind": "George Linde",
    "Luvnith Sisodia": "Luvinith Sisodia",
    "Kumar Kartikeya Singh": "Kumar Kartikeya"
}

alias_lookup = {
    normalize(k): normalize(v)
    for k, v in aliases.items()
}

def name_key(name):

    key = normalize(name)

    return alias_lookup.get(key, key)

# -----------------------------------
# 4. CRICSHEET ALIAS INDEX
# -----------------------------------

register = pd.concat([
    people[["identifier", "name"]],

    people[["identifier", "unique_name"]]
    .rename(columns={"unique_name": "name"}),

    names[["identifier", "name"]]

], ignore_index=True).dropna().drop_duplicates()

id_to_names = defaultdict(set)
name_to_ids = defaultdict(set)

for row in register.itertuples(index=False):

    key = name_key(row.name)

    id_to_names[row.identifier].add(key)
    name_to_ids[key].add(row.identifier)

# Map unified IDs to Cricsheet IDs

unified_to_external = (
    mapping.groupby("unified_player_id")
    ["external_player_id"]
    .agg(set)
    .to_dict()
)

# -----------------------------------
# 5. RETENTION INDEX
# -----------------------------------

retention["name_key"] = (
    retention["player_name"].apply(name_key)
)

retention_index = defaultdict(set)

for index, row in retention.iterrows():

    retention_index[row["name_key"]].add(index)

# -----------------------------------
# 6. IPL ELIGIBILITY SCREENING
# -----------------------------------

# Preliminary screening list.
# Individual eligibility requires verification.

pakistani_players = [
    "Babar Azam",
    "Mohammad Rizwan",
    "Fakhar Zaman",
    "Shaheen Afridi",
    "Shaheen Shah Afridi",
    "Sufiyan Muqeem",
    "Abbas Afridi",
    "Shadab Khan",
    "Haris Rauf",
    "Naseem Shah",
    "Usman Khan",
    "Salman Ali Agha",
    "Agha Salman",
    "Mohammad Nawaz",
    "Mohammad Wasim",
    "Iftikhar Ahmed",
    "Saim Ayub",
    "Abrar Ahmed",
    "Hassan Ali",
    "Hasan Ali",
    "Khushdil Shah",
    "Sahibzada Farhan",
    "Mohammad Haris",
    "Zaman Khan",
    "Azam Khan"
]

blocked_names = {
    name_key(name)
    for name in pakistani_players
}

# -----------------------------------
# 7. MATCH AND CLASSIFY PLAYERS
# -----------------------------------

results = []

for _, row in players.iterrows():

    player_name = row["player_name"]
    unified_id = row["unified_player_id"]

    keys = {name_key(player_name)}

    external_ids = unified_to_external.get(
        unified_id, set()
    )

    for player_id in external_ids:

        for alias in id_to_names.get(player_id, set()):

            # Only use unambiguous register aliases
            if len(name_to_ids[alias]) == 1:
                keys.add(alias)

    matched_records = set()

    for key in keys:

        matched_records.update(
            retention_index.get(key, set())
        )

    record = row.to_dict()

    record["matched_ipl_name"] = None
    record["ipl_2027_franchise"] = None
    record["ipl_2027_status"] = None
    record["retention_evidence"] = None

    eligibility = name_key(
        row.get("ipl_eligibility")
    )

    retirement = name_key(
        row.get("retirement_status")
    )

    registered = name_key(
        row.get("auction_registered")
    )

    verified_metadata = bool(
        name_key(row.get("source"))
    )

    if keys.intersection(blocked_names):

        decision = "Excluded - IPL eligibility screening"

    elif verified_metadata and eligibility == "ineligible":

        decision = "Excluded - IPL ineligible"

    elif verified_metadata and retirement == "retired":

        decision = "Excluded - Retired"

    elif len(matched_records) > 1:

        decision = "Needs identity verification"

    elif len(matched_records) == 1:

        match = retention.loc[
            next(iter(matched_records))
        ]

        status = match["status"]
        franchise = match["franchise"]

        record["matched_ipl_name"] = match["player_name"]
        record["ipl_2027_franchise"] = franchise
        record["ipl_2027_status"] = status
        record["retention_evidence"] = match.get("source")

        if status == "Withdrawn":

            decision = "Excluded - Withdrawn"

        elif status == "Retired":

            decision = "Excluded - Retired"

        elif status in ["Retained", "Traded"]:

            if franchise in ["RR", "Rajasthan Royals"]:

                decision = "Existing RR squad"

            else:

                decision = "Excluded - Contracted"

        elif status == "Released":

            decision = "Potential released target"

        else:

            decision = "Needs retention verification"

    else:

        # Absence from retention records is not
        # proof of availability.

        decision = "Needs availability verification"

    record["final_availability_status"] = decision

    results.append(record)

result = pd.DataFrame(results)

# -----------------------------------
# 8. SEPARATE RECRUITMENT POOLS
# -----------------------------------

excluded = result[
    result["final_availability_status"]
    .str.startswith("Excluded")
]

released = result[
    result["final_availability_status"]
    == "Potential released target"
]

rr_squad = result[
    result["final_availability_status"]
    == "Existing RR squad"
]

pending = result[
    result["final_availability_status"]
    .str.startswith("Needs")
]

# -----------------------------------
# 9. SAVE RESULTS
# -----------------------------------

for filename, data in [
    ("filtered_scouting_registry", result),
    ("strictly_excluded_players", excluded),
    ("released_player_targets", released),
    ("existing_rr_players", rr_squad),
    ("pending_availability_review", pending)
]:

    data.to_csv(
        OUT / f"{filename}.csv",
        index=False
    )

# -----------------------------------
# 10. DISPLAY RESULTS
# -----------------------------------

print("\n=== STRICT AVAILABILITY FILTER ===")

print("Total scouting players:", len(result))

print("\n=== AVAILABILITY STATUS ===")

print(
    result["final_availability_status"]
    .value_counts()
)

print("\n=== POTENTIAL RELEASED TARGETS ===")

print(
    released[[
        "player_name",
        "ipl_2027_franchise"
    ]].to_string(index=False)
)

print("\n=== RETAINED RR PLAYERS IN SCOUTING POOL ===")

print(
    rr_squad["player_name"]
    .to_string(index=False)
)

print("\n=== FINAL SUMMARY ===")

print("Excluded players:", len(excluded))
print("Released targets:", len(released))
print("Existing RR players:", len(rr_squad))
print("Pending verification:", len(pending))

print("\nSaved results to:", OUT)
