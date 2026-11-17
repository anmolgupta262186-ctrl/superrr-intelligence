
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/official/pri")

# ------------------------------------
# 1. MODEL WEIGHTS
# ------------------------------------

MODELS = {
    "default":     [0.30, 0.25, 0.20, 0.15, 0.10],
    "balanced":    [0.20, 0.20, 0.20, 0.20, 0.20],
    "improvement": [0.40, 0.35, 0.10, 0.10, 0.05],
    "absolute":    [0.15, 0.15, 0.30, 0.10, 0.30],
    "consistency": [0.20, 0.20, 0.15, 0.35, 0.10]
}

SHRINKAGE = [25, 50, 100]

MIN_PEERS = 10

GROUP = ["match_format", "phase"]

# ------------------------------------
# 2. SENSITIVITY FUNCTION
# ------------------------------------

def analyse(role, player_id, player_name, metrics):

    df = pd.read_csv(
        BASE / f"{role}_pri_ranked.csv"
    )

    # Exclude insufficient peer groups

    excluded = df[
        df["peer_group_size"] < MIN_PEERS
    ].copy()

    excluded.to_csv(
        BASE / f"{role}_insufficient_peers.csv",
        index=False
    )

    df = df[
        df["peer_group_size"] >= MIN_PEERS
    ].copy()

    # Correct percentile normalisation
    score_columns = []

    for i, (metric, ascending) in enumerate(metrics):

        col = f"metric_score_{i}"

        rank = (
            df.groupby(GROUP)[metric]
            .rank(
                method="average",
                ascending=ascending
            )
        )

        size = (
            df.groupby(GROUP)[metric]
            .transform("count")
        )

        df[col] = 100 * (rank - 1) / (size - 1)

        score_columns.append(col)

    # --------------------------------
    # 3. TEST ALL CONFIGURATIONS
    # --------------------------------

    score_cols = []

    for model, weights in MODELS.items():

        raw_score = (
            df[score_columns].to_numpy()
            @ np.array(weights)
        )

        for k in SHRINKAGE:

            col = f"{model}_k{k}"

            confidence = (
                df["effective_sample"]
                / (df["effective_sample"] + k)
            )

            df[col] = (
                50 + confidence * (raw_score - 50)
            )

            score_cols.append(col)

    # --------------------------------
    # 4. ROLE-SPECIFIC ROBUSTNESS
    # --------------------------------

    df["mean_pri"] = df[score_cols].mean(axis=1)
    df["pri_std"] = df[score_cols].std(axis=1)
    df["minimum_pri"] = df[score_cols].min(axis=1)
    df["maximum_pri"] = df[score_cols].max(axis=1)

    df = df.sort_values(
        "mean_pri",
        ascending=False
    )

    df.to_csv(
        BASE / f"{role}_pri_sensitivity.csv",
        index=False
    )

    # --------------------------------
    # 5. UNIQUE PLAYER RANKINGS
    # --------------------------------

    players = (
        df.groupby(player_id, as_index=False)[score_cols]
        .max()
    )

    names = df[
        [player_id, player_name]
    ].drop_duplicates(player_id)

    players = players.merge(
        names,
        on=player_id,
        how="left"
    )

    rank_cols = []

    for col in score_cols:

        rank_col = f"rank_{col}"

        players[rank_col] = (
            players[col].rank(
                ascending=False,
                method="min"
            )
        )

        rank_cols.append(rank_col)

    players["mean_pri"] = (
        players[score_cols].mean(axis=1)
    )

    players["mean_rank"] = (
        players[rank_cols].mean(axis=1)
    )

    players["rank_std"] = (
        players[rank_cols].std(axis=1)
    )

    players["top10_frequency"] = (
        (players[rank_cols] <= 10)
        .mean(axis=1) * 100
    )

    players = players.sort_values(
        "mean_pri",
        ascending=False
    )

    players.to_csv(
        BASE / f"{role}_player_robustness.csv",
        index=False
    )

    # --------------------------------
    # 6. DISPLAY RESULTS
    # --------------------------------

    print(f"\n=== {role.upper()} SENSITIVITY ===")

    print("Test configurations:", len(score_cols))
    print("Excluded comparisons:", len(excluded))
    print("Remaining comparisons:", len(df))
    print("Unique players:", len(players))

    print("\n=== TOP 15 ROBUST PLAYERS ===")

    print(
        players[
            [
                player_name,
                "mean_pri",
                "mean_rank",
                "rank_std",
                "top10_frequency"
            ]
        ]
        .head(15)
        .round(2)
        .to_string(index=False)
    )


# ------------------------------------
# 7. BATTING ANALYSIS
# ------------------------------------

analyse(
    "batting",
    "striker_id",
    "striker_name",
    [
        ("sr_improvement", True),
        ("dismissal_improvement", True),
        ("sr_pressure", True),
        ("success_rate", True),
        ("dismissal_rate_pressure", False)
    ]
)

# ------------------------------------
# 8. BOWLING ANALYSIS
# ------------------------------------

analyse(
    "bowling",
    "bowler_id",
    "bowler_name",
    [
        ("run_rate_improvement", True),
        ("wicket_rate_improvement", True),
        ("run_rate_pressure", False),
        ("success_rate", True),
        ("wicket_rate_pressure", True)
    ]
)

print("\nSensitivity analysis completed.")
