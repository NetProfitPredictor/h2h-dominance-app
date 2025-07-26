import streamlit as st
import requests
import datetime
import os

# Constants
API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
API_HOST = "https://v3.football.api-sports.io"
LOOKAHEAD_DAYS = 3
HEADERS = {
    "x-apisports-key": API_KEY
}

# Helper to get fixtures for a specific day
def get_fixtures_by_day(date):
    url = f"{API_HOST}/fixtures?date={date.strftime('%Y-%m-%d')}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data.get("response", [])
    return []

# Main app
st.set_page_config(page_title="Daily Dominance Filter - API-Football")
st.title("\u26bd Daily Dominance Filter - API-Football")
st.markdown("Matches with historical dominance in next 3 days")

today = datetime.date.today()

for i in range(LOOKAHEAD_DAYS):
    date = today + datetime.timedelta(days=i)
   st.subheader(f"📅 {date.strftime('%A, %d %B')}")

    fixtures = get_fixtures_by_day(date)

    # \ud83d\udd0d DEBUG: Print raw fixture data
    st.write("\ud83d\udd0d Raw fixtures from API for this date:", fixtures)

    if not fixtures:
        st.info("\u26a0\ufe0f No fixtures found.")
        continue

    # You can now add dominance rule checks here after confirming fixture data loads correctly
