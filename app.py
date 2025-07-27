import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY', 'a1e3317f95266baffbbbdaaba3e6890b')  # Your default API key

# API Football configuration
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-host': 'v3.football.api-sports.io',
    'x-rapidapi-key': API_KEY
}

# App title and configuration
st.set_page_config(page_title="H2H Dominance Analyzer", layout="wide")
st.title("⚽ Football Fixture Analyzer with H2H Dominance Rules")

# Sidebar for user inputs
with st.sidebar:
    st.header("Settings")
    league_id = st.text_input("League ID (Optional)", help="Leave empty to analyze all leagues")
    date = st.date_input("Fixture Date", datetime.today())
    selected_rules = st.multiselect(
        "Select Dominance Rules to Apply",
        ["D1 (Win majority ≥70%)", "D2 (Unbeaten streak ≥2)", 
         "D3 (Home/Away dominance)", "D4 (Minor loss ≤4/12+)"],
        default=["D1 (Win majority ≥70%)", "D2 (Unbeaten streak ≥2)"]
    )
    min_h2h_matches = st.slider("Minimum H2H Matches Required", 2, 20, 5)
    analyze_button = st.button("Analyze Fixtures")

# Function to fetch data from API
def fetch_data(endpoint, params=None):
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get('response', [])
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Function to fetch fixtures for the day
def get_fixtures(date, league_id=None):
    params = {'date': date.strftime('%Y-%m-%d')}
    if league_id:
        params['league'] = league_id
    return fetch_data('fixtures', params)

# Function to fetch H2H data between two teams
def get_h2h(team1, team2):
    return fetch_data('fixtures/headtohead', {'h2h': f"{team1}-{team2}"})

# Function to fetch lineup and injury info
def get_fixture_details(fixture_id):
    return fetch_data('fixtures', {'id': fixture_id})

# Function to analyze H2H dominance
def analyze_h2h_dominance(h2h_matches, home_team, away_team):
    if not h2h_matches or len(h2h_matches) < 2:
        return None
    
    total_matches = len(h2h_matches)
    home_wins = 0
    away_wins = 0
    draws = 0
    home_unbeaten_streak = 0
    away_unbeaten_streak = 0
    home_home_unbeaten = 0
    home_home_matches = 0
    away_away_unbeaten = 0
    away_away_matches = 0
    
    # Reverse to analyze from oldest to newest
    reversed_matches = sorted(h2h_matches, key=lambda x: x['fixture']['timestamp'])
    
    for match in reversed_matches:
        home_id = match['teams']['home']['id']
        result = match['teams']['home']['winner']
        
        # Count wins/draws
        if result is True:
            if home_id == home_team:
                home_wins += 1
                home_unbeaten_streak += 1
                away_unbeaten_streak = 0
            else:
                away_wins += 1
                away_unbeaten_streak += 1
                home_unbeaten_streak = 0
        elif result is False:
            if home_id == home_team:
                away_wins += 1
                away_unbeaten_streak += 1
                home_unbeaten_streak = 0
            else:
                home_wins += 1
                home_unbeaten_streak += 1
                away_unbeaten_streak = 0
        else:  # draw
            draws += 1
            home_unbeaten_streak += 1
            away_unbeaten_streak += 1
        
        # Check home/away dominance
        if match['teams']['home']['id'] == home_team:
            home_home_matches += 1
            if result is not False:  # home team didn't lose at home
                home_home_unbeaten += 1
        elif match['teams']['away']['id'] == away_team:
            away_away_matches += 1
            if result is not True:  # away team didn't lose at away
                away_away_unbeaten += 1
    
    # Calculate dominance
    dominance = {
        'D1_home': (home_wins / total_matches) >= 0.7 if total_matches >= 2 else False,
        'D1_away': (away_wins / total_matches) >= 0.7 if total_matches >= 2 else False,
        'D2_home': home_unbeaten_streak >= 2,
        'D2_away': away_unbeaten_streak >= 2,
        'D3_home': home_home_unbeaten == home_home_matches if home_home_matches > 0 else False,
        'D3_away': away_away_unbeaten == away_away_matches if away_away_matches > 0 else False,
        'D4_home': away_wins <= 4 if total_matches >= 12 else False,
        'D4_away': home_wins <= 4 if total_matches >= 12 else False,
        'total_matches': total_matches,
        'home_wins': home_wins,
        'away_wins': away_wins,
        'draws': draws
    }
    
    return dominance

