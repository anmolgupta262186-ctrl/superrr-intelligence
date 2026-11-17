
from pathlib import Path
from collections import defaultdict
import pandas as pd
import json

RAW = Path("data/raw/external")
OUT = Path("data/processed/domestic/smat")
OUT.mkdir(parents=True, exist_ok=True)

START_YEAR = 2015
END_YEAR = 2026

LEAGUES = {"smat": "Syed Mushtaq Ali Trophy"}

matches = []
deliveries = []
players = {}
errors = []

# ------------------------------------
# 1. ITERATE THROUGH LEAGUES
# ------------------------------------

for folder, league in LEAGUES.items():

    files = sorted((RAW / folder).glob("*.json"))

    print(f"\nProcessing {league}...")
    print("Available files:", len(files))

    match_count = 0
    ball_count = 0

    # --------------------------------
    # 2. EXTRACT MATCH INFORMATION
    # --------------------------------

    for file in files:

        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)

            info = data["info"]

            date = info["dates"][0]
            year = int(date[:4])

            if not START_YEAR <= year <= END_YEAR:
                continue

            if info.get("gender") != "male":
                continue

            if info.get("match_type") != "T20":
                continue

            match_id = f"{folder}_{file.stem}"

            registry = info.get(
                "registry", {}
            ).get("people", {})

            outcome = info.get("outcome", {})
            toss = info.get("toss", {})
            teams = info.get("teams", [])
            event = info.get("event", {})

            matches.append({
                "match_id": match_id,
                "league": league,
                "season": info.get("season"),
                "match_date": date,
                "year": year,
                "venue": info.get("venue"),
                "city": info.get("city"),
                "team_1": teams[0] if teams else None,
                "team_2": teams[1] if len(teams) > 1 else None,
                "winner": outcome.get("winner"),
                "result": outcome.get("result"),
                "result_method": outcome.get("method"),
                "toss_winner": toss.get("winner"),
                "toss_decision": toss.get("decision"),
                "scheduled_overs": info.get("overs", 20),
                "balls_per_over": info.get("balls_per_over", 6),
                "match_stage": event.get("stage")
            })

            match_count += 1

            # ------------------------
            # 3. PLAYER REGISTRY
            # ------------------------

            for team, squad in info.get("players", {}).items():

                for name in squad:

                    player_id = registry.get(name)

                    if player_id is None:
                        continue

                    if player_id not in players:
                        players[player_id] = {
                            "player_id": player_id,
                            "player_name": name,
                            "teams": set(),
                            "leagues": set()
                        }

                    players[player_id]["teams"].add(team)
                    players[player_id]["leagues"].add(league)

            # ------------------------
            # 4. EXTRACT INNINGS
            # ------------------------

            for innings_no, innings in enumerate(
                data.get("innings", []), start=1
            ):

                if innings_no > 2:
                    continue

                if innings.get("super_over", False):
                    continue

                batting_team = innings["team"]

                bowling_team = next(
                    (t for t in teams if t != batting_team),
                    None
                )

                batting_order = {}
                target = innings.get("target", {})

                delivery_number = 0

                # --------------------
                # 5. EXTRACT DELIVERIES
                # --------------------

                for over in innings.get("overs", []):

                    over_number = over["over"] + 1

                    for ball_no, ball in enumerate(
                        over["deliveries"], start=1
                    ):

                        delivery_number += 1

                        batter = ball["batter"]
                        non_striker = ball["non_striker"]
                        bowler = ball["bowler"]

                        for name in [batter, non_striker]:
                            if name not in batting_order:
                                batting_order[name] = (
                                    len(batting_order) + 1
                                )

                        runs = ball["runs"]
                        extras = ball.get("extras", {})

                        wickets = ball.get("wickets", [])

                        team_wickets = [
                            w for w in wickets
                            if w["kind"] not in {
                                "retired hurt",
                                "retired not out"
                            }
                        ]

                        bowler_wickets = [
                            w for w in wickets
                            if w["kind"] in {
                                "bowled",
                                "caught",
                                "caught and bowled",
                                "lbw",
                                "stumped",
                                "hit wicket"
                            }
                        ]

                        deliveries.append({

                            "match_id": match_id,
                            "league": league,
                            "match_date": date,
                            "year": year,

                            "innings": innings_no,
                            "overid": over_number,
                            "over_ball_num": ball_no,
                            "innings_ball_num": delivery_number,

                            "batting_team": batting_team,
                            "bowling_team": bowling_team,

                            "striker_name": batter,
                            "striker_id": registry.get(batter),

                            "non_striker_name": non_striker,
                            "non_striker_id": registry.get(non_striker),

                            "bowler_name": bowler,
                            "bowler_id": registry.get(bowler),

                            "batting_order": batting_order[batter],

                            "batter_runs": runs["batter"],
                            "extras_runs": runs["extras"],
                            "total_runs": runs["total"],

                            "wides": extras.get("wides", 0),
                            "noballs": extras.get("noballs", 0),
                            "byes": extras.get("byes", 0),
                            "legbyes": extras.get("legbyes", 0),
                            "penalty": extras.get("penalty", 0),

                            "team_wicket": len(team_wickets),
                            "bowler_wicket": len(bowler_wickets),

                            "dismissed_players": "|".join(
                                w["player_out"]
                                for w in team_wickets
                            ),

                            "dismissed_player_ids": "|".join(
                                registry.get(w["player_out"], "")
                                for w in team_wickets
                            ),

                            "dismissal_types": "|".join(
                                w["kind"]
                                for w in wickets
                            ),

                            "is_boundary": int(
                                runs["batter"] in [4, 6]
                                and not runs.get("non_boundary", False)
                            ),

                            "target_runs": target.get("runs"),
                            "target_overs": target.get("overs")
                        })

                        ball_count += 1

        except Exception as e:

            errors.append({
                "file": str(file),
                "error": str(e)
            })

    print("Selected matches:", match_count)
    print("Extracted deliveries:", ball_count)

