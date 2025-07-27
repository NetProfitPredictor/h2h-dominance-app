# app.py
import streamlit as st
import requests
from datetime import datetime, timedelta

# Constants
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Dominance Rules
DOMINANCE_RULES = {
    "D1": "Win >= 70%",
    "D2": "Unbeaten in last N",
    "D3": "Unbeaten Home/Away",
    "D4": "<=4 Losses in 12+"
}

def fetch_fixtures():
    today = datetime.now().date()
    end_date = today + timedelta(days=2)
    url = f"{API_BASE_URL}/fixtures?from={today}&to={end_date}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        st.error("Failed to fetch fixtures from API-Football.")
        return []
    return res.json().get("response", [])

def fetch_h2h(team1_id, team2_id):
    url = f"{API_BASE_URL}/fixtures/headtohead?h2h={team1_id}-{team2_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return res.json().get("response", [])

def fetch_lineups_and_injuries(fixture_id):
    lineup_url = f"{API_BASE_URL}/fixtures/lineups?fixture={fixture_id}"
    injury_url = f"{API_BASE_URL}/injuries?fixture={fixture_id}"
    lineups = requests.get(lineup_url, headers=HEADERS).json().get("response", [])
    injuries = requests.get(injury_url, headers=HEADERS).json().get("response", [])
    return lineups, injuries

def analyze_dominance(h2h_data, home_id, away_id):
    if not h2h_data or len(h2h_data) < 2:
        return []

    rules_satisfied = []
    total_matches = len(h2h_data)
    home_wins = sum(1 for match in h2h_data if match['teams']['home']['id'] == home_id and match['teams']['home'].get('winner') is True)
    away_wins = sum(1 for match in h2h_data if match['teams']['away']['id'] == away_id and match['teams']['away'].get('winner') is True)

    # Rule D1
    if home_wins / total_matches >= 0.7:
        rules_satisfied.append("D1 - Home")
    if away_wins / total_matches >= 0.7:
        rules_satisfied.append("D1 - Away")

    # Rule D2
    recent = h2h_data[:min(5, total_matches)]
    home_unbeaten = all(
        (match['teams']['home']['id'] == home_id and match['teams']['home'].get('winner') is True) or
        (match['teams']['away']['id'] == home_id and match['teams']['away'].get('winner') is True) or
        (match['goals']['home'] == match['goals']['away'])
        for match in recent
    )
    away_unbeaten = all(
        (match['teams']['away']['id'] == away_id and match['teams']['away'].get('winner') is True) or
        (match['teams']['home']['id'] == away_id and match['teams']['home'].get('winner') is True) or
        (match['goals']['home'] == match['goals']['away'])
        for match in recent
    )
    if home_unbeaten:
        rules_satisfied.append("D2 - Home")
    if away_unbeaten:
        rules_satisfied.append("D2 - Away")

    # Rule D3
    home_venue_matches = [m for m in h2h_data if m['teams']['home']['id'] == home_id]
    away_venue_matches = [m for m in h2h_data if m['teams']['away']['id'] == away_id]
    if home_venue_matches and all((m['teams']['home'].get('winner') is True or m['goals']['home'] == m['goals']['away']) for m in home_venue_matches):
        rules_satisfied.append("D3 - Home")
    if away_venue_matches and all((m['teams']['away'].get('winner') is True or m['goals']['home'] == m['goals']['away']) for m in away_venue_matches):
        rules_satisfied.append("D3 - Away")

    # Rule D4
    home_losses = sum(1 for m in h2h_data if (m['teams']['home']['id'] == home_id and m['teams']['home'].get('winner') is False) or
                      (m['teams']['away']['id'] == home_id and m['teams']['away'].get('winner') is False))
    away_losses = sum(1 for m in h2h_data if (m['teams']['away']['id'] == away_id and m['teams']['away'].get('winner') is False) or
                      (m['teams']['home']['id'] == away_id and m['teams']['home'].get('winner') is False))
    if total_matches >= 12 and home_losses <= 4:
        rules_satisfied.append("D4 - Home")
    if total_matches >= 12 and away_losses <= 4:
        rules_satisfied.append("D4 - Away")

    return rules_satisfied

def main():
    st.set_page_config(page_title="H2H Dominance Filter", layout="wide")
    st.title("⚽ H2H Dominance Filter - Next 3 Days")

    fixtures = fetch_fixtures()
    if not fixtures:
        st.warning("No fixtures found or API error.")
        return

    filtered_matches = []
    with st.spinner("Analyzing fixtures..."):
        for match in fixtures:
            fixture_id = match['fixture']['id']
            home = match['teams']['home']
            away = match['teams']['away']

            h2h_data = fetch_h2h(home['id'], away['id'])
            if not h2h_data:
                continue

            dominance = analyze_dominance(h2h_data, home['id'], away['id'])
            if dominance:
                lineups, injuries = fetch_lineups_and_injuries(fixture_id)
                filtered_matches.append({
                    "fixture": match['fixture'],
                    "home": home,
                    "away": away,
                    "dominance": dominance,
                    "lineups": lineups,
                    "injuries": injuries
                })

    for m in filtered_matches:
        st.subheader(f"{m['home']['name']} vs {m['away']['name']}")
        st.write("🧠 Dominance Rules:", m['dominance'])
        st.write("📆 Date:", m['fixture']['date'])
        st.write("📋 Lineups Available:", "Yes" if m['lineups'] else "No")
        st.write("🚑 Injuries:", len(m['injuries']))
        st.markdown("---")

if __name__ == "__main__":
    main()
