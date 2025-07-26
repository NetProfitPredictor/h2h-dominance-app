import streamlit as st
import requests
import datetime
import time

# ---------------------------- SETTINGS ---------------------------- #
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

DOMINANCE_MIN_H2H = 2  # Minimum H2H count
LOOKAHEAD_DAYS = 3     # How many days ahead to fetch fixtures

# ---------------------------- APP UI ---------------------------- #
st.title("\u26bd Daily Dominance Filter - Sofascore")
st.caption("Filtering matches based on historical dominance and odds")
st.write("\n")

with st.spinner("\ud83d\udcc5 Loading fixtures..."):
    upcoming_fixtures = []
    today = datetime.date.today()

    for i in range(LOOKAHEAD_DAYS):
        date = today + datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                events = data.get("events", [])
                st.write(f"\u2705 Found {len(events)} fixtures for {date_str}")

                for ev in events:
                    try:
                        match_id = ev.get("id")
                        home = ev.get("homeTeam", {}).get("name")
                        away = ev.get("awayTeam", {}).get("name")

                        if match_id and home and away:
                            upcoming_fixtures.append({
                                "id": match_id,
                                "home": home,
                                "away": away
                            })
                            st.write(f"\u27a1\ufe0f {home} vs {away} (ID: {match_id})")
                        else:
                            st.warning(f"\ud83d\udd39 Skipped event due to missing data: {ev.get('tournament', {}).get('name', 'Unknown')}")
                    except Exception as e:
                        st.error(f"Error parsing event: {e}")
            else:
                st.warning(f"\u26a0\ufe0f Failed to load {date_str}: Status {r.status_code}")
        except Exception as e:
            st.error(f"Request error for {date_str}: {e}")
        time.sleep(1)

# ---------------------------- RESULTS ---------------------------- #
if not upcoming_fixtures:
    st.warning("No upcoming matches found. Check Sofascore or retry later.")
else:
    st.success(f"\u2705 Total matches collected: {len(upcoming_fixtures)}")
    st.info("Next: H2H analysis, dominance rules, form check...")
    # <-- H2H & dominance logic will plug in here -->
