import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (PREMIUM THEME)
# ==========================================
st.set_page_config(page_title="EPL Hub", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

# Removed the hardcoded dark .stApp gradient so native Light/Dark toggle works.
# Swapped fixed colors for var(--secondary-background-color) and var(--text-color).
st.markdown("""
<style>
    /* Custom Card Containers */
    .scout-card { background: var(--secondary-background-color); border: 1px solid rgba(0, 136, 204, 0.3); border-radius: 12px; padding: 24px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .pitch-card { background: var(--secondary-background-color); border: 1px solid #00f2fe; border-radius: 10px; padding: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,242,254,0.1); position: relative; }
    .bench-card { background: var(--secondary-background-color); border: 1px solid #ff007f; border-radius: 10px; padding: 12px; text-align: center; position: relative;}
    .fixture-card { background: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease;}
    .fixture-card:hover { border-color: rgba(0, 136, 204, 0.5); box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
    
    /* Pitch Background - Opacity lowered so it looks good in light and dark mode */
    .pitch-container { background: linear-gradient(180deg, rgba(27, 67, 50, 0.25) 0%, rgba(45, 106, 79, 0.25) 100%); border-radius: 16px; padding: 25px; border: 1px solid rgba(76, 175, 80, 0.5); margin-bottom: 25px;}
    
    /* Badges */
    .badge-cyan { background: rgba(0, 242, 254, 0.15); color: #0088cc; border: 1px solid #00f2fe; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;}
    .badge-pink { background: rgba(255, 0, 127, 0.15); color: #cc0066; border: 1px solid #ff007f; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;}
    .score-box { background: var(--background-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 8px 18px; font-size: 20px; font-weight: 800; letter-spacing: 3px; color: var(--text-color); }
    
    /* Leaderboard Styling */
    .leaderboard-item { font-size: 14px; padding: 8px 0; border-bottom: 1px solid var(--border-color); color: var(--text-color); }
    .leaderboard-stat { color: #0088cc; font-weight: 700; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

chart_theme = "streamlit"

# ==========================================
# 2. DATA LOADERS (Cached)
# ==========================================
@st.cache_data(ttl=3600)
def load_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return None, None
    except requests.exceptions.RequestException: 
        return None, None
    
    data = response.json()
    players = pd.DataFrame(data['elements'])
    teams = pd.DataFrame(data['teams'])
    
    players['team_name'] = players['team'].map(dict(zip(teams['id'], teams['name'])))
    players['team_strength'] = players['team'].map(dict(zip(teams['id'], teams['strength']))).fillna(3)
    
    # --- AVAILABILITY LOGIC: Extract Status & Chance of Playing ---
    if 'status' in players.columns:
        players['status'] = players['status'].fillna('a')
    else:
        players['status'] = 'a'
        
    if 'chance_of_playing_next_round' in players.columns:
        players['chance_of_playing_next_round'] = pd.to_numeric(players['chance_of_playing_next_round'], errors='coerce').fillna(100.0)
    else:
        players['chance_of_playing_next_round'] = 100.0
    # --------------------------------------------------------------
    
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'expected_goals', 'expected_assists', 'bps']
    
    for col in num_cols: 
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors='coerce').fillna(0.0)
            
    players['cost_m'] = players['now_cost'] / 10.0
    players['position'] = players['element_type'].map({1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'})
    
    return players, teams

@st.cache_data(ttl=3600)
def load_match_data():
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/02_Automated_Football_Analytics/data/pl_rolling_3_years_latest.csv"
    try:
        df = pd.read_csv(raw_url)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by=['Season', 'Date'])
        df['Gameweek'] = df.groupby('Season').cumcount() // 10 + 1
        return df
    except Exception:
        return pd.DataFrame()

players_df, teams_df = load_fpl_data()
match_df = load_match_data()

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("⚽ EPL HUB")
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("Select Module:", [
    "👤 Player Scout Card", 
    "⚡ FPL Squad Optimizer", 
    "📈 Team Betting Edge",
    "📅 Match Results & Fixtures",
    "📊 Live League Table"
])

# ==========================================
# MODULE 1: PLAYER SCOUT CARD
# ==========================================
if app_mode == "👤 Player Scout Card":
    st.title("👤 Player Performance Profile")
    
    if players_df is not None and not players_df.empty:
        f_col1, f_col2 = st.columns(2)
        teams_list = ["All"] + sorted(players_df['team_name'].unique().tolist())
        selected_team = f_col1.selectbox("Filter by Team:", teams_list)
        selected_pos = f_col2.selectbox("Filter by Position:", ["All", "GKP", "DEF", "MID", "FWD"])
        
        filtered_df = players_df.copy()
        if selected_team != "All": filtered_df = filtered_df[filtered_df['team_name'] == selected_team]
        if selected_pos != "All": filtered_df = filtered_df[filtered_df['position'] == selected_pos]
        
        player_list = sorted((filtered_df['first_name'] + " " + filtered_df['second_name']).tolist())
        
        if len(player_list) > 0:
            selected_player = st.selectbox("Select Player:", player_list)
            p_data = filtered_df[(filtered_df['first_name'] + " " + filtered_df['second_name']) == selected_player].iloc[0]
            
            # Swapped hardcoded #fff and dark backgrounds for var(--text-color) and var(--background-color)
            st.markdown(f"""
            <div class="scout-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="margin-bottom: 12px;">
                            <span class="badge-cyan" style="margin-right: 8px;">{p_data['position']}</span>
                            <span class="badge-pink">{p_data['team_name']}</span>
                        </div>
                        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800; color: var(--text-color
