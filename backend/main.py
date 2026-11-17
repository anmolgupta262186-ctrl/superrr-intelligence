
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
import json

app = FastAPI(
    title="SupeRR Intelligence",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_methods=["*"],
    allow_headers=["*"]
)

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"


def load_csv(path):
    file = DATA / path

    if not file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {path}"
        )

    df = pd.read_csv(file, low_memory=False)

    return json.loads(
        df.to_json(orient="records")
    )


@app.get("/")
def home():
    return {
        "platform": "SupeRR Intelligence",
        "status": "Backend running"
    }


@app.get("/api/rankings/batters")
def batters():

    return recruitment_rankings("Batting")


@app.get("/api/rankings/bowlers")
def bowlers():
    return recruitment_rankings("Bowling")


@app.get("/api/rr/weaknesses")
def weaknesses():
    return load_csv(
        "auction2027/rr_squad_requirements.csv"
    )


@app.get("/api/auction/candidates")
def candidates():
    return load_csv(
        "auction2027/strict_final/released_candidates.csv"
    )


@app.get("/api/auction/watchlist")
def watchlist():
    return load_csv(
        "auction2027/strict_final/talent_verification_watchlist.csv"
    )


@app.get("/api/players")
def players():
    return load_csv(
        "auction2027/final_selection/integrated_recruitment_pool.csv"
    )


def recruitment_rankings(skill):

    base = DATA / "auction2027/strict_final"

    df = pd.concat([
        pd.read_csv(base / "released_candidates.csv"),
        pd.read_csv(base / "talent_verification_watchlist.csv")
    ], ignore_index=True)

    selections = {
        "Batting": [
            ("Sean Dickson", "England", "Moderate", "Middle Order Batter"),
            ("Sam Billings", "England", "Normal", "Middle Order Batter"),
            ("James Fuller", "England", "Moderate", "Finisher"),
            ("Andries Gous", "USA", "Normal", "Middle Order Batter"),
            ("Dan Lawrence", "England", "Normal", "Middle Order Batter"),
            ("Sam Hain", "England", "Normal", "Finisher"),
            ("Ryan Burl", "Zimbabwe", "Normal", "Middle Order Batter"),
            ("Jack Taylor", "England", "Moderate", "Middle Order Batter"),
            ("Ricky Bhui", "India", "Normal", "Middle Order Batter"),
            ("Tom Curran", "England", "Moderate", "Finisher")
        ],

        "Bowling": [
            ("Avesh Khan", "India", "Normal", "Death Bowler"),
            ("Trent Boult", "New Zealand", "Moderate", "Death Bowler"),
            ("Luke Procter", "England", "Normal", "Death Bowler"),
            ("Shadley van Schalkwyk", "USA", "Normal", "Death Bowler"),
            ("Saurabh Netravalkar", "USA", "Moderate", "Death Bowler"),
            ("Dushmantha Chameera", "Sri Lanka", "Normal", "Death Bowler"),
            ("Nathan McAndrew", "Australia", "Moderate", "Death Bowler"),
            ("Ben Mike", "England", "Normal", "Death Bowler"),
            ("Chris Wood", "England", "Moderate", "Death Bowler"),
            ("Tom Rogers", "Australia", "Moderate", "Death Bowler")
        ]
    }

    impacts = {
        "Middle Order Batter": "Addresses middle-order instability and scoring under pressure.",
        "Finisher": "Potential to strengthen scoring during the final overs.",
        "Death Bowler": "Potential to improve death-over run control and wicket-taking.",
        "Powerplay Bowler": "Provides early wicket-taking options."
    }

    rows = []

    for rank, (name, country, baseline, role) in enumerate(
        selections[skill], start=1
    ):

        pool = df[
            df["canonical_name"].eq(name)
            & df["skill"].eq(skill)
            & df["baseline_category"].eq(baseline)
            & df["target_role"].eq(role)
            & df["pressure_signal"].eq("Positive")
        ]

        if pool.empty:
            continue

        row = pool.sort_values(
            "frs", ascending=False
        ).iloc[0].to_dict()

        row.update({
            "rank": rank,
            "player_name": name,
            "nationality": country,
            "role": role,
            "impact": impacts.get(role, role),
            "mean_pri": row["pri"],
            "match_format": row.get("competition"),
            "overseas": country != "India"
        })

        row["striker_name" if skill == "Batting"
            else "bowler_name"] = name

        rows.append(row)

    return json.loads(
        pd.DataFrame(rows).to_json(orient="records")
    )