# ------------------------------------
# 6. CREATE DATAFRAMES
# ------------------------------------

matches_df = pd.DataFrame(matches)
balls_df = pd.DataFrame(deliveries)

if matches_df.empty or balls_df.empty:
    raise SystemExit(
        "No data extracted. Check downloaded datasets."
    )

player_records = []

for player in players.values():

    player_records.append({
        "player_id": player["player_id"],
        "player_name": player["player_name"],
        "teams": ", ".join(sorted(player["teams"])),
        "leagues": ", ".join(sorted(player["leagues"])),
        "league_count": len(player["leagues"])
    })

players_df = pd.DataFrame(player_records)

# ------------------------------------
# 7. SAVE DATASETS
# ------------------------------------

matches_df.to_csv(
    OUT / "smat_matches.csv",
    index=False
)

balls_df.to_csv(
    OUT / "smat_deliveries.csv",
    index=False
)

players_df.to_csv(
    OUT / "smat_players.csv",
    index=False
)

pd.DataFrame(
    errors,
    columns=["file", "error"]
).to_csv(
    OUT / "ingestion_errors.csv",
    index=False
)

# ------------------------------------
# 8. VALIDATION
# ------------------------------------

print("\n=== SMAT DATA INGESTION ===")

print("Total matches:", len(matches_df))
print("Total deliveries:", len(balls_df))
print("Unique players:", len(players_df))

print("Unique batters:", balls_df["striker_id"].nunique())
print("Unique bowlers:", balls_df["bowler_id"].nunique())

print("Ingestion errors:", len(errors))

print("\n=== MATCHES BY LEAGUE ===")
print(matches_df["league"].value_counts())

print("\n=== DELIVERIES BY LEAGUE ===")
print(balls_df["league"].value_counts())

print("\n=== MATCHES BY YEAR ===")
print(matches_df["year"].value_counts().sort_index())

print("\n=== DATA QUALITY ===")

print("Missing batter IDs:", balls_df["striker_id"].isna().sum())
print("Missing bowler IDs:", balls_df["bowler_id"].isna().sum())

print("\nFiles saved to:", OUT)
