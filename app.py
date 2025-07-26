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
    home_home_results = []
    away_away_results = []

    for match in h2hs:
        home = match["teams"]["home"]
        away = match["teams"]["away"]
        home_score = match["goals"]["home"]
        away_score = match["goals"]["away"]

        is_draw = home_score == away_score
        if is_draw:
            draws += 1
        elif home_score > away_score:
            if home["id"] == home_id:
                home_wins += 1
            else:
                away_wins += 1
        else:
            if away["id"] == home_id:
                home_wins += 1
            else:
                away_wins += 1

        # D4 collection
        if home["id"] == home_id:
            home_home_results.append((home_score, away_score))
        if away["id"] == away_id:
            away_away_results.append((away_score, home_score))

    total_played = home_wins + away_wins + draws

    # D1: Win Majority in all H2Hs
    if home_wins > total_played / 2 or away_wins > total_played / 2:
        rules_triggered.append("D1")

    # D2: Unbeaten streak in all H2Hs (win/draw only)
    if all(
        (match["teams"]["home"]["id"] == home_id and match["goals"]["home"] >= match["goals"]["away"]) or
        (match["teams"]["away"]["id"] == home_id and match["goals"]["away"] >= match["goals"]["home"])
        for match in h2hs
    ):
        rules_triggered.append("D2")
    elif all(
        (match["teams"]["home"]["id"] == away_id and match["goals"]["home"] >= match["goals"]["away"]) or
        (match["teams"]["away"]["id"] == away_id and match["goals"]["away"] >= match["goals"]["home"])
        for match in h2hs
    ):
        rules_triggered.append("D2")

    # D4: Unbeaten in all venue-specific H2Hs
    if home_home_results and all(h >= a for h, a in home_home_results):
        rules_triggered.append("D4")
    if away_away_results and all(a >= h for a, h in away_away_results):
        rules_triggered.append("D4")

    # D5: 3+ Win streak
    if home_wins >= 3:
        rules_triggered.append("D5")
    if away_wins >= 3:
        rules_triggered.append("D5")

    return list(set(rules_triggered))

# Load and process fixtures for next 3 days
for i in range(3):
    day = today + datetime.timedelta(days=i)
    st.subheader(f"📅 {day.strftime('%A, %d %B')}")
    fixtures = get_fixtures_by_day(day)

    if not fixtures:
        st.info("No fixtures found.")
        continue

    for fixture in fixtures:
        home = fixture["teams"]["home"]
        away = fixture["teams"]["away"]
        league = fixture["league"]["name"]
        date = fixture["fixture"]["date"]

        h2hs = get_h2h(home["id"], away["id"])
        triggered = apply_dominance_rules(h2hs, home["id"], away["id"])

        if triggered:
            dominant_matches.append({
                "match": f"{home['name']} vs {away['name']}",
                "league": league,
                "date": date,
                "rules": triggered
            })

# Display results
if dominant_matches:
    st.success(f"✅ {len(dominant_matches)} dominant match(es) found.")
    for match in dominant_matches:
        st.markdown(f"""
        **{match['match']}**
        - 🏆 League: {match['league']}
        - 🗓 Date: {match['date']}
        - ✅ Rules triggered: {', '.join(match['rules'])}
        """)
else:
    st.warning("⚠️ No dominant matches found based on current rules.")
