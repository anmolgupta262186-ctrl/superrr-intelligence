
from pathlib import Path
import pandas as pd

BASE = Path("data/raw/rr_official")

df = pd.read_csv(BASE / "ball_by_ball.csv")

print("\n=== EXTRAS_2_RUNS DISTRIBUTION ===")
print(df["extras_2_runs"].value_counts().sort_index())

print("\n=== EXTRAS_2_RUNS BY TYPE ===")
print(
    df.groupby(
        ["extras_type", "extras_2_runs"],
        dropna=False
    ).size().to_string()
)

print("\n=== EXTRA RUNS WITH BOUNDARIES ===")
print(
    df[
        (df["extras_2_runs"] > 0) &
        ((df["is_four"]) | (df["is_six"]))
    ].shape[0]
)

print("\n=== NO-BALL RUN PATTERNS ===")
print(
    df[df["extras_type"] == "Overstep"]
    .groupby(["runs", "extras_2_runs"])
    .size()
    .to_string()
)

print("\n=== WIDE RUN PATTERNS ===")
print(
    df[df["extras_type"] == "wide"]
    .groupby(["runs", "extras_2_runs"])
    .size()
    .to_string()
)

print("\n=== MATCHES WITH NONZERO EXTRAS_2 ===")
print(
    df[df["extras_2_runs"] > 0]["match_id"].nunique()
)
