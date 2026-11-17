
from pathlib import Path
import pandas as pd
import numpy as np
import re

BASE = Path("data/processed")
PERF = BASE / "unified/performance"
AUCTION = BASE / "auction2027"
OUT = AUCTION / "whi"

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD DATA
# ------------------------------------

players = pd.read_csv(
    AUCTION / "quality_control/qc_scouting_pool.csv",
    low_memory=False
)

bat = pd.read_csv(
    PERF / "unified_batting_performance.csv",
    low_memory=False
)

bowl = pd.read_csv(
    PERF / "unified_bowling_performance.csv",
    low_memory=False
)

official = pd.read_csv(
    BASE / "official/clean_deliveries.csv",
    dtype={"striker_id": str, "bowler_id": str},
    low_memory=False
)

bat["skill"] = "Batting"
bowl["skill"] = "Bowling"

reference = pd.concat([bat, bowl], ignore_index=True)

reference = reference[
    reference["pri"].notna()
].copy()

# ------------------------------------
# 2. IDENTIFY PACE AND SPIN
# ------------------------------------

def bowling_style(value):

    value = str(value).lower().strip()

    if re.search(r"spin|break|orthodox|chinaman", value):
        return "Spin"

    if re.search(r"pace|fast|medium|seam", value):
        return "Pace"

    return "Unknown"


official["style"] = official[
    "pace_or_spin"
].apply(bowling_style)

unknown = official["style"] == "Unknown"

official.loc[unknown, "style"] = official.loc[
    unknown, "bowling_type"
].apply(bowling_style)

styles = official[
    official["style"] != "Unknown"
].copy()

styles = styles.groupby([
    "bowler_id", "style"
]).size().reset_index(name="deliveries")

styles["share"] = (
    styles["deliveries"]
    / styles.groupby("bowler_id")["deliveries"]
    .transform("sum")
)

styles = styles.sort_values(
    "deliveries", ascending=False
).drop_duplicates("bowler_id")

styles.loc[
    styles["share"] < 0.80, "style"
] = "Mixed"

styles["unified_player_id"] = (
    "RR_" + styles["bowler_id"]
)

players = players.merge(
    styles[["unified_player_id", "style"]],
    on="unified_player_id",
    how="left"
)

players["style"] = players["style"].fillna("Unknown")

# ------------------------------------
# 3. REFINE BOWLING ROLES
# ------------------------------------

def refined_role(row):

    role = row["target_role"]
    style = row["style"]

    if row["skill"] == "Bowling":

        if role == "Death Bowler":

            if style == "Pace":
                return "Death Pacer"

            if style == "Spin":
                return "Death Spinner"

            return "Death Bowler - Style Review"

        if role == "Powerplay Bowler":

            if style == "Pace":
                return "Powerplay Pacer"

            if style == "Spin":
                return "Powerplay Spinner"

            return "Powerplay Bowler - Style Review"

        if role == "Middle Over Bowler":

            if style == "Pace":
                return "Middle Over Pacer"

            if style == "Spin":
                return "Middle Over Spinner"

            return "Middle Bowler - Style Review"

    return role


players["specialist_role"] = players.apply(
    refined_role, axis=1
)

# ------------------------------------
# 4. PREPARE PERFORMANCE METRICS
# ------------------------------------

def prepare_metrics(df):

    df = df.copy()

    df["run_control"] = df[
        "economy_pressure"
    ].combine_first(df["run_rate_pressure"])

    df["run_control_type"] = np.where(
        df["economy_pressure"].notna(),
        "Actual Economy",
        "Off-bat Run Rate"
    )

    return df


players = prepare_metrics(players)
reference = prepare_metrics(reference)

# ------------------------------------
# 5. COMPARABLE PEER GROUPS
# ------------------------------------

def peer_key(row):

    role = row.get("batting_role", "")

    if (
        row["skill"] != "Batting"
        or row["source"] == "Official RR"
        or pd.isna(role)
    ):
        role = ""

    control = ""

    if row["skill"] == "Bowling":
        control = row["run_control_type"]

    return (
        row["skill"],
        row["source"],
        row["competition"],
        row["baseline_category"],
        row["phase"],
        role,
        control
    )


players["peer_key"] = players.apply(peer_key, axis=1)
reference["peer_key"] = reference.apply(peer_key, axis=1)

peer_groups = {
    key: group.drop_duplicates("unified_player_id")
    for key, group in reference.groupby("peer_key")
}

# ------------------------------------
# 6. WHI WEIGHTS
# ------------------------------------

BAT_MIDDLE = {
    "sr_pressure": (0.30, True),
    "dismissal_rate_pressure": (0.35, False),
    "boundary_pct_pressure": (0.15, True),
    "dot_pct_pressure": (0.20, False)
}

BAT_FINISHER = {
    "sr_pressure": (0.40, True),
    "dismissal_rate_pressure": (0.15, False),
    "boundary_pct_pressure": (0.30, True),
    "dot_pct_pressure": (0.15, False)
}

BOWL_DEATH = {
    "run_control": (0.50, False),
    "wicket_rate_pressure": (0.30, True),
    "dot_pct_pressure": (0.20, True)
}

BOWL_POWERPLAY = {
    "run_control": (0.30, False),
    "wicket_rate_pressure": (0.50, True),
    "dot_pct_pressure": (0.20, True)
}

