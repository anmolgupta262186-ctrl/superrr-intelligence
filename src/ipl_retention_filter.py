
from pathlib import Path
import pandas as pd

OUT = Path("data/raw/auction2027")
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. RELEASED PLAYERS
# ------------------------------------

released = {
    "SRH": """
        Travis Head, Kamindu Mendis, Jaydev Unadkat,
        Dilshan Madushanka, Onkar Tarmale, Amit Kumar,
        Shivam Mavi, Gerald Coetzee, David Payne
    """,

    "PBKS": """
        Lockie Ferguson, Mitch Owen, Nehal Wadhera,
        Pyla Avinash, Praveen Dubey, Vishal Nishad
    """,

    "DC": """
        Mitchell Starc, Nitish Rana, Abishek Porel,
        Pathum Nissanka, Ben Duckett, Karun Nair,
        Sahil Parakh, Dushmantha Chameera,
        Rehan Ahmed, Ajay Mandal
    """,

    "CSK": """
        MS Dhoni, Prashant Veer, Matthew Short,
        Matt Henry, Zak Foulkes, Aman Khan,
        Kuldip Yadav, Akash Madhwal, Dian Forrester,
        Macneil Noronha, Spencer Johnson
    """,

    "MI": """
        Trent Boult, Deepak Chahar, AM Ghazanfar,
        Atharva Ankolekar, Keshav Maharaj,
        Mohammed Izhar, Danish Malewar,
        Mayank Markande, Mayank Rawat
    """,

    "RR": """
        Adam Milne, Emanjot Singh Chahal, Kuldeep Sen,
        Kwena Maphaka, Ravi Singh, Shimron Hetmyer,
        Tushar Deshpande, Vignesh Puthur, Yudhvir Singh
    """,

    "RCB": """
        Jacob Bethell, Richard Gleeson, Mangesh Yadav,
        Vihaan Malhotra, Satvik Deswal
    """,

    "LSG": """
        Avesh Khan, Wanindu Hasaranga,
        Matthew Breetzke, Naman Tiwari,
        Anrich Nortje, George Linde
    """,

    "KKR": """
        Ajinkya Rahane, Akash Deep,
        Blessing Muzarabani, Luvinith Sisodia,
        Matheesha Pathirana, Mustafizur Rahman,
        Navdeep Saini, Rachin Ravindra,
        Rahul Tripathi, Tejasvi Singh, Umran Malik
    """,

    "GT": """
        Shahrukh Khan, Ishant Sharma, Luke Wood,
        Connor Esterhuizen, Kulwant Khejroliya
    """
}

# ------------------------------------
# 2. RETAINED PLAYERS
# ------------------------------------

retained = {
    "RR": """
        Riyan Parag, Yashasvi Jaiswal,
        Vaibhav Sooryavanshi, Ravindra Jadeja,
        Dhruv Jurel, Jofra Archer, Aman Rao Perala,
        Brijesh Sharma, Nandre Burger, Dasun Shanaka,
        Donovan Ferreira, Lhuan-dre Pretorius,
        Ravi Bishnoi, Sandeep Sharma, Shubham Dubey,
        Sushant Mishra, Yash Punja,
        Mohammed Shami, Manimaran Siddharth
    """,

    "CSK": """
        Sanju Samson, Ruturaj Gaikwad, Ayush Mhatre,
        Dewald Brevis, Urvil Patel, Kartik Sharma,
        Sarfaraz Khan, Anshul Kamboj, Gurjapneet Singh,
        Mukesh Choudhary, Noor Ahmad, Rahul Chahar,
        Jamie Overton, Ramakrishna Ghosh,
        Shivam Dube, Shreyas Gopal, Akeal Hosein,
        Liam Livingstone, Jack Edwards
    """,

    "DC": """
        Ashutosh Sharma, KL Rahul, Sameer Rizvi,
        Tristan Stubbs, David Miller, Prithvi Shaw,
        Mukesh Kumar, Tripurana Vijay, Auqib Nabi,
        Axar Patel, Madhav Tiwari, Vipraj Nigam,
        Rishabh Pant, Zeeshan Ansari
    """,

    "GT": """
        Anuj Rawat, Jos Buttler, Kumar Kushagra,
        Sai Sudharsan, Shubman Gill, Tom Banton,
        Gurnoor Brar, Kagiso Rabada, Mohammed Siraj,
        Arshad Khan, Prasidh Krishna, Sai Kishore,
        Rashid Khan, Ashok Sharma, Glenn Phillips,
        Jayant Yadav, Manav Suthar, Nishant Sindhu,
        Rahul Tewatia, Washington Sundar,
        Jason Holder, Harshal Patel
    """,

    "KKR": """
        Anukul Roy, Angkrish Raghuvanshi,
        Cameron Green, Finn Allen, Harshit Rana,
        Kartik Tyagi, Manish Pandey, Prashant Solanki,
        Ramandeep Singh, Rinku Singh, Rovman Powell,
        Sarthak Ranjan, Saurabh Dubey, Sunil Narine,
        Tim Seifert, Vaibhav Arora, Varun Chakravarthy
    """,

    "LSG": """
        Abdul Samad, Nicholas Pooran, Mukul Choudhary,
        Akshat Raghuwanshi, Josh Inglis, Akash Singh,
        Arjun Tendulkar, Digvesh Rathi, Mayank Yadav,
        Mohsin Khan, Prince Yadav, Aiden Markram,
        Ayush Badoni, Mitchell Marsh, Kuldeep Yadav,
        Sam Curran
    """,

    "MI": """
        Rohit Sharma, Ryan Rickelton,
        Sherfane Rutherford, Suryakumar Yadav,
        Tilak Varma, Quinton de Kock, Ashwani Kumar,
        Jasprit Bumrah, Raghu Sharma, Shardul Thakur,
        Corbin Bosch, Mitchell Santner, Naman Dhir,
        Raj Bawa, Will Jacks, Arshdeep Singh
    """,

    "PBKS": """
        Harnoor Singh Pannu, Prabhsimran Singh,
        Priyansh Arya, Shashank Singh, Shreyas Iyer,
        Vishnu Vinod, Vijaykumar Vyshak,
        Xavier Bartlett, Yash Thakur, Yuzvendra Chahal,
        Ben Dwarshuis, Azmatullah Omarzai,
        Harpreet Brar, Marco Jansen, Marcus Stoinis,
        Musheer Khan, Suryansh Shedge,
        Cooper Connolly, Hardik Pandya
    """,

    "RCB": """
        Devdutt Padikkal, Jitesh Sharma, Phil Salt,
        Rajat Patidar, Tim David, Virat Kohli,
        Jordan Cox, Abhinandan Singh, Bhuvneshwar Kumar,
        Josh Hazlewood, Nuwan Thushara, Rasikh Dar,
        Suyash Sharma, Yash Dayal, Jacob Duffy,
        Vicky Ostwal, Krunal Pandya, Romario Shepherd,
        Venkatesh Iyer, Kanishk Chouhan
    """,

    "SRH": """
        Aniket Verma, Heinrich Klaasen, Ishan Kishan,
        Smaran Ravichandran, Salil Arora, Brydon Carse,
        Eshan Malinga, Pat Cummins, Sakib Hussain,
        Praful Hinge, Abhishek Sharma, Harsh Dubey,
        Nitish Kumar Reddy, Shivang Kumar,
        Krains Fuletra, Khaleel Ahmed, Nathan Ellis
    """
}

