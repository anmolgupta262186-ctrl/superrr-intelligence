
import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw/ipl_json")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_matches():
    matches = []

    for file in DATA_DIR.rglob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            info = data["info"]
            teams = info.get("teams", [])

            if "Rajasthan Royals" not in teams:
                continue

            season = str(info.get("season", ""))

            if season not in ["2025", "2026"]:
                continue

            matches.append({
                "match_id": file.stem,
                "season": season,
                "date": info.get("dates", [None])[0],
                "team1": teams[0],
                "team2": teams[1],
                "venue": info.get("venue"),
                "city": info.get("city"),
                "toss_winner": info.get("toss", {}).get("winner"),
                "toss_decision": info.get("toss", {}).get("decision"),
                "winner": info.get("outcome", {}).get("winner"),
                "event": info.get("event", {}).get("name")
            })

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error in {file.name}: {e}")

    return pd.DataFrame(matches)


if __name__ == "__main__":
    df = load_matches()

    df = df.sort_values(["season", "date"])

    output_file = OUTPUT_DIR / "rr_matches_2025_2026.csv"
    df.to_csv(output_file, index=False)

    print("Total RR matches:", len(df))
    print("\nSeason-wise matches:")
    print(df.groupby("season").size())

    print("\nMatch details:")
    print(df[["season", "date", "team1", "team2", "winner"]])

    print("\nSaved to:", output_file)
