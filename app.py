import streamlit as st
import requests
import datetime

API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

st.set_page_config(page_title="H2H Dominance Finder", layout="centered")
st.title("⚽ Daily Dominance Filter - API-Football")
st.caption("Matches with historical dominance in next 3 days")

today = datetime.date.today()
all_matches = []
dominant_matches = []

def get_fixtures_by_day(day):
    date_str = day.strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures?date={date_str}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get("response", [])
    return []

def get_h2h(home_id, away_id):
    url = f"{BASE_URL}/fixtures/headtohead?h2h={home_id}-{away_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get("response", [])
    return []

def apply_dominance_rules(h2hs, home_id, away_id):
    if len(h2hs) < 3:
        return []

    rules_triggered = []
    home_wins = away_wins = draws = 0
    home_home_venue_results = []
    away_away_venue_results = []

    for match in h2hs:
        winner = match["teams"]["home" if match["teams"]["home"]["id"] == home_id else "away"]["name"]
        is_draw = match["goals"]["home"] == match["goals"]["away"]

        if is_draw:
            draws += 1
        elif winner == match["teams"]["home"]["name"]:
            if match["teams"]["home"]["id"] == home_id:
                home_wins += 1
            else:
                away_wins += 1
        else:
            if match["teams"]["away"]["id"] == home_id:
                home_wins += 1
            else:
                away_wins += 1

        # Track venue dominance
        if match["teams"]["home"]["id"] == home_id:
            home_home_venue_results.append(match)
        if match["teams"]["away"]["id"] == away_id:
            away_away_venue_results.append(match)

    total = home_wins + away_wins + draws

    # D1: Win Majority
    if home_wins > total / 2 or away_wins > total / 2:
        rules_triggered.append("D1")

    # D2: Unbeaten (all win/draw)
    unbeaten_team = None
    if all(
        match["teams"]["home"]["id"] == home_id and match["goals"]["home"] >= match["goals"]["away"] or
        match["teams"]["away"]["id"] == home_id and match["goals"]["away"] >= match["goals"]["home"]
        for match in h2hs
    ):
        unbeaten_team = "Home"
        rules_triggered.append("D2")
    elif all(
        match["teams"]["home"]["id"] == away_id and match["goals"]["home"] >= match["goals"]["away"] or
        match["teams"]["away"]["id"] == away_id and match["goals"]["away"] >= match["goals"]["home"]
        for match in h2hs
    ):
        unbeaten_team = "Away"
        rules_triggered.append("D2")

    # D4: Venue-specific unbeaten streak
    if home_home_venue_results and all(
        match["goals"]["home"] >= match["goals"]["away"]
        for match in home_home_venue_results
    ):
        rules_triggered.append("D4")
    if away_away_venue_results and all(
        match["goals"]["away"] >= match["goals"]["home"]
        for match in away_away_venue_results
    ):
        rules_triggered.append("D4")

    # D5: Winning streak
    if home_wins >= 3:
        rules_triggered.append("D5")
    if away_wins >= 3:
        rules_triggered.append("D5")

    return list(set(rules_triggered))

# Load and check matches
for i in range(3):
    date = today + datetime.timedelta(days=i)
    fixtures = get_fixtures_by_day(date)
    st.subheader(f"📅 Matches for {date.strftime('%A, %d %B')} ({len(fixtures)} matches)")

    for fixture in fixtures:
        home_team = fixture["teams"]["home"]
        away_team = fixture["teams"]["away"]
        fixture_id = fixture["fixture"]["id"]

        h2h_matches = get_h2h(home_team["id"], away_team["id"])

        triggered = apply_dominance_rules(h2h_matches, home_team["id"], away_team["id"])
        if triggered:
            match_info = {
                "date": fixture["fixture"]["date"],
                "teams": f"{home_team['name']} vs {away_team['name']}",
                "triggered_rules": triggered,
                "league": fixture["league"]["name"]
            }
            dominant_matches.append(match_info)

# Show results
if dominant_matches:
    st.success(f"✅ {len(dominant_matches)} dominant match(es) found:")
    for m in dominant_matches:
        st.markdown(f"""
        **{m['teams']}**
        - 🏆 League: {m['league']}
        - 📆 Date: {m['date']}
        - ✅ Rules triggered: {', '.join(m['triggered_rules'])}
        """)
else:
    st.warning("⚠️ No dominant matches found based on current rules.")