# ------------------------------------
# 3. DISPUTED OR INCOMPLETE RECORDS
# ------------------------------------

review = {
    "DC": "Kyle Jamieson, Lungi Ngidi",
    "KKR": "Daksh Kamra",
    "LSG": "Himmat Singh, Arshin Kulkarni, Shahbaz Ahmed",
    "MI": "Robin Minz, Krish Bhagat, Mahipal Lomror, Ruchit Ahir",
    "RCB": "Swapnil Singh",
    "GT": "Prithviraj Yarra"
}

# ------------------------------------
# 4. RETIRED OR UNAVAILABLE PLAYERS
# ------------------------------------

unavailable = {
    "MS Dhoni": "Retired",
    "Ajinkya Rahane": "Retired",
    "Travis Head": "Withdrawn",
    "Mitchell Starc": "Withdrawn"
}

# ------------------------------------
# 5. CREATE MASTER DATASET
# ------------------------------------

SOURCE = (
    "https://www.wisden.com/series/ipl-2027/"
    "cricket-news/ipl-2027-retention-list-full-list-retained-released"
    " | "
    "https://timesofindia.indiatimes.com/sports/cricket/"
    "news/ipl-2027-retention-list-full-list-of-retained-and-"
    "released-players-remaining-purse-of-all-10-teams/"
    "articleshow/135926264.cms"
)

RR_SOURCE = (
    "https://www.rajasthanroyals.com/latest-news/"
    "ipl-2027-rr-players-retention-list-retained-released"
)

rows = []

for status, teams in [
    ("Released", released),
    ("Retained", retained),
    ("Needs review", review)
]:

    for franchise, names in teams.items():

        for name in names.split(","):

            name = name.strip()

            if not name:
                continue

            rows.append({
                "player_name": name,
                "franchise": franchise,
                "status": unavailable.get(name, status),
                "source": RR_SOURCE if franchise == "RR"
                          else SOURCE,
                "verification_date": "2026-11-17"
            })

df = pd.DataFrame(rows)

# ------------------------------------
# 6. VALIDATE AND SAVE
# ------------------------------------

duplicates = df[
    df["player_name"].duplicated(keep=False)
]

if not duplicates.empty:
    print("\nWARNING: Duplicate player names")
    print(duplicates.to_string(index=False))
    raise SystemExit("Resolve duplicate records first.")

df.to_csv(
    OUT / "retention_list.csv",
    index=False
)

df[df["franchise"] == "RR"].to_csv(
    OUT / "rr_squad_2027.csv",
    index=False
)

print("\n=== IPL 2027 MASTER DATASET ===")

print("Total player records:", len(df))
print("Franchises:", df["franchise"].nunique())

print("\n=== PLAYER STATUS ===")
print(df["status"].value_counts())

print("\n=== FRANCHISE-WISE STATUS ===")
print(pd.crosstab(df["franchise"], df["status"]))

print("\n=== CURRENT RR SQUAD ===")

print(
    df[
        (df["franchise"] == "RR")
        & (df["status"] == "Retained")
    ]["player_name"].to_string(index=False)
)

print("\nSaved files to:", OUT)