# Main app logic
if analyze_button:
    st.subheader(f"Analyzing Fixtures for {date.strftime('%Y-%m-%d')}")
    
    # Fetch fixtures
    fixtures = get_fixtures(date, league_id)
    if not fixtures:
        st.warning("No fixtures found for the selected date and league.")
        st.stop()
    
    progress_bar = st.progress(0)
    results = []
    
    for i, fixture in enumerate(fixtures):
        progress_bar.progress((i + 1) / len(fixtures))
        
        fixture_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['id']
        away_team = fixture['teams']['away']['id']
        league = fixture['league']['name']
        
        # Fetch H2H data
        h2h_data = get_h2h(home_team, away_team)
        if not h2h_data or len(h2h_data) < min_h2h_matches:
            continue
        
        # Analyze dominance
        dominance = analyze_h2h_dominance(h2h_data, home_team, away_team)
        if not dominance:
            continue
        
        # Check selected rules
        rules_satisfied = []
        if "D1 (Win majority ≥70%)" in selected_rules:
            if dominance['D1_home']:
                rules_satisfied.append("D1: Home team wins ≥70%")
            if dominance['D1_away']:
                rules_satisfied.append("D1: Away team wins ≥70%")
        
        if "D2 (Unbeaten streak ≥2)" in selected_rules:
            if dominance['D2_home']:
                rules_satisfied.append(f"D2: Home team unbeaten in last {dominance['D2_home']} matches")
            if dominance['D2_away']:
                rules_satisfied.append(f"D2: Away team unbeaten in last {dominance['D2_away']} matches")
        
        if "D3 (Home/Away dominance)" in selected_rules:
            if dominance['D3_home']:
                rules_satisfied.append("D3: Home team unbeaten at home in H2H")
            if dominance['D3_away']:
                rules_satisfied.append("D3: Away team unbeaten away in H2H")
        
        if "D4 (Minor loss ≤4/12+)" in selected_rules and dominance['total_matches'] >= 12:
            if dominance['D4_home']:
                rules_satisfied.append("D4: Home team lost ≤4 in 12+ H2H")
            if dominance['D4_away']:
                rules_satisfied.append("D4: Away team lost ≤4 in 12+ H2H")
        
        if rules_satisfied:
            # Fetch additional details
            fixture_details = get_fixture_details(fixture_id)
            lineup = None
            injuries = []
            
            if fixture_details:
                lineup = fixture_details[0].get('lineups', [])
                injuries = fixture_details[0].get('injuries', [])
            
            results.append({
                'fixture_id': fixture_id,
                'league': league,
                'home_team': fixture['teams']['home']['name'],
                'away_team': fixture['teams']['away']['name'],
                'time': fixture['fixture']['timestamp'],
                'h2h_matches': dominance['total_matches'],
                'h2h_record': f"{dominance['home_wins']}-{dominance['draws']}-{dominance['away_wins']}",
                'rules_satisfied': ", ".join(rules_satisfied),
                'lineup_available': bool(lineup),
                'injuries_count': len(injuries)
            })
    
    progress_bar.empty()
    
    if not results:
        st.warning("No fixtures satisfy the selected dominance rules.")
        st.stop()
    
    # Display results
    st.success(f"Found {len(results)} fixtures that satisfy the selected rules!")
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(results)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%H:%M')
    
    # Show summary table
    st.subheader("Dominant Fixtures")
    st.dataframe(df[['league', 'home_team', 'away_team', 'time', 'h2h_matches', 'h2h_record', 'rules_satisfied']])
    
    # Show details for selected fixture
    selected_fixture = st.selectbox(
        "Select fixture to view details",
        [f"{row['home_team']} vs {row['away_team']} ({row['league']})" for _, row in df.iterrows()]
    )
    
    if selected_fixture:
        selected_idx = [i for i, x in enumerate([f"{row['home_team']} vs {row['away_team']} ({row['league']})" 
                                for _, row in df.iterrows()]) if x == selected_fixture][0]
        selected = df.iloc[selected_idx]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Fixture Details")
            st.write(f"**League:** {selected['league']}")
            st.write(f"**Home Team:** {selected['home_team']}")
            st.write(f"**Away Team:** {selected['away_team']}")
            st.write(f"**Time:** {selected['time']}")
            st.write(f"**H2H Matches:** {selected['h2h_matches']}")
            st.write(f"**H2H Record (W-D-L):** {selected['h2h_record']}")
            st.write(f"**Dominance Rules:** {selected['rules_satisfied']}")
        
        with col2:
            st.subheader("Additional Info")
            if selected['lineup_available']:
                st.success("Lineup data available")
            else:
                st.warning("Lineup data not available")
            
            if selected['injuries_count'] > 0:
                st.warning(f"{selected['injuries_count']} injuries reported")
            else:
                st.success("No injuries reported")

# Add some instructions
with st.expander("How to use this app"):
    st.markdown("""
    1. Select the date you want to analyze (defaults to today)
    2. Optionally enter a league ID to filter specific leagues
    3. Select which dominance rules you want to apply
    4. Set the minimum number of H2H matches required for analysis
    5. Click "Analyze Fixtures" to run the analysis
    6. View the results and select any fixture for more details
    
    **Dominance Rules Explained:**
    - **D1 (Win majority ≥70%)**: A team wins ≥70% of all H2H matches
    - **D2 (Unbeaten streak ≥2)**: A team is unbeaten in all of the last N H2H matches (N≥2)
    - **D3 (Home/Away dominance)**: A team is unbeaten in all H2H matches at their home/away venue
    - **D4 (Minor loss ≤4/12+)**: A team lost ≤4 in 12+ H2H matches
    """)

# Add footer
st.markdown("---")
st.markdown("""
    *Data provided by API-Football*  
    *App created with Streamlit*
""")