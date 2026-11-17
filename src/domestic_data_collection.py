import requests
from bs4 import BeautifulSoup
import re

matches = {
    "TNPL": 119279,
    "DPL": 129997,
    "RPL": 80481
}

keywords = [
    "commentaryList",
    "commentary",
    "ballNbr",
    "overNumber",
    "batsman",
    "bowler",
    "inningsId",
    "matchId",
    "batTeam",
    "commText"
]

for league, match_id in matches.items():

    url = (
        "https://www.cricbuzz.com/"
        f"live-cricket-full-commentary/{match_id}"
    )

    print("\n" + "=" * 60)
    print("League:", league)

    try:
        response = requests.get(url, timeout=30)

        soup = BeautifulSoup(
            response.text, "html.parser"
        )

        print("Status:", response.status_code)
        print("Page title:", soup.title.get_text()
              if soup.title else "Unknown")

        scripts = soup.find_all("script")

        script_text = "\n".join(
            script.get_text() for script in scripts
        )

        print("\nEmbedded data indicators:")

        for keyword in keywords:

            count = len(re.findall(
                re.escape(keyword),
                script_text,
                re.IGNORECASE
            ))

            print(keyword, ":", count)

    except requests.RequestException as e:
        print("Error:", e)