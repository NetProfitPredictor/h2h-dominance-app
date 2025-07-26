import streamlit as st
import requests
import datetime

API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

st.set_page_config(page_title="Daily Dominance Filter", layout="wide")
st.title("⚽ Daily Dominance Filter - API-Football")
st.caption("Matches with historical dominance in next 3 days")

today = datetime.date.today()
LOOKAHEAD_DAYS = 3
MIN_H2H = 3

def get_fixtures_by_day(date):
    url = f"{BASE_URL}/fixtures"
    params = {"date": date.strftime("%Y-%m-%d")}
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json().get("response", []) if res.status_code == 200 else []

def get_h2h_matches(home_team_id, away_team_id):
    url = f"{BASE_URL}/fixtures/headtohead"
    params = {
        "h2h": f"{home_team_id}-{away_team_id}",
        "last": 20  # get last 20 meetings
    }
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json().get("response", []) if res.status_code == 200 else []

def evaluate_dominance_rules(h2h, home_id, away_id):
    if len(h2h) < MIN_H2H:
        return []

    home_wins, away_wins, draws = 0, 0, 0
    home_at_home_unbeaten = True
    away_at_away_unbeaten = True

    for match in h2h:
        home = match['teams']['home']['id']
        winner = match['teams']['winner']
        is_draw = not winner

        if is_draw:
            draws += 1
        elif winner == match['teams']['home']['id']:
            if home == home_id:
                home_wins += 1
            else:
                away_wins += 1
        else:
            if home == home_id:
                away_wins += 1
            else:
                home_wins += 1

        # Check unbeaten at venue
        if match['teams']['home']['id'] == home_id and winner == away_id:
            home_at_home_unbeaten = False
        if match['teams']['home']['id'] == away_id and winner == home_id:
            away_at_away_unbeaten = False

    rules_triggered = []

    # D1: Majority wins
    if home_wins + away_wins > 0:
        if home_wins > away_wins:
            rules_triggered.append("D1 (Home Win Majority)")
        elif away_wins > home_wins:
            rules_triggered.append("D1 (Away Win Majority)")

    # D2: One team unbeaten in all H2H
    unbeaten_home = all(
        match['teams']['winner'] != away_id
        for match in h2h
        if match['teams']['home']['id'] == home_id
    )
    unbeaten_away = all(
        match['teams']['winner'] != home_id
        for match in h2h
        if match['teams']['home']['id'] == away_id
    )
    if unbeaten_home:
        rules_triggered.append("D2 (Home Unbeaten in H2H)")
    if unbeaten_away:
        rules_triggered.append("D2 (Away Unbeaten in H2H)")

    # D4: Venue Unbeaten Record
    if home_at_home_unbeaten:
        rules_triggered.append("D4 (Home Unbeaten at Home)")
    if away_at_away_unbeaten:
        rules_triggered.append("D4 (Away Unbeaten at Away)")

    # D5: Winning Streak
    streak_team = h2h[0]['teams']['winner']
    if streak_team and all(match['teams']['winner'] == streak_team for match in h2h):
        if streak_team == home_id:
            rules_triggered.append("D5 (Home Winning Streak)")
        elif streak_team == away_id:
            rules_triggered.append("D5 (Away Winning Streak)")

    return rules_triggered

# Main loop
for i in range(LOOKAHEAD_DAYS):
    date = today + datetime.timedelta(days=i)
    st.subheader(f"📅 {date.strftime('%A, %d %B')}")

    fixtures = get_fixtures_by_day(date)
    st.write("🔍 Raw fixtures from API for this date:", fixtures)

    if not fixtures:
        st.info("⚠️ No fixtures found.")
        continue

    found = False

    for fixture in fixtures:
        try:
            home = fixture['teams']['home']
            away = fixture['teams']['away']
            home_id = home['id']
            away_id = away['id']

            h2h = get_h2h_matches(home_id, away_id)

            rules = evaluate_dominance_rules(h2h, home_id, away_id)

            if rules:
                found = True
                st.markdown(f"### 🏟️ {home['name']} vs {away['name']}")
                st.markdown(f"**🏆 Dominance Rules Triggered:** {', '.join(rules)}")
                st.markdown("---")

        except Exception as e:
            st.warning(f"Error checking fixture: {e}")
            continue

    if not found:
        st.info("⚠️ No dominant matches found based on current rules.")
