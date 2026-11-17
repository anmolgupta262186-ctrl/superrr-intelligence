
from pathlib import Path
import pandas as pd
import numpy as np
import re

BASE = Path("data/processed")
AUCTION = BASE / "auction2027"
OUT = AUCTION / "final_selection"

OUT.mkdir(parents=True, exist_ok=True)

# 1. Load integrated evidence

df = pd.read_csv(
    BASE / "domestic/smat/final"
    / "combined_global_domestic_evidence.csv",
    low_memory=False
)

retention = pd.read_csv(
    "data/raw/auction2027/retention_list.csv"
)

# 2. Correct known aliases

aliases = {
    "SA Yadav": "Suryakumar Yadav",
    "R Tewatia": "Rahul Tewatia",
    "VG Arora": "Vaibhav Arora",
    "RK Singh": "Rinku Singh",
    "AR Patel": "Axar Patel",
    "R Parag": "Riyan Parag",
    "S Dube": "Shivam Dube",
    "VR Iyer": "Venkatesh Iyer",
    "SN Thakur": "Shardul Thakur",
    "M Shahrukh Khan": "Shahrukh Khan",
    "C Sakariya": "Chetan Sakariya",
    "LI Meriwala": "Lukman Meriwala",
    "SR Dickson": "Sean Dickson",
    "AGS Gous": "Andries Gous",
    "DW Lawrence": "Dan Lawrence",
    "SR Hain": "Sam Hain",
    "TJ Moores": "Tom Moores",
    "SW Currie": "Scott Currie",
    "N McAndrew": "Nathan McAndrew",
    "JDM Evison": "Joey Evison",
    "PM Siddle": "Peter Siddle",
    "JK Fuller": "James Fuller",
    "TK Curran": "Tom Curran",
    "HWR Cartwright": "Hilton Cartwright",
    "SC van Schalkwyk": "Shadley van Schalkwyk",
    "AS Rajpoot": "Ankit Rajpoot",
    "SS Tiwary": "Saurabh Tiwary",
    "IK Pathan": "Irfan Pathan",
    "YK Pathan": "Yusuf Pathan",
    "DS Kulkarni": "Dhawal Kulkarni",
    "A Mithun": "Abhimanyu Mithun"
}

df["canonical_name"] = df[
    "canonical_name"
].replace(aliases)

def key(name):
    return re.sub(
        r"[^a-z0-9]", "", str(name).lower()
    )

df["name_key"] = df["canonical_name"].apply(key)

retention["name_key"] = retention[
    "player_name"
].replace(aliases).apply(key)

contracted = set(
    retention[
        retention["status"].isin(
            ["Retained", "Traded", "Retired", "Withdrawn"]
        )
    ]["name_key"]
)

released = set(
    retention[
        retention["status"] == "Released"
    ]["name_key"]
)

# 3. Additional manual review queue

review_names = [
    "Irfan Pathan", "Yusuf Pathan",
    "Saurabh Tiwary", "Dhawal Kulkarni",
    "Abhimanyu Mithun", "Ankit Rajpoot",
    "Piyush Chawla", "Sheldon Jackson",
    "Kane Richardson", "Mohammad Amir",
    "Usama Mir", "Mohit Sharma",
    "Dinesh Karthik", "Ambati Rayudu",
    "Imad Wasim", "Usman Tariq"
]

review_keys = {key(n) for n in review_names}

df["selection_status"] = "Availability pending"

df.loc[
    df["name_key"].isin(released),
    "selection_status"
] = "Released - registration pending"

df.loc[
    df["name_key"].isin(review_keys),
    "selection_status"
] = "Hold - Manual verification"

df.loc[
    df["name_key"].isin(contracted),
    "selection_status"
] = "Excluded - Retention registry"

# Preserve earlier exclusions and holds

