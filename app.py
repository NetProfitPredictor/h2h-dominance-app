import streamlit as st
import requests
import datetime
import pandas as pd

API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

LOOKAHEAD_DAYS = 3
MIN_H2H_MATCHES = 3

st.set_page_config(page_title="⚽ Daily Dominance Filter - API-Football", layout="wide")
st.title("⚽ Daily Dominance Filter - API-Football")
st.caption("Matches with historical dominance in next 3 days")

today = datetime.date.today()

def get_fixtures_by_day(date):
    url = f"{API_BASE}/fixtures?date={date}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        data = res.json().get("response", [])
        st.markdown(f"🔍 **Raw fixtures from API for {date}:**")
        if len(data) == 0:
            st.warning("⚠️ No fixtures returned in API response.")
        else:
            st.write(data[:10])  # Show first 10 fixtures to inspect structure
        return data
    else:
        st.error(f"❌ Failed to fetch fixtures. Status code: {res.status_code}")
        return []

def get_h2h(home_id, away_id):
    url = f"{API_BASE}/fixtures/headtohead?h2h={home_id}-{away_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get("response", [])
    return []

def check_d1_majority_wins(h2h, home_id, away_id):
    home_wins = sum(1 for m in h2h if m["teams"]["home"]["id"] == home_id and m["teams"]["home"]["winner"])
    away_wins = sum(1 for m in h2h if m["teams"]["away"]["id"] == away_id and m["teams"]["away"]["winner"])
    total = home_wins + away_wins
    if total == 0:
        return False
    return home_wins > total / 2 or away_wins > total / 2

def check_d2_unbeaten_streak(h2h, team_id):
    if len(h2h) < 3:
        return False
    unbeaten = all(
        (match["teams"]["home"]["id"] == team_id and (match["teams"]["home"]["winner"] or not match["teams"]["away"]["winner"])) or
        (match["teams"]["away"]["id"] == team_id and (match["teams"]["away"]["winner"] or not match["teams"]["home"]["winner"]))
        for match in h2h[:3]
    )
    return unbeaten

def check_d4_home_or_away_dominance(h2h, team_id, is_home):
    if is_home:
        filtered = [m for m in h2h if m["teams"]["home"]["id"] == team_id]
        unbeaten = all(m["teams"]["home"]["winner"] or not m["teams"]["away"]["winner"] for m in filtered)
    else:
        filtered = [m for m in h2h if m["teams"]["away"]["id"] == team_id]
        unbeaten = all(m["teams"]["away"]["winner"] or not m["teams"]["home"]["winner"] for m in filtered)
    return unbeaten and len(filtered) > 0

def check_d5_streak(h2h, team_id):
    count = 0
    for match in h2h:
        if match["teams"]["home"]["id"] == team_id and match["teams"]["home"]["winner"]:
            count += 1
        elif match["teams"]["away"]["id"] == team_id and match["teams"]["away"]["winner"]:
            count += 1
        else:
            break
    return count >= 3

for i in range(LOOKAHEAD_DAYS):
    date = today + datetime.timedelta(days=i)
    st.subheader(f"📅 {date.strftime('%A, %d %B')}")

    fixtures = get_fixtures_by_day(date)

    if not fixtures:
        st.warning("⚠️ No fixtures found.")
        continue

    dominant_matches = []

    for fixture in fixtures:
        try:
            home = fixture["teams"]["home"]
            away = fixture["teams"]["away"]
            league = fixture["league"]["name"]

            h2h = get_h2h(home["id"], away["id"])
            if len(h2h) < MIN_H2H_MATCHES:
                continue

            d1 = check_d1_majority_wins(h2h, home["id"], away["id"])
            d2_home = check_d2_unbeaten_streak(h2h, home["id"])
            d2_away = check_d2_unbeaten_streak(h2h, away["id"])
            d4_home = check_d4_home_or_away_dominance(h2h, home["id"], is_home=True)
            d4_away = check_d4_home_or_away_dominance(h2h, away["id"], is_home=False)
            d5_home = check_d5_streak(h2h, home["id"])
            d5_away = check_d5_streak(h2h, away["id"])

            if d1 or d2_home or d2_away or d4_home or d4_away or d5_home or d5_away:
                dominant_matches.append({
                    "match": f"{home['name']} vs {away['name']}",
                    "league": league,
                    "rules": ", ".join(
                        []
                        + (["D1"] if d1 else [])
                        + (["D2-H"] if d2_home else [])
                        + (["D2-A"] if d2_away else [])
                        + (["D4-H"] if d4_home else [])
                        + (["D4-A"] if d4_away else [])
                        + (["D5-H"] if d5_home else [])
                        + (["D5-A"] if d5_away else [])
                    )
                })
        except Exception as e:
            continue

    if not dominant_matches:
        st.info("⚠️ No dominant matches found based on current rules.")
    else:
        for match in dominant_matches:
            st.markdown(f"✅ **{match['match']}** — {match['league']}  \n🧠 Rules Matched: `{match['rules']}`")

        # ✅ Export section
        df = pd.DataFrame(dominant_matches)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dominant Matches as CSV",
            data=csv,
            file_name=f"dominant_matches_{date}.csv",
            mime="text/csv"
        )
