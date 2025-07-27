import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import asyncio
import aiohttp
import plotly.express as px

# Configure API
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"  # Your API-Football key
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# --- Data Fetching Functions ---
async def fetch_fixtures(session, date):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"date": date}
    async with session.get(url, headers=HEADERS, params=params) as response:
        return await response.json()

async def fetch_h2h(session, team1_id, team2_id, last=10):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"
    params = {"h2h": f"{team1_id}-{team2_id}", "last": last}
    async with session.get(url, headers=HEADERS, params=params) as response:
        return await response.json()

async def fetch_lineup_injuries(session, fixture_id):
    lineup_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/lineups"
    injuries_url = "https://api-football-v1.p.rapidapi.com/v3/injuries"
    params = {"fixture": fixture_id}
    
    async with session.get(lineup_url, headers=HEADERS, params=params) as response:
        lineup = await response.json()
    
    async with session.get(injuries_url, headers=HEADERS, params=params) as response:
        injuries = await response.json()
    
    return lineup, injuries

# --- Dominance Rules ---
def apply_dominance_rules(h2h_data, home_id, away_id, venue):
    if not h2h_data.get("response"):
        return None
    
    matches = h2h_data["response"]
    home_wins = 0
    draws = 0
    home_venue_results = []
    away_venue_results = []
    
    for match in matches:
        if match["teams"]["home"]["id"] == home_id:
            if match["teams"]["home"]["winner"]:
                home_wins += 1
                home_venue_results.append("win")
            elif match["teams"]["away"]["winner"]:
                home_venue_results.append("loss")
            else:
                draws += 1
                home_venue_results.append("draw")
        else:
            if match["teams"]["away"]["winner"]:
                home_wins += 1
                away_venue_results.append("win")
            elif match["teams"]["home"]["winner"]:
                away_venue_results.append("loss")
            else:
                draws += 1
                away_venue_results.append("draw")
    
    total_matches = len(matches)
    win_rate = (home_wins / total_matches) * 100 if total_matches > 0 else 0
    
    # Rule D1: Win ≥70% of H2H
    d1 = win_rate >= 70
    
    # Rule D2: Unbeaten in last N (≥2) matches
    last_n = min(5, total_matches)
    last_n_results = []
    for match in matches[:last_n]:
        if match["teams"]["home"]["id"] == home_id:
            last_n_results.append("win" if match["teams"]["home"]["winner"] else "draw" if match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"] else "loss")
        else:
            last_n_results.append("win" if match["teams"]["away"]["winner"] else "draw" if match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"] else "loss")
    d2 = all(result in ["win", "draw"] for result in last_n_results) and last_n >= 2
    
    # Rule D3: Home/Away unbeaten
    if venue == "home":
        d3 = all(result in ["win", "draw"] for result in home_venue_results) if home_venue_results else False
    else:
        d3 = all(result in ["win", "draw"] for result in away_venue_results) if away_venue_results else False
    
    # Rule D4: Trend (≥3 wins in last 5)
    d4 = home_wins >= 3 if total_matches >= 5 else False
    
    return {
        "D1": d1, "D2": d2, "D3": d3, "D4": d4,
        "Win Rate": win_rate,
        "Last 5 Results": last_n_results[:5]
    }

# --- Streamlit App ---
st.set_page_config(layout="wide", page_title="H2H Dominance Analyzer")
st.title("⚽ H2H Dominance Analyzer")

# Sidebar controls
st.sidebar.header("Settings")
selected_dates = st.sidebar.multiselect(
    "Select dates",
    [(datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)],
    default=[(datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
)

selected_rules = st.sidebar.multiselect(
    "Dominance Rules",
    ["D1 (Win ≥70%)", "D2 (Unbeaten streak)", "D3 (Home/Away dominance)", "D4 (Trend)"],
    default=["D1 (Win ≥70%)", "D2 (Unbeaten streak)"]
)

min_h2h_matches = st.sidebar.slider("Minimum H2H matches", 2, 10, 5)

# Main analysis
if st.sidebar.button("Analyze Fixtures"):
    async def main():
        async with aiohttp.ClientSession() as session:
            # Fetch fixtures
            all_fixtures = []
            for date in selected_dates:
                fixtures = await fetch_fixtures(session, date)
                if fixtures.get("response"):
                    all_fixtures.extend(fixtures["response"])
            
            # Process fixtures
            results = []
            for fixture in all_fixtures[:30]:  # Limit to 30 for demo
                home_team = fixture["teams"]["home"]["name"]
                away_team = fixture["teams"]["away"]["name"]
                home_id = fixture["teams"]["home"]["id"]
                away_id = fixture["teams"]["away"]["id"]
                venue = "home" if fixture["teams"]["home"]["id"] == home_id else "away"
                
                # Fetch H2H
                h2h_data = await fetch_h2h(session, home_id, away_id, min_h2h_matches)
                dominance = apply_dominance_rules(h2h_data, home_id, away_id, venue)
                
                if dominance and any(dominance[rule.split(" ")[0]] for rule in selected_rules):
                    lineup, injuries = await fetch_lineup_injuries(session, fixture["fixture"]["id"])
                    
                    # Prepare result
                    result = {
                        "Match": f"{home_team} vs {away_team}",
                        "Date": datetime.strptime(fixture["fixture"]["date"][:10], "%Y-%m-%d").strftime("%d %b"),
                        "League": fixture["league"]["name"],
                        "Venue": venue.capitalize(),
                        "Win Rate": f"{dominance['Win Rate']:.1f}%",
                        "Lineup": "✅" if lineup.get("response") else "❌",
                        "Injuries": len(injuries.get("response", [])),
                        "Last 5 Results": ", ".join(dominance["Last 5 Results"])
                    }
                    
                    # Add rule-specific columns
                    for rule in selected_rules:
                        result[rule] = "✅" if dominance[rule.split(" ")[0]] else "❌"
                    
                    results.append(result)
            
            # Display results
            if results:
                df = pd.DataFrame(results)
                df = df[["Match", "Date", "League", "Venue", "Win Rate"] + selected_rules + ["Last 5 Results", "Lineup", "Injuries"]]
                
                # Visualize
                st.success(f"Found {len(results)} dominant matches!")
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Win rate distribution chart
                fig = px.histogram(df, x="Win Rate", title="Win Rate Distribution of Dominant Teams")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No dominant matches found for selected criteria!")
    
    asyncio.run(main())

# --- Instructions ---
st.sidebar.markdown("""
### How to Use
1. Select dates (default: next 3 days)
2. Choose dominance rules to apply
3. Set minimum H2H matches (2-10)
4. Click "Analyze Fixtures"

### Dominance Rules
- **D1**: Team wins ≥70% of all H2H matches
- **D2**: Unbeaten in last N matches (N≥2)
- **D3**: Unbeaten at current venue (home/away)
- **D4**: Wins ≥3 of last 5 H2H matches
""")
