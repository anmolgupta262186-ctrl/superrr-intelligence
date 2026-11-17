
from pathlib import Path
import pandas as pd
import re

BASE = Path("data/processed/auction2027")
OUT = BASE / "strict_final"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "final_selection/integrated_recruitment_pool.csv",
    low_memory=False
)

retention = pd.read_csv(
    "data/raw/auction2027/retention_list.csv"
)

df = df.copy()

def key(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())

# 1. Name corrections

aliases = {
    "SN Netravalkar": "Saurabh Netravalkar",
    "LA Procter": "Luke Procter",
    "BA Raine": "Ben Raine",
    "TS Rogers": "Tom Rogers",
    "BWM Mike": "Ben Mike",
    "CP Wood": "Chris Wood",
    "JMR Taylor": "Jack Taylor",
    "WL Madsen": "Wayne Madsen",
    "JL du Plooy": "Leus du Plooy",
    "PWA Mulder": "Wiaan Mulder",
    "L Gregory": "Lewis Gregory",
    "FJ Klaassen": "Fred Klaassen",
    "WCF Smeed": "Will Smeed",
    "CT Bancroft": "Cameron Bancroft",
    "M Shahrukh Khan": "Shahrukh Khan",
    "VG Arora": "Vaibhav Arora",
    "SA Yadav": "Suryakumar Yadav",
    "R Tewatia": "Rahul Tewatia"
}

df["canonical_name"] = df["canonical_name"].replace(aliases)
df["name_key"] = df["canonical_name"].apply(key)

retention["name_key"] = retention[
    "player_name"
].replace(aliases).apply(key)

# 2. Existing franchise contracts

contracted = set(
    retention.loc[
        retention["status"].str.lower().isin([
            "retained", "traded", "retired", "withdrawn"
        ]), "name_key"
    ]
)

# Additional confirmed exclusions

additional_contracts = [
    "Shubman Gill", "Sai Sudharsan",
    "Shivam Dube", "David Miller",
    "Shashank Singh", "Suryakumar Yadav",
    "Rinku Singh", "Hardik Pandya",
    "Prasidh Krishna", "Patrick Cummins",
    "Pat Cummins", "Vaibhav Arora",
    "Khaleel Ahmed", "Rahul Tewatia",
    "Sam Curran", "Suryansh Shedge",
    "Swapnil Singh", "Jason Holder"
]

rr_squad = [
    "Riyan Parag", "Yashasvi Jaiswal",
    "Vaibhav Sooryavanshi", "Ravindra Jadeja",
    "Dhruv Jurel", "Jofra Archer",
    "Aman Rao Perala", "Brijesh Sharma",
    "Nandre Burger", "Dasun Shanaka",
    "Donovan Ferreira", "Lhuan-dre Pretorius",
    "Ravi Bishnoi", "Sandeep Sharma",
    "Shubham Dubey", "Sushant Mishra",
    "Yash Punja", "Mohammed Shami",
    "Manimaran Siddharth"
]

contracted.update(map(key, additional_contracts))
contracted.update(map(key, rr_squad))

# 3. IPL recruitment eligibility exclusions

pakistani_players = [
    "Babar Azam", "Mohammad Rizwan",
    "Shaheen Afridi", "Shaheen Shah Afridi",
    "Sufiyan Muqeem", "Haris Rauf",
    "Naseem Shah", "Shadab Khan",
    "Fakhar Zaman", "Mohammad Amir",
    "Usama Mir", "Imad Wasim",
    "Iftikhar Ahmed", "Mohammad Nawaz",
    "Salman Ali Agha", "Abrar Ahmed",
    "Mohammad Haris", "Saim Ayub",
    "Hasan Ali", "Mohammad Hasnain",
    "Mohammad Wasim", "Azam Khan",
    "Shoaib Malik", "Asif Ali",
    "Khushdil Shah", "Usman Tariq",
    "Faheem Ashraf", "Hussain Talat",
    "Aamer Jamal", "Abbas Afridi",
    "Zaman Khan", "Mohammad Abbas",
    "Shan Masood", "Saud Shakeel",
    "Mohammad Irfan", "Mohammad Hafeez"
]

excluded_keys = set(map(key, pakistani_players))

unavailable = [
    "MS Dhoni", "Ajinkya Rahane",
    "Irfan Pathan", "Yusuf Pathan",
    "Dhawal Kulkarni", "Saurabh Tiwary",
    "Travis Head", "Mitchell Starc"
]

excluded_keys.update(map(key, unavailable))

# 4. Confirmed released players
# Release does not guarantee auction registration.

