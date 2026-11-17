
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed")

OFFICIAL = BASE / "official/pri"
EXTERNAL = BASE / "external/pri"
EMERGING = BASE / "external/emerging_talent"
UNIFIED = BASE / "unified"

OUT = UNIFIED / "performance"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD PLAYER IDENTITIES
# ------------------------------------

mapping = pd.read_csv(
    UNIFIED / "consolidated_identity_mapping.csv",
    dtype=str
)

registry = pd.read_csv(
    UNIFIED / "consolidated_player_registry.csv",
    dtype=str
)

identity = mapping[
    [
        "external_player_id",
        "unified_player_id",
        "mapping_status"
    ]
]

# ------------------------------------
# 2. LOAD OFFICIAL PERFORMANCE
# ------------------------------------

def load_official(role, player_id, name):

    df = pd.read_csv(
        OFFICIAL / f"{role}_pri_sensitivity.csv",
        dtype={player_id: str}
    )

    df["unified_player_id"] = (
        "RR_" + df[player_id]
    )

    df["source"] = "Official RR"
    df["competition"] = df["match_format"]
    df["baseline_category"] = "Normal"

    df["pri"] = df["mean_pri"]

    df["evidence_status"] = "Standard PRI"
    df["mapping_status"] = "Official identity"

    df["balls_baseline"] = df["balls_normal"]

    return df.rename(
        columns={name: "player_name"}
    )

# ------------------------------------
# 3. LOAD EXTERNAL PERFORMANCE
# ------------------------------------

def load_external(role, player_id, name):

    df = pd.read_csv(
        EXTERNAL / f"external_{role}_pri_ranked.csv",
        dtype={player_id: str}
    )

    df = df.merge(
        identity,
        left_on=player_id,
        right_on="external_player_id",
        how="left",
        validate="many_to_one"
    )

    df["unified_player_id"] = (
        df["unified_player_id"]
        .fillna("EXT_" + df[player_id])
    )

    df["source"] = "External leagues"
    df["competition"] = df["league"]

    df["pri"] = df[f"{role}_pri"]

    df["evidence_status"] = "Standard PRI"

    return df.rename(
        columns={name: "player_name"}
    )

# ------------------------------------
# 4. LOAD SMAT EMERGING PERFORMANCE
# ------------------------------------

def load_emerging(role, player_id, name):

    df = pd.read_csv(
        EMERGING / f"smat_{role}_emerging_pri.csv",
        dtype={player_id: str}
    )

    df = df.merge(
        identity,
        left_on=player_id,
        right_on="external_player_id",
        how="left",
        validate="many_to_one"
    )

    df["unified_player_id"] = (
        df["unified_player_id"]
        .fillna("EXT_" + df[player_id])
    )

    df["source"] = "Emerging talent"

    df["competition"] = (
        "Syed Mushtaq Ali Trophy"
    )

    df["pri"] = df["emerging_pri"]

    return df.rename(
        columns={name: "player_name"}
    )

# ------------------------------------
# 5. COMBINE PERFORMANCE RECORDS
# ------------------------------------

def combine(role, player_id, name):

    official = load_official(
        role, player_id, name
    )

    external = load_external(
        role, player_id, name
    )

    emerging = load_emerging(
        role, player_id, name
    )

    combined = pd.concat(
        [official, external, emerging],
        ignore_index=True
    )

    # Preserve source-specific player names
    combined["source_player_name"] = (
        combined["player_name"]
    )

    canonical_names = (
        registry.set_index("unified_player_id")
        ["player_name"]
    )

    combined["player_name"] = (
        combined["unified_player_id"]
        .map(canonical_names)
        .fillna(combined["player_name"])
    )

    combined = combined.sort_values(
        "pri",
        ascending=False
    )

    combined.to_csv(
        OUT / f"unified_{role}_performance.csv",
        index=False
    )

    # --------------------------------
    # 6. PLAYER COVERAGE SUMMARY
    # --------------------------------

    ranked = combined[
        combined["pri"].notna()
    ].copy()

    summary = (
        ranked.groupby(
            ["unified_player_id", "player_name"],
            as_index=False
        )
        .agg(
            performance_records=("pri", "size"),

            competition_count=(
                "competition", "nunique"
            ),

            competitions=(
                "competition",
                lambda x: " | ".join(sorted(set(x)))
            ),

            sources=(
                "source",
                lambda x: " | ".join(sorted(set(x)))
            ),

            highest_observed_pri=("pri", "max")
        )
    )

    summary = summary.sort_values(
        ["competition_count", "performance_records"],
        ascending=False
    )

    summary.to_csv(
        OUT / f"unified_{role}_coverage.csv",
        index=False
    )

    print(f"\n=== UNIFIED {role.upper()} ===")

    print("Performance records:", len(combined))

    print("Unique players:",
          combined["unified_player_id"].nunique())

    print("Players with PRI:",
          ranked["unified_player_id"].nunique())

    print("\nRecords by source:")
    print(combined["source"].value_counts())

    print("\n=== MULTI-COMPETITION PLAYERS ===")

    print(
        summary[
            [
                "player_name",
                "competition_count",
                "performance_records",
                "highest_observed_pri"
            ]
        ].head(20).round(2).to_string(index=False)
    )

# ------------------------------------
# 7. EXECUTE
# ------------------------------------

combine(
    "batting",
    "striker_id",
    "striker_name"
)

combine(
    "bowling",
    "bowler_id",
    "bowler_name"
)

print("\nResults saved to:", OUT)
