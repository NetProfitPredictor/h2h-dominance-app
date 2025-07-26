import streamlit as st
import requests
import datetime
import time
import json

st.set_page_config(page_title="⚽ Daily Dominance Filter", layout="centered")
st.title("⚽ Daily Dominance Filter - Sofascore")
st.caption("Filtering matches based on historical dominance and odds")
st.write("")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

LOOKAHEAD_DAYS = 3
today = datetime.date.today()
all_matches = []

st.subheader("📅 Loading fixtures...")

for i in range(LOOKAHEAD_DAYS):
    date = today + datetime.timedelta(days=i)
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
    st.code(f"Fetching: {url}", language="text")

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        st.write(f"Status code: {res.status_code}")
        
        if res.status_code == 200:
            json_data = res.json()
            events = json_data.get("events", [])
            st.write(f"✅ {len(events)} events found for {date_str}")
            
            if len(events) > 0:
                st.json(events[0])  # show one sample event for inspection

            for ev in events:
                home = ev.get("homeTeam", {}).get("name", "")
                away = ev.get("awayTeam", {}).get("name", "")
                match_id = ev.get("id", "")
                if home and away and match_id:
                    all_matches.append((home, away, match_id))
                    st.write(f"➡️ {home} vs {away} (ID: {match_id})")
        else:
            st.warning(f"⚠️ Request failed for {date_str}. Status code: {res.status_code}")

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")

    time.sleep(1)

if not all_matches:
    st.warning("⚠️ No upcoming matches found. Check if Sofascore changed the structure.")
else:
    st.success(f"✅ Total matches loaded: {len(all_matches)}")