BOWL_MIDDLE = {
    "run_control": (0.40, False),
    "wicket_rate_pressure": (0.40, True),
    "dot_pct_pressure": (0.20, True)
}

def get_weights(row):

    if row["skill"] == "Batting":

        if row["target_role"] == "Finisher":
            return BAT_FINISHER

        return BAT_MIDDLE

    if row["phase"] == "Death":
        return BOWL_DEATH

    if row["phase"] == "Powerplay":
        return BOWL_POWERPLAY

    return BOWL_MIDDLE

# ------------------------------------
# 7. PEER PERCENTILE SCORING
# ------------------------------------

def percentile(value, values, higher_better):

    if not higher_better:
        value = -value
        values = -values

    lower = (values < value).sum()
    equal = (values == value).sum()

    return 100 * (lower + 0.5 * equal) / len(values)


def calculate_whi(row):

    peers = peer_groups.get(row["peer_key"])

    if peers is None or len(peers) < 5:
        return pd.Series({
            "whi": np.nan,
            "whi_peer_count": 0 if peers is None else len(peers),
            "metric_coverage": 0,
            "whi_metrics_used": "",
            "whi_status": "Insufficient peers"
        })

    weights = get_weights(row)

    score = 0
    total_weight = 0
    used = []

    for metric, (weight, higher) in weights.items():

        value = row.get(metric, np.nan)

        values = pd.to_numeric(
            peers[metric], errors="coerce"
        ).dropna().to_numpy()

        if pd.isna(value) or len(values) < 5:
            continue

        metric_score = percentile(
            float(value), values, higher
        )

        score += weight * metric_score
        total_weight += weight
        used.append(metric)

    if len(used) < 2:
        whi = np.nan
    else:
        whi = score / total_weight

        # Reduce the effect of small samples
        balls = float(row["balls_pressure"])
        confidence = balls / (balls + 50)

        whi = 50 + confidence * (whi - 50)

    return pd.Series({
        "whi": whi,
        "whi_peer_count": len(peers),
        "metric_coverage": total_weight * 100,
        "whi_metrics_used": ", ".join(used),
        "whi_status": (
            "Full metrics" if total_weight >= 0.999
            else "Reduced metrics"
        ) if pd.notna(whi) else "Insufficient metrics"
    })


players = pd.concat([
    players,
    players.apply(calculate_whi, axis=1)
], axis=1)

# ------------------------------------
# 8. RECRUITMENT INDEX
# ------------------------------------

players["rri"] = (
    0.50 * players["whi"]
    + 0.50 * players["pri"]
)

players["rri_whi60"] = (
    0.60 * players["whi"]
    + 0.40 * players["pri"]
)

players["rri_pri60"] = (
    0.40 * players["whi"]
    + 0.60 * players["pri"]
)

# ------------------------------------
# 9. SAVE RESULTS
# ------------------------------------

players = players.sort_values(
    "rri", ascending=False
)

players.to_csv(
    OUT / "complete_whi_analysis.csv",
    index=False
)

ranked = players[
    players["rri"].notna()
].copy()

ranked.to_csv(
    OUT / "rri_ranked_evidence.csv",
    index=False
)

style_review = players[
    (players["skill"] == "Bowling")
    & players["style"].isin(["Unknown", "Mixed"])
]

style_review[[
    "canonical_name",
    "unified_player_id",
    "style",
    "qc_status"
]].drop_duplicates().to_csv(
    OUT / "bowling_style_review.csv",
    index=False
)

# ------------------------------------
# 10. GROUP-WISE TOP PLAYERS
# ------------------------------------

for role in [
    "Death Pacer",
    "Middle Order Batter",
    "Finisher",
    "Powerplay Pacer",
    "Middle Over Spinner"
]:

    data = ranked[
        ranked["specialist_role"] == role
    ].copy()

    data = data[
        data["baseline_category"] == "Normal"
    ]

    data["metric_group"] = (
        data["comparison_group"]
        + " | "
        + data["phase"]
        + " | "
        + data["batting_role"].fillna("")
        + " | "
        + data["whi_metrics_used"]
        + " | "
        + np.where(
            data["skill"] == "Bowling",
            data["run_control_type"],
            ""
        )
    )

    data = data.drop_duplicates([
        "name_key", "metric_group"
    ])

    data["group_rank"] = (
        data.groupby("metric_group").cumcount() + 1
    )

    top = data[data["group_rank"] <= 10]

    filename = role.lower().replace(" ", "_")

    top.to_csv(
        OUT / f"top_{filename}.csv",
        index=False
    )

    print(f"\n=== {role.upper()} ===")

    for group, records in top.groupby("metric_group"):

        print("\nComparison:", group)

        print(records[[
            "canonical_name",
            "balls_pressure",
            "pri",
            "whi",
            "rri"
        ]].round(2).to_string(index=False))

# ------------------------------------
# 11. FINAL SUMMARY
# ------------------------------------

print("\n=== BOWLING STYLE VALUES ===")
print(official["pace_or_spin"].value_counts())

print("\n=== WHI SUMMARY ===")
print(players["whi_status"].value_counts())

print("\n=== SPECIALIST ROLE COVERAGE ===")

print(
    ranked.groupby("specialist_role")
    ["name_key"].nunique()
)

print("\nTotal evaluated records:", len(ranked))

print("Unique evaluated players:",
      ranked["name_key"].nunique())

print("Bowlers requiring style verification:",
      style_review["name_key"].nunique())

print("\nSaved files to:", OUT)
