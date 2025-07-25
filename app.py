import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ------------------------
# CONFIGURATION
# ------------------------
DAYS_AHEAD = 3
H2H_CHECK_LIMIT = 10

# ------------------------
# FETCH FIXTURES
# ------------------------
def get_fixtures():
    base_url = "https://api.sofascore.com/api/v1/sport/football/scheduled-events/"
    fixtures = []

    for i in range(DAYS_AHEAD):
        date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        url = base_url + date
        r = requests.get(url)
        if r.status_code != 200:
            continue
        data = r.json()
        for e in data.get('events', []):
            try:
                fixtures.append({
                    'date': date,
                    'home': e['homeTeam']['name'],
                    'away': e['awayTeam']['name'],
                    'match_id': e['id']
                })
            except:
                continue
    return fixtures

# ------------------------
# FETCH H2H RESULTS
# ------------------------
def get_h2h_results(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/h2h"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    matches = r.json().get('h2h', [])[:H2H_CHECK_LIMIT]
    results = []
    for m in matches:
        home = m['homeTeam']['name']
        away = m['awayTeam']['name']
        hs = m.get('homeScore', {}).get('current')
        as_ = m.get('awayScore', {}).get('current')
        if hs is None or as_ is None:
            continue
        winner = 'Draw'
        if hs > as_:
            winner = home
        elif as_ > hs:
            winner = away
        results.append({'winner': winner, 'home': home})
    return results

# ------------------------
# DOMINANCE RULES
# ------------------------
def evaluate_dominance(h2h, team1, team2, home_team):
    team1_wins = sum(1 for m in h2h if m['winner'] == team1)
    team2_wins = sum(1 for m in h2h if m['winner'] == team2)
    
    # Modified D2: Team1 unbeaten in all of the last N (>=4) H2H matches
    team1_unbeaten_streak = 0
    for m in reversed(h2h):
        if m['winner'] in [team1, 'Draw']:
            team1_unbeaten_streak += 1
        else:
            break
    
    team1_streak = all(m['winner'] == team1 for m in h2h[-4:])
    home_venue_wins = sum(1 for m in h2h if m['home'] == home_team and m['winner'] == home_team)

    rules = []
    if team1_wins >= 7:
        rules.append("D1")
    if team1_unbeaten_streak >= 4:
        rules.append("D2")
    if team1_streak:
        rules.append("D5")
    if home_venue_wins >= 4:
        rules.append("D4")
    return rules

# ------------------------
# FETCH ODDS
# ------------------------
def get_odds(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/odds/1/all"
    r = requests.get(url)
    if r.status_code != 200:
        return {}
    markets = r.json().get('markets', [])
    one, x, two = [], [], []
    for m in markets:
        if m['marketName'] != "1X2":
            continue
        for book in m['bookmakers']:
            for val in book['values']:
                if val['value'] == '1':
                    one.append(val['odd'])
                elif val['value'] == 'X':
                    x.append(val['odd'])
                elif val['value'] == '2':
                    two.append(val['odd'])
    avg = lambda lst: round(sum(lst)/len(lst), 2) if lst else None
    return {'1': avg(one), 'X': avg(x), '2': avg(two)}

# ------------------------
# STREAMLIT UI
# ------------------------
st.set_page_config(page_title="H2H Dominance Filter", layout="wide")
st.title("⚽ Daily Dominance Filter - Sofascore")
st.write("Filtering matches based on historical dominance and odds")

with st.spinner("Fetching matches & data..."):
    fixtures = get_fixtures()
    filtered = []
    for f in fixtures:
        h2h = get_h2h_results(f['match_id'])
        if not h2h:
            continue
        rules = evaluate_dominance(h2h, f['home'], f['away'], f['home'])
        if rules:
            odds = get_odds(f['match_id'])
            filtered.append({
                'Date': f['date'],
                'Match': f"{f['home']} vs {f['away']}",
                'Dominant Team': f['home'],
                'Rules': ", ".join(rules),
                'Odds 1': odds.get('1'),
                'Odds X': odds.get('X'),
                'Odds 2': odds.get('2'),
                'Match ID': f['match_id']
            })

    df = pd.DataFrame(filtered)

if not df.empty:
    st.success(f"{len(df)} dominant matches found")
    st.dataframe(df)
    st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name="dominant_matches.csv", mime="text/csv")
else:
    st.warning("No dominant matches found.")
