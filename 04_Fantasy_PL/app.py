import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (LIGHT/DARK COMPATIBLE)
# ==========================================
st.set_page_config(page_title="EPL Hub", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

# Using CSS variables so it adapts to Streamlit's native Light/Dark toggle
st.markdown("""
<style>
    /* Custom Card Containers using theme variables */
    .scout-card { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    .pitch-card { background-color: var(--secondary-background-color); border: 1px solid #00f2fe; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .bench-card { background-color: var(--background-color); border: 1px solid #ff007f; border-radius: 8px; padding: 10px; text-align: center; opacity: 0.8;}
    .fixture-card { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    
    /* Pitch Background - Kept green for realism */
    .pitch-container { background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%); border-radius: 15px; padding: 20px; border: 2px solid #4caf50; color: white; }
    
    /* Badges */
    .badge-cyan { background-color: rgba(0, 242, 254, 0.15); color: #0088cc; border: 1px solid #00f2fe; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .badge-pink { background-color: rgba(255, 0, 127, 0.15); color: #cc0066; border: 1px solid #ff007f; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .score-box { background-color: var(--background-color); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px 14px; font-size: 18px; font-weight: bold; letter-spacing: 2px; }
</style>
""", unsafe_allow_html=True)

# Determine chart theme based on Streamlit environment
chart_theme = "streamlit" 

# ==========================================
# 2. DATA LOADERS (Cached)
# ==========================================
@st.cache_data(ttl=3600)
def load_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: 
            return None, None
    except requests.exceptions.RequestException: 
        return None, None
    
    data = response.json()
    players = pd.DataFrame(data['elements'])
    teams = pd.DataFrame(data['teams'])
    
    players['team_name'] = players['team'].map(dict(zip(teams['id'], teams['name'])))
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'bps']
    
    for col in num_cols: 
        players[col] = pd.to_numeric(players[col], errors='coerce').fillna(0.0)
            
    players['cost_m'] = players['now_cost'] / 10.0
    players['position'] = players['element_type'].map({1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'})
    
    # Extract FDR Data (Next fixture difficulty)
    teams['FDR'] = teams['strength'] # Simplified placeholder for real FDR array logic
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
            
            st.markdown(f"""
            <div class="scout-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="badge-cyan">{p_data['position'].upper()}</span>
                        <span class="badge-pink">{p_data['team_name']}</span>
                        <h1 style="margin: 10px 0 0 0;">{p_data['first_name']} {p_data['second_name']}</h1>
                        <p style="margin: 0;">Price: £{p_data['cost_m']}M | Ownership: {p_data['selected_by_percent']}% | Points: {int(p_data['total_points'])}</p>
                    </div>
                    <div style="text-align: right;">
                        <h2 style="margin:0;">ICT: {p_data['ict_index']}</h2>
                        <p style="margin:0;">Form: {p_data['form']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- NEW INTERACTIVE GRID ---
            st.markdown("### 🔍 Interactive Player Database")
            grid_cols = ['first_name', 'second_name', 'team_name', 'position', 'cost_m', 'total_points', 'form', 'ict_index']
            gb = GridOptionsBuilder.from_dataframe(filtered_df[grid_cols])
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_default_column(editable=True, groupable=True, value=True, enableRowGroup=True, aggFunc='sum')
            gridOptions = gb.build()
            
            AgGrid(filtered_df[grid_cols], gridOptions=gridOptions, enable_enterprise_modules=False, height=400, fit_columns_on_grid_load=True)

        else:
            st.warning("No players found with these filters.")

# ==========================================
# MODULE 2: TEAM BETTING EDGE (PLOTLY THEMING)
# ==========================================
elif app_mode == "📈 Team Betting Edge":
    st.title("📈 Predictive Match Analytics")
    
    if match_df is not None and not match_df.empty:
        selected_season = st.selectbox("Select Season to Analyze:", sorted(match_df['Season'].unique().tolist(), reverse=True))
        szn_match_df = match_df[match_df['Season'] == selected_season]
        
        if not szn_match_df.empty:
            # Example metric manipulation
            home_m = szn_match_df[['Home_Team', 'Home_Score_FT', 'Away_Score_FT']].copy()
            home_m.columns = ['Team', 'Scored_FT', 'Conceded_FT']
            
            team_stats = home_m.groupby('Team').mean().reset_index()
            
            fig = px.scatter(team_stats, x='Conceded_FT', y='Scored_FT', text='Team', size='Scored_FT', color_discrete_sequence=['#00f2fe'])
            fig.update_traces(textposition='top center')
            
            # Dynamic theming applied
            fig.update_layout(title="Home Performance Matrix", template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULE 3: LIVE LEAGUE TABLE (AG-GRID)
# ==========================================
elif app_mode == "📊 Live League Table":
    st.title("📊 League Table & Trends")
    st.info("Ag-Grid interactive league table currently under construction for Phase 3 (xG Integration).")
