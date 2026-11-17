
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/external")
PRI = BASE / "pri"
OUT = BASE / "emerging_talent"

OUT.mkdir(parents=True, exist_ok=True)

LEAGUE = "Syed Mushtaq Ali Trophy"

MIN_BALLS = 12
MIN_MATCHES = 2
MIN_PEERS = 3
SHRINKAGE = 100

WEIGHTS = np.array([
    0.30, 0.25, 0.20, 0.15, 0.10
])

# ------------------------------------
# 1. EMERGING TALENT PRI
# ------------------------------------

def calculate_pri(role, player_id, name, metrics, groups):

    frames = []

    for baseline in ["normal", "moderate"]:

        df = pd.read_csv(
            PRI / f"external_{role}_{baseline}_all.csv"
        )

        df = df[df["league"] == LEAGUE].copy()

        eligible = df[
            (df["balls_baseline"] >= MIN_BALLS)
            & (df["balls_pressure"] >= MIN_BALLS)
            & (df["matches_baseline"] >= MIN_MATCHES)
            & (df["matches_pressure"] >= MIN_MATCHES)
            & (df["evaluated_matches"] >= MIN_MATCHES)
        ].copy()

        eligible["peer_group_size"] = (
            eligible.groupby(groups)[player_id]
            .transform("nunique")
        )

        eligible["emerging_pri"] = np.nan

        ranked = eligible[
            eligible["peer_group_size"] >= MIN_PEERS
        ].copy()

        score_columns = []

        for i, (metric, ascending) in enumerate(metrics):

            col = f"metric_score_{i}"

            rank = ranked.groupby(groups)[metric].rank(
                ascending=ascending,
                method="average"
            )

            size = ranked.groupby(groups)[metric].transform(
                "count"
            )

            ranked[col] = (
                100 * (rank - 1) / (size - 1)
            )

            score_columns.append(col)

        ranked["raw_pri"] = (
            ranked[score_columns].to_numpy()
            @ WEIGHTS
        )

        ranked["effective_sample"] = (
            2 * ranked["balls_baseline"]
            * ranked["balls_pressure"]
            / (
                ranked["balls_baseline"]
                + ranked["balls_pressure"]
            )
        )

        confidence = (
            ranked["effective_sample"]
            / (ranked["effective_sample"] + SHRINKAGE)
        )

        ranked["emerging_pri"] = (
            50 + confidence
            * (ranked["raw_pri"] - 50)
        )

        eligible.loc[
            ranked.index, "emerging_pri"
        ] = ranked["emerging_pri"]

        eligible["evidence_status"] = np.where(
            eligible["emerging_pri"].notna(),
            "Preliminary ranking",
            "Insufficient peers"
        )

        frames.append(eligible)

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    combined = combined.sort_values(
        "emerging_pri",
        ascending=False
    )

    combined.to_csv(
        OUT / f"smat_{role}_emerging_pri.csv",
        index=False
    )

    print(f"\n=== SMAT {role.upper()} ===")

    print("Eligible comparisons:", len(combined))
    print("Ranked comparisons:",
          combined["emerging_pri"].notna().sum())

    print("Unique players:",
          combined[player_id].nunique())

    columns = [
        name,
        "phase",
        "baseline_category",
        "balls_baseline",
        "balls_pressure",
        "emerging_pri",
        "evidence_status"
    ]

    if role == "batting":
        columns.insert(2, "batting_role")
        columns.insert(6, "sr_pressure")
    else:
        columns.insert(5, "economy_pressure")

    print(
        combined[columns]
        .head(25)
        .round(2)
        .to_string(index=False)
    )


# ------------------------------------
# 2. BATTING PRI
# ------------------------------------

calculate_pri(
    "batting",
    "striker_id",
    "striker_name",
    [
        ("sr_improvement", True),
        ("dismissal_improvement", True),
        ("sr_pressure", True),
        ("success_rate", True),
        ("dismissal_rate_pressure", False)
    ],
    ["phase", "batting_role"]
)

# ------------------------------------
# 3. BOWLING PRI
# ------------------------------------

calculate_pri(
    "bowling",
    "bowler_id",
    "bowler_name",
    [
        ("economy_improvement", True),
        ("wicket_rate_improvement", True),
        ("economy_pressure", False),
        ("success_rate", True),
        ("wicket_rate_pressure", True)
    ],
    ["phase"]
)

# ------------------------------------
# 4. HIGH-PRESSURE TALENT DISCOVERY
# ------------------------------------

# Include players without sufficient normal
# or moderate baseline appearances.

df = pd.read_csv(
    BASE / "external_pressure_deliveries.csv",
    low_memory=False
)

df = df[df["league"] == LEAGUE].copy()

# Batting watchlist

bat = (
    df[df["batting_pressure_category"] == "High"]
    .groupby([
        "striker_id",
        "striker_name",
        "phase",
        "batting_role"
    ], as_index=False)
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("striker_dismissal", "sum"),
        matches=("match_id", "nunique")
    )
)

bat = bat[
    (bat["balls"] >= MIN_BALLS)
    & (bat["matches"] >= MIN_MATCHES)
].copy()

bat["strike_rate"] = (
    100 * bat["runs"] / bat["balls"]
)

bat["dismissals_per_100"] = (
    100 * bat["dismissals"] / bat["balls"]
)

bat = bat.sort_values(
    "strike_rate",
    ascending=False
)

# Bowling watchlist

bowl = (
    df[df["bowling_pressure_category"] == "High"]
    .groupby([
        "bowler_id",
        "bowler_name",
        "phase"
    ], as_index=False)
    .agg(
        runs=("bowler_runs", "sum"),
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum"),
        matches=("match_id", "nunique")
    )
)

bowl = bowl[
    (bowl["balls"] >= MIN_BALLS)
    & (bowl["matches"] >= MIN_MATCHES)
].copy()

bowl["economy"] = (
    6 * bowl["runs"] / bowl["balls"]
)

bowl["wickets_per_100"] = (
    100 * bowl["wickets"] / bowl["balls"]
)

bowl = bowl.sort_values("economy")

# Metadata requires independent verification

for data in [bat, bowl]:
    data["age"] = pd.NA
    data["capped_status"] = "Unverified"
    data["nationality"] = "Unverified"
    data["auction_availability"] = "Unverified"

bat.to_csv(
    OUT / "smat_batting_watchlist.csv",
    index=False
)

bowl.to_csv(
    OUT / "smat_bowling_watchlist.csv",
    index=False
)

# ------------------------------------
# 5. DISPLAY TALENT WATCHLISTS
# ------------------------------------

print("\n=== SMAT MIDDLE ORDER AND FINISHERS ===")

print(
    bat[bat["batting_role"].isin([
        "Middle Order", "Lower Middle Order"
    ])][[
        "striker_name", "phase", "batting_role",
        "runs", "balls", "matches", "strike_rate"
    ]].head(20).round(2).to_string(index=False)
)

for phase in ["Powerplay", "Death"]:

    print(f"\n=== SMAT {phase.upper()} BOWLERS ===")

    print(
        bowl[bowl["phase"] == phase][[
            "bowler_name", "balls", "matches",
            "wickets", "economy", "wickets_per_100"
        ]].head(15).round(2).to_string(index=False)
    )

print("\nUnique batting prospects:",
      bat["striker_id"].nunique())

print("Unique bowling prospects:",
      bowl["bowler_id"].nunique())

print("\nSaved results to:", OUT)
