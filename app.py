import streamlit as st
import requests
import datetime

# Set page config
st.set_page_config(page_title="⚽ Daily Dominance Filter - API-Football")

st.title("⚽ Daily Dominance Filter - API-Football")
st.caption("Matches with historical dominance in next 3 days")

# API Setup
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Constants
MIN_H2H = 3  # You can reduce to 1 for debugging
LOOKAHEAD_DAYS = 3

# Function to get fixtures for a given date
def get_fixtures_by_day(date):
    url = f"{BASE_URL}/fixtures"
    params = {
        "date": date.strftime('%Y-%m-%d')
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("response", [])
    else:
        st.error(f"❌ Failed to fetch fixtures for {date}. Status code: {response.status_code}")
        return []

# Start loop through next 3 days
today = datetime.date.today()

for i in range(LOOKAHEAD_DAYS):
    date = today + datetime.timedelta(days=i)
    st.subheader(f"📅 {date.strftime('%A, %d %B')}")

    fixtures = get_fixtures_by_day(date)

    # Debug: Show fixture count
    st.write(f"🔍 Raw fixtures from API for this date:\n\n[{0} - {len(fixtures)}]")

    # ✅ Show first 10 matchups to verify
    if fixtures:
        st.write(f"✅ Total fixtures: {len(fixtures)}")
        for idx, fixture in enumerate(fixtures[:10]):
            home = fixture['teams']['home']['name']
            away = fixture['teams']['away']['name']
            league = fixture['league']['name']
            st.markdown(f"**{idx+1}. {home} vs {away}** — _{league}_")
    else:
        st.info("⚠️ No fixtures found.")
