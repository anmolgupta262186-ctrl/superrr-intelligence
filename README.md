# SupeRR Intelligence
### Pressure Analytics & Player Recruitment Platform

An end-to-end cricket analytics and recruitment intelligence platform developed for Rajasthan Royals SupeRR Selector Season 2.

## Project Objective

Identify reliable cricket players under high-pressure situations and recommend potential recruitment targets based on Rajasthan Royals' historical weaknesses, individual player performance and squad requirements.

## Key Features

- Ball-by-ball cricket analytics
- Rajasthan Royals 2025–2026 performance analysis
- Match-state pressure detection
- Domestic and international talent scouting
- Top 10 batter and bowler recommendations
- Individual player scouting profiles
- Normal vs high-pressure performance analysis
- Interactive player comparison
- Auction simulation with budget and overseas slot constraints

## Dataset Coverage

| Dataset | Coverage |
|---|---:|
| RR historical matches | 30 |
| Official RR data pack | 200,999 delivery records |
| External T20 competitions | 9 |
| Expanded SMAT dataset | 695 matches |
| SMAT regulation deliveries | 158,789 |
| Integrated recruitment prospects | 392 |
| Shortlisted prospects | 232 |

Dataset counts represent different analytical stages and may overlap.

## Analytical Methodology

### Pressure Reliability Index (PRI)

Evaluates player performance under pressure relative to baseline performance, considering improvement, consistency, absolute performance and sample reliability.

### Weakness Handling Index (WHI)

Measures a player's ability to address specific Rajasthan Royals performance weaknesses.

### Recruitment Reliability Index (RRI)

RRI = 0.5 × PRI + 0.5 × WHI

### Final Recruitment Score (FRS)

FRS = 0.4 × PRI + 0.4 × WHI + 0.2 × Squad Priority

## Technology Stack

**Frontend:** React.js, Vite, Tailwind CSS, Recharts, Lucide React

**Backend:** FastAPI, Python, Uvicorn

**Data Analytics:** Pandas, NumPy, Cricsheet

## System Architecture

Raw Cricket Data → Data Preprocessing → Pressure Detection → Player Performance Analysis → Recruitment Scoring → FastAPI → React Dashboard

## Run Locally

### Backend

```bash
source .venv/bin/activate
pip install fastapi uvicorn pandas numpy
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

Backend: http://localhost:8000

API Documentation: http://localhost:8000/docs

## Limitations

- Cross-competition scores are not fully calibrated.
- Player availability and auction registration require final verification.
- Historical domestic performances may not reflect current form.
- Official bowling run-control statistics exclude ambiguous extras.
- State-level competition data coverage is limited.
- Auction bids are hypothetical.

## Data Sources

- Rajasthan Royals official hackathon data pack
- Cricsheet
- Cricsheet Player Register

Confidential datasets are excluded from the public repository.

## Developer

Anmol Gupta

Artificial Intelligence and Data Science

Developed for Rajasthan Royals SupeRR Selector Season 2.






