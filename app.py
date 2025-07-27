import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuration - Uses Streamlit Secrets
API_KEY = st.secrets["API_KEY"]
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-host': 'v3.football.api-sports.io',
    'x-rapidapi-key': API_KEY
}

# App Setup
st.set_page_config(
    page_title="⚽ H2H Dominance Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Football Match Dominance Analyzer")

# Cached API Functions
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fixtures(date):
    params = {'date': date.strftime('%Y-%m-%d')}
    response = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params)
    return response.json().get('response', [])

@st.cache_data(ttl=3600)
def fetch_h2h(home_id, away_id):
    response = requests.get(
        f"{BASE_URL}/fixtures/headtohead",
        headers=HEADERS,
        params={'h2h': f"{home_id}-{away_id}"}
    )
    return response.json().get('response', [])

@st.cache_data(ttl=3600)
def fetch_fixture_details(fixture_id):
    response = requests.get(
        f"{BASE_URL}/fixtures",
        headers=HEADERS,
        params={'id': fixture_id}
    )
    data = response.json().get('response', [])
    return {
        'lineups': bool(data[0].get('lineups')) if data else False,
        'injuries': len(data[0].get('injuries', [])) if data else 0
    }

# Dominance Analysis
def analyze_dominance(h2h_matches, home_id, away_id):
    if len(h2h_matches) < 2:
        return None
    
    stats = {
        'home_wins': 0,
        'away_wins': 0,
        'draws': 0,
        'home_unbeaten_streak': 0,
        'away_unbeaten_streak': 0,
        'home_home_unbeaten': 0,
        'home_home_matches': 0,
        'away_away_unbeaten': 0,
        'away_away_matches': 0
    }
    
    for match in sorted(h2h_matches, key=lambda x: x['fixture']['timestamp'], reverse=True):
        is_home = match['teams']['home']['id'] == home_id
        result = match['teams']['home']['winner']
        
        # Update win/draw counts
        if result is True:
            if is_home: stats['home_wins'] += 1
            else: stats['away_wins'] += 1
        elif result is False:
            if is_home: stats['away_wins'] += 1
            else: stats['home_wins'] += 1
        else:
            stats['draws'] += 1
        
        # Update streaks
        if result is not False if is_home else result is not True:
            stats['home_unbeaten_streak'] += 1
        else:
            stats['home_unbeaten_streak'] = 0
            
        if result is not True if is_home else result is not False:
            stats['away_unbeaten_streak'] += 1
        else:
            stats['away_unbeaten_streak'] = 0
        
        # Venue-specific stats
        if match['teams']['home']['id'] == home_id:
            stats['home_home_matches'] += 1
            if result is not False: stats['home_home_unbeaten'] += 1
        elif match['teams']['away']['id'] == away_id:
            stats['away_away_matches'] += 1
            if result is not True: stats['away_away_unbeaten'] += 1
    
    total_matches = stats['home_wins'] + stats['away_wins'] + stats['draws']
    return {
        'D1_home': stats['home_wins'] / total_matches >= 0.7,
        'D1_away': stats['away_wins'] / total_matches >= 0.7,
        'D2_home': stats['home_unbeaten_streak'] >= 2,
        'D2_away': stats['away_unbeaten_streak'] >= 2,
        'D3_home': stats['home_home_unbeaten'] == stats['home_home_matches'] if stats['home_home_matches'] > 0 else False,
        'D3_away': stats['away_away_unbeaten'] == stats['away_away_matches'] if stats['away_away_matches'] > 0 else False,
        'D4_home': stats['away_wins'] <= 4 if total_matches >= 12 else False,
        'D4_away': stats['home_wins'] <= 4 if total_matches >= 12 else False,
        'record': f"{stats['home_wins']}-{stats['draws']}-{stats['away_wins']}",
        'total_matches': total_matches
    }

# UI Components
date = st.date_input("Match Date", datetime.today())
min_h2h = st.slider("Minimum H2H Matches", 2, 10, 5)
selected_rules = st.multiselect(
    "Dominance Rules to Apply",
    options=["D1 (Win ≥70%)", "D2 (Unbeaten ≥2)", "D3 (Home/Away Dominance)", "D4 (≤4 Losses/12+)"],
    default=["D1 (Win ≥70%)", "D2 (Unbeaten ≥2)"]
)

# Main Execution
if st.button("Analyze Fixtures"):
    fixtures = fetch_fixtures(date)
    if not fixtures:
        st.warning("No fixtures found for selected date")
    else:
        results = []
        for fixture in fixtures:
            home_id = fixture['teams']['home']['id']
            away_id = fixture['teams']['away']['id']
            
            h2h_matches = fetch_h2h(home_id, away_id)
            if len(h2h_matches) < min_h2h:
                continue
                
            dominance = analyze_dominance(h2h_matches, home_id, away_id)
            if not dominance:
                continue
                
            rules = []
            if "D1 (Win ≥70%)" in selected_rules:
                if dominance['D1_home']: rules.append("D1: Home dominant")
                if dominance['D1_away']: rules.append("D1: Away dominant")
                
            if "D2 (Unbeaten ≥2)" in selected_rules:
                if dominance['D2_home']: rules.append(f"D2: Home unbeaten (last {dominance['home_unbeaten_streak']})")
                if dominance['D2_away']: rules.append(f"D2: Away unbeaten (last {dominance['away_unbeaten_streak']})")
                
            if "D3 (Home/Away Dominance)" in selected_rules:
                if dominance['D3_home']: rules.append("D3: Home venue dominance")
                if dominance['D3_away']: rules.append("D3: Away venue dominance")
                
            if "D4 (≤4 Losses/12+)" in selected_rules and dominance['total_matches'] >= 12:
                if dominance['D4_home']: rules.append("D4: Home minor losses")
                if dominance['D4_away']: rules.append("D4: Away minor losses")
                
            if rules:
                details = fetch_fixture_details(fixture['fixture']['id'])
                results.append({
                    'League': fixture['league']['name'],
                    'Home': fixture['teams']['home']['name'],
                    'Away': fixture['teams']['away']['name'],
                    'Time': datetime.fromtimestamp(fixture['fixture']['timestamp']).strftime('%H:%M'),
                    'H2H': dominance['record'],
                    'Matches': dominance['total_matches'],
                    'Rules': ", ".join(rules),
                    'Lineups': "✅" if details['lineups'] else "❌",
                    'Injuries': details['injuries']
                })
        
        if results:
            df = pd.DataFrame(results)
            st.dataframe(
                df.sort_values('Matches', ascending=False),
                column_config={
                    "Lineups": st.column_config.Column(width="small"),
                    "Injuries": st.column_config.ProgressColumn(
                        "Injuries",
                        help="Number of injuries",
                        format="%d",
                        min_value=0,
                        max_value=max(df['Injuries']) if len(df) > 0 else 1
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("No matches satisfy the selected dominance rules")

# Mobile Optimization
st.markdown("""
<style>
    .stDataFrame {
        font-size: 14px;
    }
    @media (max-width: 768px) {
        .stSlider {
            width: 100% !important;
        }
        .stMultiSelect {
            width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)
