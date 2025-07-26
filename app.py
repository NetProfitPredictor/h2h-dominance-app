import streamlit as st
import requests
import datetime

API_KEY = "a1e3317f95266baffbbbdaaba3e6890b"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# Streamlit page settings
st.set_page_config(page_title="Daily Dominance Filter", layout="wide")
st.title("⚽ Daily Dominance Filter - API-Football")
st.caption("Matches with historical dominance in next 3 days")

today = datetime.date.today()

def get_fixtures_by_day(date):
    url = f"{BASE_URL}/fixtures"
    params = {
        "date": date.strftime("%Y-%m-%d")
    }
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get("response", [])
    else:
        st.error(f"⚠️ API error: {response.status_code}")
        return []

# ✅ Just check today's fixtures
date = today
st.subheader(f"📅 {date.strftime('%A, %d %B')}")

fixtures = get_fixtures_by_day(date)

# 🔍 DEBUG: Show raw fixture data
st.write("🔍 Raw fixtures from API for this date:", fixtures)

if not fixtures:
    st.info("⚠️ No fixtures found.")
