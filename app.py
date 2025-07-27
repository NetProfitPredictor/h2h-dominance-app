import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
from dateutil import parser
import json

# API Football configuration
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

# Streamlit page configuration for mobile-friendly layout
st.set_page_config(
    page_title="H2H Dominance Football App",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to fetch fixtures for the current day
def fetch_fixtures(date_str):
    url = f"{API_URL}/fixtures?date={date_str}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get('response', [])
    else:
        st.error("Error fetching fixtures. Please try again later.")
        return []

# Function to fetch H2H data between two teams
def fetch_h2h(team1_id, team2_id):
    url = f"{API_URL}/fixtures/headtohead?h2h={team1_id}-{team2_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get('response', [])
    else:
        return []

# Function to fetch lineup and injury info
def fetch_lineup_and_injuries(fixture_id):
    url = f"{API_URL}/fixtures/lineups?fixture={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    lineup_data = response.json().get('response', []) if response.status_code == 200 else []

    url = f"{API_URL}/injuries?fixture={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    injury_data = response.json().get('response', []) if response.status_code == 200 else []

    return lineup_data, injury_data

# Function to analyze H2H dominance
def analyze_h2h(h2h_matches, home_team_id, away_team_id, venue):
    if len(h2h_matches) < 2:
        return []

    dominance_results = []
    total_matches = len(h2h_matches)
    home_wins = sum(1 for match in h2h_matches if match['teams']['home']['id'] == home_team_id and match['teams']['home']['winner'] == True)
    away_wins = sum(1 for match in h2h_matches if match['teams']['away']['id'] == home_team_id and match['teams']['away']['winner'] == True)
    total_home_team_wins = home_wins + away_wins

    # D1: Win majority (≥70% of H2H matches)
    win_percentage = (total_home_team_wins / total_matches) * 100 if total_matches > 0 else 0
    d1_satisfied = win_percentage >= 70 and total_matches >= 2

    # D2: Unbeaten streak in last N matches (N≥2)
    last_n_matches = h2h_matches[-2:] if len(h2h_matches) >= 2 else h2h_matches
    d2_satisfied = all(
        match['teams']['home']['winner'] != False if match['teams']['home']['id'] == home_team_id
        else match['teams']['away']['winner'] != False for match in last_n_matches
    ) and len(last_n_matches) >= 2

    # D3: Unbeaten at home/away venue
    venue_matches = [
        match for match in h2h_matches
        if (venue == 'home' and match['teams']['home']['id'] == home_team_id) or
           (venue == 'away' and match['teams']['away']['id'] == home_team_id)
    ]
    d3_satisfied = all(
        match['teams']['home']['winner'] != False if match['teams']['home']['id'] == home_team_id
        else match['teams']['away']['winner'] != False for match in venue_matches
    ) and len(venue_matches) > 0

    # D4: Minor loss (≤4 losses in 12+ matches)
    losses = sum(1 for match in h2h_matches if
                 (match['teams']['home']['id'] == home_team_id and match['teams']['home']['winner'] == False) or
                 (match['teams']['away']['id'] == home_team_id and match['teams']['away']['winner'] == False))
    d4_satisfied = losses <= 4 and total_matches >= 12

    if d1_satisfied:
        dominance_results.append("D1: Win majority (≥70%)")
    if d2_satisfied:
        dominance_results.append("D2: Unbeaten in last 2+ matches")
    if d3_satisfied:
        dominance_results.append(f"D3: Unbeaten at {venue}")
    if d4_satisfied:
        dominance_results.append("D4: ≤4 losses in 12+ matches")

    return dominance_results

# Main app
def main():
    st.title("Football H2H Dominance Analyzer")
    st.markdown("Analyze today's football fixtures for head-to-head dominance.")

    # Date selection (default to today)
    today = date.today().strftime("%Y-%m-%d")
    st.write(f"Fetching fixtures for: {today}")

    # Fetch fixtures
    fixtures = fetch_fixtures(today)
    if not fixtures:
        st.warning("No fixtures found for today.")
        return

    # Process each fixture
    results = []
    for fixture in fixtures:
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        home_team_id = fixture['teams']['home']['id']
        away_team_id = fixture['teams']['away']['id']
        fixture_id = fixture['fixture']['id']
        venue = fixture['fixture']['venue']['name']

        # Fetch H2H data
        h2h_matches = fetch_h2h(home_team_id, away_team_id)
        if len(h2h_matches) < 2:
            continue

        # Analyze dominance for home team
        home_dominance = analyze_h2h(h2h_matches, home_team_id, away_team_id, 'home')
        away_dominance = analyze_h2h(h2h_matches, away_team_id, home_team_id, 'away')

        # Fetch lineup and injuries
        lineup_data, injury_data = fetch_lineup_and_injuries(fixture_id)

        # Prepare result
        if home_dominance or away_dominance:
            results.append({
                'match': f"{home_team} vs {away_team}",
                'venue': venue,
                'home_dominance': home_dominance,
                'away_dominance': away_dominance,
                'lineup': lineup_data,
                'injuries': injury_data
            })

    # Display results
    if results:
        st.subheader("Matches with H2H Dominance")
        for result in results:
            with st.expander(f"{result['match']} at {result['venue']}"):
                if result['home_dominance']:
                    st.write(f"**{result['match'].split(' vs ')[0]} Dominance**: {', '.join(result['home_dominance'])}")
                if result['away_dominance']:
                    st.write(f"**{result['match'].split(' vs ')[1]} Dominance**: {', '.join(result['away_dominance'])}")
                
                # Display lineup
                st.write("**Lineups**")
                if result['lineup']:
                    for team in result['lineup']:
                        team_name = team['team']['name']
                        formation = team.get('formation', 'N/A')
                        players = [player['player']['name'] for player in team['startXI']]
                        st.write(f"{team_name} (Formation: {formation}): {', '.join(players)}")
                else:
                    st.write("Lineup data not available.")

                # Display injuries
                st.write("**Injuries**")
                if result['injuries']:
                    for injury in result['injuries']:
                        player = injury['player']['name']
                        reason = injury.get('reason', 'N/A')
                        st.write(f"{player}: {reason}")
                else:
                    st.write("No injury data available.")
    else:
        st.info("No matches meet the dominance criteria today.")

if __name__ == "__main__":
    main()
