import streamlit as st
import requests
from datetime import datetime, timedelta

# --- Config ---
MIN_H2H_MATCHES = 2
DAYS_AHEAD = 3

# --- Dominance Rule Functions ---
def apply_d1(h2h):
    home_wins = sum(1 for m in h2h if m['homeScore']['current'] > m['awayScore']['current'] and m['homeTeam']['id'] == m['winnerTeam']['id'])
    away_wins = sum(1 for m in h2h if m['awayScore']['current'] > m['homeScore']['current'] and m['awayTeam']['id'] == m['winnerTeam']['id'])
    return home_wins > away_wins or away_wins > home_wins

def apply_d2(h2h):
    unbeaten_team = h2h[0]['homeTeam']['id'] if h2h[0]['homeTeam']['id'] == h2h[1]['homeTeam']['id'] else h2h[0]['awayTeam']['id']
    for match in h2h:
        if match['winnerTeam'] and match['winnerTeam']['id'] != unbeaten_team:
            return False
    return len(h2h) >= MIN_H2H_MATCHES

def apply_d4(h2h, current_home_id):
    home_matches = [m for m in h2h if m['homeTeam']['id'] == current_home_id]
    return len(home_matches) >= MIN_H2H_MATCHES and all(m['homeScore']['current'] >= m['awayScore']['current'] for m in home_matches)

def apply_d5(h2h):
    last_team = None
    streak = 0
    for match in h2h:
        winner = match['winnerTeam']
        if not winner:
            break
        if winner['id'] == last_team:
            streak += 1
        else:
            streak = 1
            last_team = winner['id']
    return streak >= 3

# --- Helper Functions ---
def get_upcoming_matches():
    all_matches = []
    for i in range(DAYS_AHEAD):
        date_str = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
        resp = requests.get(url)
        if resp.status_code == 200:
            day_matches = resp.json().get('events', [])
            all_matches.extend(day_matches)
    return all_matches

def get_h2h(home_id, away_id):
    url = f"https://api.sofascore.com/api/v1/event/{home_id}/h2h/{away_id}"
    resp = requests.get(url)
    return resp.json().get('matches', [])

# --- Streamlit UI ---
st.title("⚽ Daily Dominance Filter - Sofascore")
st.write("Filtering matches based on historical dominance and odds")

st.write("\n📅 Loading fixtures...")
upcoming_matches = get_upcoming_matches()

if not upcoming_matches:
    st.warning("No upcoming matches found.")
else:
    count_displayed = 0
    for match in upcoming_matches:
        home = match['homeTeam']
        away = match['awayTeam']
        match_id = match['id']

        try:
            h2h_matches = get_h2h(home['id'], away['id'])
            if len(h2h_matches) < MIN_H2H_MATCHES:
                continue

            rules_triggered = []
            if apply_d1(h2h_matches):
                rules_triggered.append("D1")
            if apply_d2(h2h_matches):
                rules_triggered.append("D2")
            if apply_d4(h2h_matches, home['id']):
                rules_triggered.append("D4")
            if apply_d5(h2h_matches):
                rules_triggered.append("D5")

            if rules_triggered:
                count_displayed += 1
                st.markdown(f"### {home['name']} vs {away['name']}")
                st.markdown(f"- Rules triggered: ✅ {' , '.join(rules_triggered)}")
                st.markdown(f"- Dominance score: **{len(rules_triggered)} / 4**")
                st.markdown("---")

        except Exception as e:
            st.write(f"Error processing match {home['name']} vs {away['name']}: {e}")

    if count_displayed == 0:
        st.warning("⚠️ No dominant matches found based on current criteria.")