confirmed_released = [
    "Avesh Khan", "Trent Boult",
    "Akash Madhwal", "Anrich Nortje",
    "Dushmantha Chameera", "David Payne",
    "Jaydev Unadkat", "Nitish Rana",
    "Shahrukh Khan", "Atharva Ankolekar",
    "Shimron Hetmyer", "Tushar Deshpande",
    "Kuldeep Sen", "Adam Milne",
    "Kwena Maphaka", "Vignesh Puthur",
    "Matthew Short", "Matt Henry",
    "Deepak Chahar", "Mayank Markande",
    "Rehan Ahmed", "Ben Duckett",
    "Pathum Nissanka", "Karun Nair",
    "Nehal Wadhera", "Lockie Ferguson",
    "Mitch Owen", "Jacob Bethell",
    "Richard Gleeson", "Gerald Coetzee",
    "Kamindu Mendis", "Shivam Mavi",
    "Wanindu Hasaranga", "George Linde",
    "Matthew Breetzke", "Rachin Ravindra",
    "Matheesha Pathirana", "Umran Malik",
    "Rahul Tripathi", "Navdeep Saini",
    "Akash Deep", "Mustafizur Rahman",
    "Blessing Muzarabani", "Luke Wood"
]

released_keys = set(map(key, confirmed_released))

# 5. Strict separation of candidates

df["auction_status"] = "Verification pending"

df.loc[
    df["name_key"].isin(released_keys),
    "auction_status"
] = "Confirmed released"

df.loc[
    df["name_key"].isin(contracted),
    "auction_status"
] = "Excluded - Existing contract or unavailable"

df.loc[
    df["name_key"].isin(excluded_keys),
    "auction_status"
] = "Excluded - Eligibility or availability"

# Conflicting records must be reviewed

conflicts = contracted & released_keys

df.loc[
    df["name_key"].isin(conflicts)
    & ~df["name_key"].isin(excluded_keys),
    "auction_status"
] = "Hold - Conflicting retention records"

# 6. RR squad priorities

priorities = {
    "Death Bowler": 100,
    "Middle Order Batter": 95,
    "Finisher": 95,
    "Backup Fast Bowler": 80,
    "Powerplay Bowler": 70,
    "Batting All-rounder": 65,
    "Bowling All-rounder": 55,
    "Middle Over Bowler": 40,
    "Backup Wicketkeeper": 30,
    "Backup Opener": 20
}

df["squad_priority"] = df[
    "target_role"
].map(priorities)

df["frs"] = (
    0.40 * df["pri"]
    + 0.40 * df["whi"]
    + 0.20 * df["squad_priority"]
)

# 7. Evidence quality filter

qualified = df[
    df["frs"].notna()
    & df["pressure_signal"].eq("Positive")
    & ~df["historical_only"].fillna(False)
].copy()

released = qualified[
    qualified["auction_status"] == "Confirmed released"
].copy()

pending = qualified[
    qualified["auction_status"] == "Verification pending"
].copy()

excluded = df[
    df["auction_status"].str.startswith("Excluded")
].copy()

# 8. Save complete results

df.to_csv(OUT / "complete_screening.csv", index=False)
released.to_csv(OUT / "released_candidates.csv", index=False)
pending.to_csv(OUT / "verification_pending.csv", index=False)
excluded.to_csv(OUT / "excluded_players.csv", index=False)

# 9. Generate auction ranking previews
# Keep Normal and Moderate baselines separate.

for baseline in ["Normal", "Moderate"]:

    for skill in ["Batting", "Bowling"]:

        pool = released[
            (released["skill"] == skill)
            & (released["baseline_category"] == baseline)
        ].copy()

        pool = pool.sort_values(
            ["frs", "balls_pressure"],
            ascending=False
        )

        top = pool.drop_duplicates("name_key").head(10)

        top.to_csv(
            OUT / f"top10_{skill.lower()}_{baseline.lower()}.csv",
            index=False
        )

        print(f"\n=== {skill.upper()} | {baseline} ===")

        print(top[[
            "canonical_name", "target_role",
            "pri", "whi", "squad_priority", "frs"
        ]].round(2).to_string(index=False))

# 10. Verification queue for domestic and overseas talent

watchlist = pending.sort_values(
    ["frs", "balls_pressure"],
    ascending=False
).drop_duplicates(["name_key", "skill", "target_role"])

watchlist.to_csv(
    OUT / "talent_verification_watchlist.csv",
    index=False
)

print("\n=== FINAL SUMMARY ===")

for status, group in df.groupby("auction_status"):
    print(status, ":", group["name_key"].nunique())

print("\nQualified released prospects:",
      released["name_key"].nunique())

print("Qualified unverified prospects:",
      pending["name_key"].nunique())

print("\nResults saved to:", OUT)
