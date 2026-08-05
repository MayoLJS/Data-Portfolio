import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="FPL Squad Architect & Scout", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp { background-color: #0b0e14; color: #e0e6ed; }
    section[data-testid="stSidebar"] { background-color: #121621; border-right: 1px solid #1e2638; }
    
    /* Custom Card Containers */
    .scout-card { background-color: #161b26; border: 1px solid #232b3e; border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    .pitch-card { background-color: #161b26; border: 1px solid #00f2fe; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .bench-card { background-color: #1e2638; border: 1px solid #ff007f; border-radius: 8px; padding: 10px; text-align: center; opacity: 0.8;}
    
    /* Pitch Background */
    .pitch-container { background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%); border-radius: 15px; padding: 20px; border: 2px solid #4caf50;}
    
    /* Badges */
    .badge-cyan { background-color: rgba(0, 242, 254, 0.15); color: #00f2fe; border: 1px solid #00f2fe; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .badge-pink { background-color: rgba(255, 0, 127, 0.15); color: #ff007f; border: 1px solid #ff007f; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    
    /* Progress Bars (Cyan Gradient) */
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #00c6ff, #00f2fe); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADERS (Cached)
# ==========================================
@st.cache_data(ttl=3600)
def load_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return None
    except: return None
    
    data = response.json()
    players = pd.DataFrame(data['elements'])
    teams = pd.DataFrame(data['teams'])
    
    players['team_name'] = players['team'].map(dict(zip(teams['id'], teams['name'])))
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'bps']
    for col in num_cols: players[col] = pd.to_numeric(players[col], errors='coerce').fillna(0.0)
            
    players['cost_m'] = players['now_cost'] / 10.0
    players['position'] = players['element_type'].map({1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'})
    return players

@st.cache_data(ttl=3600)
def load_match_data():
    # Make sure this matches your raw GitHub dataset URL exactly
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/02_Automated_Football_Analytics/data/pl_rolling_3_years_latest.csv"
    try:
        df = pd.read_csv(raw_url)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception:
        return pd.DataFrame()

players_df = load_fpl_data()
match_df = load_match_data()

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("⚽ SCOUT LAB PRO")
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("Select Module:", [
    "👤 Player Scout Card", 
    "⚡ FPL Squad Optimizer", 
    "📈 Team Betting Edge",
    "📊 Live League Table"
])

# ==========================================
# MODULE 1: PLAYER SCOUT CARD (With Filters)
# ==========================================
if app_mode == "👤 Player Scout Card":
    st.title("👤 Player Performance Profile")
    
    if players_df is not None and not players_df.empty:
        # Step 1: UI Filters
        f_col1, f_col2 = st.columns(2)
        teams_list = ["All"] + sorted(players_df['team_name'].unique().tolist())
        selected_team = f_col1.selectbox("Filter by Team:", teams_list)
        selected_pos = f_col2.selectbox("Filter by Position:", ["All", "GKP", "DEF", "MID", "FWD"])
        
        # Step 2: Apply Filters
        filtered_df = players_df.copy()
        if selected_team != "All": filtered_df = filtered_df[filtered_df['team_name'] == selected_team]
        if selected_pos != "All": filtered_df = filtered_df
