
import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw/ipl_json")
OUTPUT_DIR = Path("data/processed")

matches = pd.read_csv(OUTPUT_DIR / "rr_matches_2025_2026.csv")

selected_ids = set(matches["match_id"].astype(str))

deliveries = []

for file in DATA_DIR.rglob("*.json"):

    if file.stem not in selected_ids:
        continue

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    info = data["info"]
    teams = info["teams"]

    for innings_no, innings in enumerate(data["innings"], start=1):

        batting_team = innings["team"]
        bowling_team = next(
            (team for team in teams if team != batting_team),
            None
        )

        for over in innings["overs"]:

            over_number = over["over"] + 1

            for ball_no, ball in enumerate(
                over["deliveries"], start=1
            ):

                runs = ball["runs"]
                extras = ball.get("extras", {})
                wickets = ball.get("wickets", [])

                deliveries.append({
                    "match_id": file.stem,
                    "season": str(info["season"]),
                    "date": info["dates"][0],
                    "innings": innings_no,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "over": over_number,
                    "ball_in_over": ball_no,
                    "batter": ball["batter"],
                    "bowler": ball["bowler"],
                    "non_striker": ball["non_striker"],
                    "batter_runs": runs["batter"],
                    "extra_runs": runs["extras"],
                    "total_runs": runs["total"],
                    "extras": json.dumps(extras),
                    "is_wicket": len(wickets) > 0,
                    "wicket_count": len(wickets),
                    "dismissal_types": ",".join(
                        w["kind"] for w in wickets
                    ),
                    "players_out": ",".join(
                        w["player_out"] for w in wickets
                    )
                })

df = pd.DataFrame(deliveries)

output_file = OUTPUT_DIR / "rr_deliveries_2025_2026.csv"

df.to_csv(output_file, index=False)

print("Total deliveries:", len(df))

print("\nSeason-wise deliveries:")
print(df.groupby("season").size())

print("\nBatting teams:")
print(df["batting_team"].value_counts())

print("\nTotal wickets:", df["wicket_count"].sum())

print("\nSaved:", output_file)
