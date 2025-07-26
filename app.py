import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ------------------------ CONFIG ------------------------
DOMINANCE_RULES = ['D1', 'D2', 'D4', 'D5']
MIN_H2H_MATCHES = 4
LOOKAHEAD_DAYS = 3

# ------------------------ APP ------------------------
st.set_page_config(page_title="⚽ Daily Dominance Filter", layout="wide")
st.title("⚽ Daily Dominance Filter - Sofascore")
st.markdown("Filtering matches based on historical dominance and odds")

# ------------------------ UTILITIES ------------------------
def fetch_fixtures():
    today = datetime.utcnow().date()
    to_date = today + timedelta(days=LOOKAHEAD_DAYS)
    fixtures = []
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}/{to_date}"
    try:
        response = requests.get(url)
        data = response.json()
        for event in data.get("events", []):
            home = event['homeTeam']['name']
            away = event['awayTeam']['name']
            start = datetime.utcfromtimestamp(event['startTimestamp']).strftime('%Y-%m-%d %H:%M')
            fixtures.append({
                'id': event['id'],
                'home': home,
                'away': away,
                'start_time': start
            })
    except:
        st.error("⚠️ Could not fetch fixtures from Sofascore.")
    return fixtures

def fetch_h2h(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/h2h"
    try:
        response = requests.get(url)
        h2h_matches = response.json().get('matches', [])
        return h2h_matches
    except:
        return []

def apply_dominance_rules(home, away, h2h_matches):
    stats = {'D1': False, 'D2': False, 'D4': False, 'D5': False, 'rules_matched': []}
    if len(h2h_matches) < MIN_H2H_MATCHES:
        return stats

    home_wins, away_wins, draws = 0, 0, 0
    unbeaten_side = None
    win_streak = None
    home_h2h = []

    for match in h2h_matches:
        h = match['homeTeam']['name']
        a = match['awayTeam']['name']
        winner = match['winnerCode']
        if winner == 1:
            win = h
        elif winner == 2:
            win = a
        else:
            win = 'draw'

        if win == home:
            home_wins += 1
        elif win == away:
            away_wins += 1
        else:
            draws += 1

        if h == home:
            home_h2h.append((win, 'home'))
        elif a == home:
            home_h2h.append((win, 'away'))

    # D1: Win Majority
    if home_wins > away_wins:
        stats['D1'] = True
        stats['rules_matched'].append('D1')

    # D2: Unbeaten Streak (last N all win/draw)
    recent = h2h_matches[:MIN_H2H_MATCHES]
    unbeaten = True
    for match in recent:
        h = match['homeTeam']['name']
        a = match['awayTeam']['name']
        winner = match['winnerCode']
        if home == h:
            result = 1 if winner == 1 else (0 if winner == 0 else -1)
        elif home == a:
            result = 1 if winner == 2 else (0 if winner == 0 else -1)
        else:
            result = -1
        if result == -1:
            unbeaten = False
            break
    if unbeaten:
        stats['D2'] = True
        stats['rules_matched'].append('D2')

    # D4: Home/Away H2H dominance
    home_side_wins = sum(1 for win, side in home_h2h if win == home)
    if home_side_wins >= 3:
        stats['D4'] = True
        stats['rules_matched'].append('D4')

    # D5: Winning streak (3+)
    streak = 0
    for match in h2h_matches:
        h = match['homeTeam']['name']
        a = match['awayTeam']['name']
        winner = match['winnerCode']
        if home == h and winner == 1:
            streak += 1
        elif home == a and winner == 2:
            streak += 1
        else:
            break
    if streak >= 3:
        stats['D5'] = True
        stats['rules_matched'].append('D5')

    return stats

# ------------------------ MAIN ------------------------
st.markdown("\n📅 Loading fixtures...")
fixtures = fetch_fixtures()
results = []

for fixture in fixtures:
    h2h = fetch_h2h(fixture['id'])
    if not h2h:
        continue
    dom_stats = apply_dominance_rules(fixture['home'], fixture['away'], h2h)
    if len(dom_stats['rules_matched']) > 0:
        results.append({
            'Match': f"{fixture['home']} vs {fixture['away']}",
            'Start Time': fixture['start_time'],
            'Dominance Rules': ", ".join(dom_stats['rules_matched']),
            'Score': len(dom_stats['rules_matched'])
        })

if results:
    df = pd.DataFrame(results)
    df = df.sort_values(by='Score', ascending=False)
    st.success(f"✅ {len(df)} dominant matches found.")
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="dominant_matches.csv")
else:
    st.warning("⚠️ No dominant matches found based on current criteria.")
