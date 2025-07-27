import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser
import json

# API-Football configuration
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
API_HOST = "api-football-v1.p.rapidapi.com/v3"
BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": API_HOST
}

# Function to fetch fixtures for the next 3 days
def fetch_fixtures():
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?from={start_date}&to={end_date}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if data.get("response"):
            return data["response"]
        return []
    except requests.RequestException as e:
        st.error(f"Error fetching fixtures: {e}")
        return []

# Function to fetch H2H matches between two teams
def fetch_h2h(team1_id, team2_id):
    url = f"{BASE_URL}/fixtures/headtohead?h2h={team1_id}-{team2_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if data.get("response"):
            return data["response"]
        return []
    except requests.RequestException as e:
        st.error(f"Error fetching H2H for teams {team1_id} vs {team2_id}: {e}")
        return []

# Function to fetch lineup and injury info for a fixture
def fetch_lineup_and_injuries(fixture_id):
    url = f"{BASE_URL}/fixtures/players?fixture={fixture_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if data.get("response"):
            return data["response"]
        return []
    except requests.RequestException as e:
        st.error(f"Error fetching lineup/injuries for fixture {fixture_id}: {e}")
        return []

# Analyze H2H dominance rules
def analyze_h2h(h2h_matches, home_team, away_team, venue):
    if len(h2h_matches) < 2:
        return []

    dominance_results = []
    
    # D1: Win majority (≥70% wins)
    home_wins = sum(1 for match in h2h_matches if match["teams"]["home"]["winner"] and match["teams"]["home"]["name"] == home_team)
    away_wins = sum(1 for match in h2h_matches if match["teams"]["away"]["winner"] and match["teams"]["away"]["name"] == away_team)
    total_matches = len(h2h_matches)
    home_win_pct = home_wins / total_matches if total_matches > 0 else 0
    away_win_pct = away_wins / total_matches if total_matches > 0 else 0
    
    if home_win_pct >= 0.7:
        dominance_results.append(f"D1: {home_team} wins {home_win_pct:.0%} of H2H matches")
    if away_win_pct >= 0.7:
        dominance_results.append(f"D1: {away_team} wins {away_win_pct:.0%} of H2H matches")

    # D2: Unbeaten streak in last N matches (N≥2)
    last_n = min(5, len(h2h_matches))  # Check last 5 or fewer matches
    if last_n >= 2:
        recent_matches = h2h_matches[:last_n]
        home_unbeaten = all(
            match["teams"]["home"]["winner"] or match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"]
            for match in recent_matches if match["teams"]["home"]["name"] == home_team
        ) or all(
            match["teams"]["away"]["winner"] or match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"]
            for match in recent_matches if match["teams"]["away"]["name"] == home_team
        )
        away_unbeaten = all(
            match["teams"]["away"]["winner"] or match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"]
            for match in recent_matches if match["teams"]["away"]["name"] == away_team
        ) or all(
            match["teams"]["home"]["winner"] or match["score"]["fulltime"]["home"] == match["score"]["fulltime"]["away"]
            for match in recent_matches if match["teams"]["home"]["name"] == away_team
        )
        if home_unbeaten:
            dominance_results.append(f"D2: {home_team} unbeaten in last {last_n} H2H matches")
        if away_unbeaten:
            dominance_results.append(f"D2: {away_team} unbeaten in last {last_n} H2H matches")

    # D3: Home/Away H2H dominance
    home_venue_matches = [m for m in h2h_matches if m["fixture"]["venue"]["name"] == venue]
    if home_venue_matches:
        home_unbeaten_venue = all(
            m["teams"]["home"]["winner"] or m["score"]["fulltime"]["home"] == m["score"]["fulltime"]["away"]
            for m in home_venue_matches if m["teams"]["home"]["name"] == home_team
        )
        if home_unbeaten_venue:
            dominance_results.append(f"D3: {home_team} unbeaten in H2H matches at {venue}")

    # D4: Trend (consistent wins regardless of form)
    # Simplified: Check if one team has won at least 3 consecutive H2H matches
    consecutive_wins = 0
    last_winner = None
    for match in h2h_matches[:5]:  # Check recent 5 matches
        winner = match["teams"]["home"]["name"] if match["teams"]["home"]["winner"] else (
            match["teams"]["away"]["name"] if match["teams"]["away"]["winner"] else None)
        if winner == last_winner:
            consecutive_wins += 1
        else:
            consecutive_wins = 1
            last_winner = winner
        if consecutive_wins >= 3 and last_winner:
            dominance_results.append(f"D4: {last_winner} consistently beats opponent")
            break

    return dominance_results

# Streamlit app
st.set_page_config(page_title="H2H Dominance Football App", layout="wide")

# Mobile-friendly CSS
st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
        padding: 1rem;
    }
    .match-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #f9f9f9;
    }
    .match-header {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .details {
        font-size: 0.9rem;
        color: #555;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Football H2H Dominance Analyzer")
st.write("Matches satisfying D1, D2, D3, or D4 dominance rules for the next 3 days")

# Fetch fixtures
with st.spinner("Fetching fixtures..."):
    fixtures = fetch_fixtures()

if not fixtures:
    st.warning("No fixtures found for the next 3 days.")
else:
    matches_with_dominance = []
    for fixture in fixtures:
        home_team = fixture["teams"]["home"]["name"]
        away_team = fixture["teams"]["away"]["name"]
        home_team_id = fixture["teams"]["home"]["id"]
        away_team_id = fixture["teams"]["away"]["id"]
        fixture_id = fixture["fixture"]["id"]
        date = parser.parse(fixture["fixture"]["date"]).strftime("%Y-%m-%d %H:%M")
        venue = fixture["fixture"]["venue"]["name"]

        # Fetch H2H data
        h2h_matches = fetch_h2h(home_team_id, away_team_id)
        if len(h2h_matches) >= 2:
            dominance = analyze_h2h(h2h_matches, home_team, away_team, venue)
            if dominance:
                # Fetch lineup and injury info
                lineup_data = fetch_lineup_and_injuries(fixture_id)
                lineup_info = []
                for team_data in lineup_data:
                    team_name = team_data["team"]["name"]
                    players = team_data.get("players", [])
                    injuries = [p["player"]["name"] for p in players if p["player"].get("reason") == "Injured"]
                    lineup = [p["player"]["name"] for p in players if p["player"].get("reason") != "Injured"]
                    lineup_info.append({
                        "team": team_name,
                        "lineup": lineup[:11] if lineup else ["Not available"],
                        "injuries": injuries if injuries else ["None"]
                    })

                matches_with_dominance.append({
                    "match": f"{home_team} vs {away_team}",
                    "date": date,
                    "venue": venue,
                    "dominance": dominance,
                    "lineup": lineup_info
                })

    # Display results
    if matches_with_dominance:
        st.subheader("Matches with H2H Dominance")
        for match in matches_with_dominance:
            with st.container():
                st.markdown(f"""
                    <div class="match-container">
                        <div class="match-header">{match['match']}</div>
                        <div class="details">Date: {match['date']}</div>
                        <div class="details">Venue: {match['venue']}</div>
                        <div class="details">Dominance Rules: {', '.join(match['dominance'])}</div>
                        <div class="details">Lineup & Injuries:</div>
                """, unsafe_allow_html=True)
                for team in match["lineup"]:
                    st.markdown(f"""
                        <div class="details">{team['team']} Lineup: {', '.join(team['lineup'])}</div>
                        <div class="details">{team['team']} Injuries: {', '.join(team['injuries'])}</div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No matches found satisfying the dominance rules.")
