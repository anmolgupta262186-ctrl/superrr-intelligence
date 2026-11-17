
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/official/pri")
OUT = Path("data/processed/official/final")
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------
# 1. GENERATE PLAYER RANKINGS
# -----------------------------------

def generate_rankings(role, player_id, player_name, metrics):

    robustness = pd.read_csv(
        BASE / f"{role}_player_robustness.csv"
    )

    sensitivity = pd.read_csv(
        BASE / f"{role}_pri_sensitivity.csv"
    )

    # Identify strongest format-phase combination

    best_roles = (
        sensitivity.sort_values(
            "mean_pri", ascending=False
        )
        .drop_duplicates(player_id)
        .copy()
    )

    best_roles = best_roles[
        [
            player_id,
            "match_format",
            "phase",
            "balls_normal",
            "balls_pressure",
            "matches_normal",
            "matches_pressure",
            "evaluated_matches",
            "success_rate",
            "peer_group_size",
            "mean_pri"
        ] + metrics
    ]

    best_roles = best_roles.rename(
        columns={"mean_pri": "best_role_pri"}
    )

    # Combine reliability and performance evidence

    rankings = robustness[
        [
            player_id,
            player_name,
            "mean_pri",
            "mean_rank",
            "rank_std",
            "top10_frequency"
        ]
    ].merge(
        best_roles,
        on=player_id,
        how="left",
        validate="one_to_one"
    )

    rankings = rankings.sort_values(
        "mean_pri",
        ascending=False
    ).reset_index(drop=True)

    rankings.insert(
        0, "rank", range(1, len(rankings) + 1)
    )

    # Ranking stability classification

    def stability(freq):
        if freq >= 80:
            return "Very High"
        elif freq >= 60:
            return "High"
        elif freq >= 40:
            return "Moderate"
        return "Low"

    rankings["ranking_stability"] = (
        rankings["top10_frequency"].apply(stability)
    )

    rankings["success_rate_pct"] = (
        rankings["success_rate"] * 100
    )

    # Save complete rankings

    rankings.to_csv(
        OUT / f"final_{role}_rankings.csv",
        index=False
    )

    # Save top 10

    top10 = rankings.head(10).copy()

    top10.to_csv(
        OUT / f"top10_{role}.csv",
        index=False
    )

    # Save phase-wise specialists

    for phase in ["Powerplay", "Middle", "Death"]:

        specialists = (
            sensitivity[sensitivity["phase"] == phase]
            .sort_values("mean_pri", ascending=False)
            .drop_duplicates(player_id)
            .head(10)
        )

        specialists.to_csv(
            OUT / f"{role}_{phase.lower()}_specialists.csv",
            index=False
        )

    print(f"\n=== FINAL {role.upper()} RANKINGS ===")

    print("Total ranked players:", len(rankings))

    print(
        top10[
            [
                "rank",
                player_name,
                "match_format",
                "phase",
                "balls_pressure",
                "mean_pri",
                "top10_frequency",
                "ranking_stability"
            ]
        ].round(2).to_string(index=False)
    )


# -----------------------------------
# 2. BATTING RANKINGS
# -----------------------------------

generate_rankings(
    "batting",
    "striker_id",
    "striker_name",
    [
        "sr_normal",
        "sr_pressure",
        "sr_improvement",
        "dismissal_rate_normal",
        "dismissal_rate_pressure",
        "dismissal_improvement"
    ]
)

# -----------------------------------
# 3. BOWLING RANKINGS
# -----------------------------------

generate_rankings(
    "bowling",
    "bowler_id",
    "bowler_name",
    [
        "run_rate_normal",
        "run_rate_pressure",
        "run_rate_improvement",
        "wicket_rate_normal",
        "wicket_rate_pressure",
        "wicket_rate_improvement"
    ]
)

print("\nRankings saved to:", OUT)