for col in [
    "qc_status",
    "recruitment_status",
    "final_availability_status"
]:

    status = df[col].fillna("").astype(str)

    df.loc[
        status.str.startswith("Hold")
        | status.str.contains("retention verification",
                              case=False),
        "selection_status"
    ] = "Hold - Previous screening"

    df.loc[
        status.str.startswith("Excluded")
        | status.eq("Existing RR squad"),
        "selection_status"
    ] = "Excluded - Previous screening"

# 4. Preserve data requiring verification

df.to_csv(
    OUT / "complete_integrated_evidence.csv",
    index=False
)

df = df[
    ~df["selection_status"].str.startswith(
        ("Excluded", "Hold")
    )
].copy()

# 5. Evaluate pressure response

def pressure_signal(row):

    if row["skill"] == "Batting":

        first = row.get("sr_improvement")
        second = row.get("dismissal_improvement")

    else:

        first = row.get("economy_improvement")

        if pd.isna(first):
            first = row.get("run_rate_improvement")

        second = row.get("wicket_rate_improvement")

    if pd.isna(first) or pd.isna(second):
        return "Incomplete"

    if first >= 0 and second >= 0:
        if first > 0 or second > 0:
            return "Positive"

    if first < 0 and second < 0:
        return "Negative"

    return "Mixed"


df["pressure_signal"] = df.apply(
    pressure_signal, axis=1
)

df["final_rri"] = (
    0.5 * df["pri"] + 0.5 * df["whi"]
)

df = df[df["final_rri"].notna()].copy()

# 6. Identify domestic evidence

df["historical_only"] = (
    df["recent_evidence"]
    == "Historical evidence only"
)

df["style"] = df["style"].fillna("Unknown")

df["comparison_group"] = (
    df["source"].astype(str)
    + " | "
    + df["competition"].astype(str)
    + " | "
    + df["baseline_category"].astype(str)
    + " | "
    + df["phase"].astype(str)
    + " | "
    + df["batting_role"].fillna("")
    + " | "
    + df["whi_metrics_used"].fillna("Not recorded")
)

# 7. Rank provisional candidates

roles = [
    "Death Bowler",
    "Middle Order Batter",
    "Finisher",
    "Powerplay Bowler",
    "Middle Over Bowler",
    "Backup Opener"
]

shortlists = []

for role in roles:

    for baseline in ["Normal", "Moderate"]:

        data = df[
            (df["target_role"] == role)
            & (df["baseline_category"] == baseline)
            & ~df["historical_only"]
        ].copy()

        if role in ["Death Bowler", "Powerplay Bowler"]:

            data = data[data["style"] != "Spin"]

        data = data.sort_values(
            ["final_rri", "balls_pressure"],
            ascending=False
        )

        data = data.drop_duplicates([
            "name_key", "comparison_group"
        ])

        data["group_rank"] = (
            data.groupby("comparison_group")
            .cumcount() + 1
        )

        top = data[data["group_rank"] <= 10]

        shortlists.append(top)

        filename = (
            baseline + "_" + role
        ).lower().replace(" ", "_")

        top.to_csv(
            OUT / f"integrated_{filename}.csv",
            index=False
        )

        print(f"\n=== {role} | {baseline} ===")

        # Cross-league screening preview only
        preview = top.drop_duplicates("name_key")

        print(preview[[
            "canonical_name",
            "competition",
            "pri", "whi", "final_rri",
            "pressure_signal"
        ]].head(10).round(2).to_string(index=False))

# 8. Save all eligible-for-review prospects

df.to_csv(
    OUT / "integrated_recruitment_pool.csv",
    index=False
)

final = pd.concat(shortlists, ignore_index=True)

final.to_csv(
    OUT / "integrated_role_shortlists.csv",
    index=False
)

print("\n=== FINAL SUMMARY ===")

print("Unique prospects:",
      df["name_key"].nunique())

print("Unique shortlisted prospects:",
      final["name_key"].nunique())

print("\nSaved results to:", OUT)
