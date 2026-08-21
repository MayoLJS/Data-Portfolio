import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go
import re

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (LIGHT/DARK COMPATIBLE)
# ==========================================
st.set_page_config(page_title="EPL Hub", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Custom Card Containers */
    .scout-card { background: var(--secondary-background-color); border: 1px solid rgba(0, 136, 204, 0.3); border-radius: 12px; padding: 24px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .pitch-card { background: var(--secondary-background-color); border: 1px solid #00f2fe; border-radius: 10px; padding: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,242,254,0.1); position: relative; }
    .bench-card { background: var(--secondary-background-color); border: 1px solid #ff007f; border-radius: 10px; padding: 12px; text-align: center; position: relative;}
    .fixture-card { background: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease;}
    .fixture-card:hover { border-color: rgba(0, 136, 204, 0.5); box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
    
    /* Pitch Background */
    .pitch-container { background: linear-gradient(180deg, rgba(27, 67, 50, 0.25) 0%, rgba(45, 106, 79, 0.25) 100%); border-radius: 16px; padding: 25px; border: 1px solid rgba(76, 175, 80, 0.5); margin-bottom: 25px;}
    
    /* Badges */
    .badge-cyan { background: rgba(0, 242, 254, 0.15); color: #0088cc; border: 1px solid #00f2fe; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;}
    .badge-pink { background: rgba(255, 0, 127, 0.15); color: #cc0066; border: 1px solid #ff007f; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;}
    .badge-cap { background: #ffcc00; color: #000; border: 1px solid #d4af37; padding: 1px 5px; border-radius: 4px; font-size: 10px; font-weight: 900; margin-left: 4px;}
    .score-box { background: var(--background-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 8px 18px; font-size: 20px; font-weight: 800; letter-spacing: 3px; color: var(--text-color); }
    
    /* Leaderboard Styling */
    .leaderboard-item { font-size: 14px; padding: 8px 0; border-bottom: 1px solid var(--border-color); color: var(--text-color); }
    .leaderboard-stat { color: #0088cc; font-weight: 700; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

chart_theme = "streamlit"

def format_season(season_str):
    """Dynamically handles both '2025' and '2526' string formats"""
    season_str = str(season_str)
    if re.match(r'^20\d{2}$', season_str):
        # Format 2025 -> 2025/2026 Season
        next_year = int(season_str) + 1
        return f"{season_str}/{next_year} Season"
    elif re.match(r'^\d{4}$', season_str):
        # Format 2526 -> 2025/2026 Season
        return f"20{season_str[:2]}/20{season_str[2:]} Season"
    return season_str

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
    
    # Extract official FPL Predicted Points (ep_next)
    players['predicted_points'] = pd.to_numeric(players.get('ep_next', 0), errors='coerce').fillna(0.0)
    players['next_opponent'] = "N/A"
    
    # Fetch fixtures to get next opponent
    try:
        fix_response = requests.get("https://fantasy.premierleague.com/api/fixtures/?future=1", timeout=5)
        if fix_response.status_code == 200:
            fixtures = pd.DataFrame(fix_response.json())
            if not fixtures.empty and 'event' in fixtures.columns:
                next_event = fixtures['event'].dropna().min()
                next_fixtures = fixtures[fixtures['event'] == next_event]
                
                team_mapping = dict(zip(teams['id'], teams['short_name']))
                next_opp_dict = {}
                for _, row in next_fixtures.iterrows():
                    h_id = row['team_h']
                    a_id = row['team_a']
                    next_opp_dict[h_id] = f"{team_mapping.get(a_id, 'UNK')} (H)"
                    next_opp_dict[a_id] = f"{team_mapping.get(h_id, 'UNK')} (A)"
                
                players['next_opponent'] = players['team'].map(next_opp_dict).fillna("Blank GW")
    except Exception:
        pass
    
    if 'status' in players.columns:
        players['status'] = players['status'].fillna('a')
    else:
        players['status'] = 'a'
        
    if 'chance_of_playing_next_round' in players.columns:
        players['chance_of_playing_next_round'] = pd.to_numeric(players['chance_of_playing_next_round'], errors='coerce').fillna(100.0)
    else:
        players['chance_of_playing_next_round'] = 100.0
    
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'expected_goals', 'expected_assists', 'bps', 'minutes', 'goals_conceded', 'saves']
    
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

@st.cache_data(ttl=3600)
def load_understat_data():
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/04_Fantasy_PL/data/team_shooting.csv"
    try:
        df = pd.read_csv(raw_url)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception:
        return None

# Helper calculation engine for Benchwarmers V2 Logic
def calculate_v2_metrics(p_df, t_df, u_df, w_long=0.8, w_short=0.2, fa_boost=1.4, home_away_boost=0.05):
    if p_df is None or t_df is None:
        return pd.DataFrame()
        
    df = p_df.copy()
    df['full_name'] = df['first_name'] + " " + df['second_name']
    
    # Estimate base metrics & per 90
    df['mins_played'] = pd.to_numeric(df.get('minutes', 0), errors='coerce').fillna(0)
    df['xg_p90'] = np.where(df['mins_played'] > 90, (df['expected_goals'] / df['mins_played']) * 90, df['expected_goals'])
    df['xa_p90'] = np.where(df['mins_played'] > 90, (df['expected_assists'] / df['mins_played']) * 90, df['expected_assists'])
    
    # Opponent extraction
    df['is_home'] = df['next_opponent'].str.contains(r'\(H\)', regex=True)
    df['opp_short'] = df['next_opponent'].str.replace(' (H)', '', regex=False).str.replace(' (A)', '', regex=False)
    short_to_full = dict(zip(t_df['short_name'], t_df['name']))
    df['opp_name'] = df['opp_short'].map(short_to_full).fillna('Average Team')
    
    # Team stats from Understat or defaults
    t_stats = {}
    if u_df is not None and not u_df.empty:
        latest_szn = u_df['season'].max()
        curr = u_df[u_df['season'] == latest_szn]
        for t in curr['home_team'].unique():
            h = curr[curr['home_team'] == t]
            a = curr[curr['away_team'] == t]
            h_xg_col = 'home_xg' if 'home_xg' in curr.columns else 'home_xG'
            a_xg_col = 'away_xg' if 'away_xg' in curr.columns else 'away_xG'
            tot_xg = h[h_xg_col].sum() + a[a_xg_col].sum()
            tot_xgc = h[a_xg_col].sum() + a[h_xg_col].sum()
            m = len(h) + len(a)
            if m > 0:
                t_stats[t] = {'xg_p90': tot_xg / m, 'xgc_p90': tot_xgc / m}
                
    league_avg_xg = np.mean([v['xg_p90'] for v in t_stats.values()]) if t_stats else 1.35
    league_avg_xgc = np.mean([v['xgc_p90'] for v in t_stats.values()]) if t_stats else 1.35
    
    def get_stat(team_name, stat):
        m = {"Man City": "Manchester City", "Man Utd": "Manchester United", "Newcastle": "Newcastle United", "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Wolves": "Wolverhampton Wanderers"}
        name = m.get(team_name, team_name)
        return t_stats.get(name, {}).get(stat, league_avg_xg)
        
    df['team_xgc'] = df['team_name'].apply(lambda x: get_stat(x, 'xgc_p90'))
    df['opp_xg'] = df['opp_name'].apply(lambda x: get_stat(x, 'xg_p90'))
    df['opp_xgc'] = df['opp_name'].apply(lambda x: get_stat(x, 'xgc_p90'))
    
    # 1. Appearance Probabilities
    fit_prob = df['chance_of_playing_next_round'] / 100.0
    df['p_app_1'] = np.where(df['mins_played'] > 200, 0.95, 0.50) * fit_prob
    df['p_app_2'] = np.where(df['mins_played'] > 450, 0.85, 0.35) * fit_prob
    df['exp_app_pts'] = df['p_app_1'] * 1.0 + df['p_app_2'] * 1.0
    
    # 2. Attacking Points (Positional Goal values + 40% Fantasy Assist Boost)
    goal_pts_map = {1: 6, 2: 6, 3: 5, 4: 4}
    df['goal_val'] = df['element_type'].map(goal_pts_map)
    df['attack_mult'] = (df['opp_xgc'] / league_avg_xgc).clip(0.5, 2.0)
    df['exp_goal_pts'] = (df['xg_p90'] * df['goal_val']) * df['attack_mult']
    df['exp_assist_pts'] = (df['xa_p90'] * 3.0 * fa_boost) * df['attack_mult']
    
    # 3. Defensive Points (Poisson Clean Sheets + 2+ Conceded Penalty)
    df['def_mult'] = (df['opp_xg'] / league_avg_xg).clip(0.5, 2.0)
    df['match_xgc'] = df['team_xgc'] * df['def_mult']
    df['prob_cs'] = np.exp(-df['match_xgc']) # Poisson k=0
    df['prob_conc_2plus'] = 1.0 - np.exp(-df['match_xgc']) * (1.0 + df['match_xgc']) # Poisson k>=2
    
    df['cs_val'] = df['element_type'].map({1: 4.0, 2: 4.0, 3: 1.0, 4: 0.0})
    df['conc_penalty_val'] = df['element_type'].map({1: -1.0, 2: -1.0, 3: 0.0, 4: 0.0})
    
    df['exp_cs_pts'] = df['prob_cs'] * df['cs_val']
    df['exp_conc_penalty'] = df['prob_conc_2plus'] * df['conc_penalty_val']
    
    # 4. Defcon / BPS Approximation
    df['exp_bonus_pts'] = (df['bps'] / np.maximum(df['mins_played'], 1.0)) * 90.0 * 0.04
    
    # 5. Composite Raw xP & Home/Away adjustment
    df['raw_xp'] = df['exp_app_pts'] + df['exp_goal_pts'] + df['exp_assist_pts'] + df['exp_cs_pts'] + df['exp_conc_penalty'] + df['exp_bonus_pts']
    ha_factor = np.where(df['is_home'], 1.0 + home_away_boost, 1.0 - home_away_boost)
    df['v2_xp'] = (df['raw_xp'] * ha_factor).round(2)
    
    return df

players_df, teams_df = load_fpl_data()
match_df = load_match_data()
understat_shooting_df = load_understat_data() 

# ==========================================
# 3. SIDEBAR NAVIGATION (Subfolder Layout)
# ==========================================
st.sidebar.title("⚽ EPL HUB")
st.sidebar.markdown("---")

menu_category = st.sidebar.selectbox("Select Category:", ["Fantasy", "Fantasy V2 (Benchwarmers Model)", "Real", "Betting"])
st.sidebar.markdown("---")

if menu_category == "Fantasy":
    app_mode = st.sidebar.radio("Select Module:", [
        "👤 Player Scout Card", 
        "⚡ FPL Squad Optimizer"
    ])
elif menu_category == "Fantasy V2 (Benchwarmers Model)":
    app_mode = st.sidebar.radio("Select Module:", [
        "📊 Model Control Panel & Data Bank",
        "🧮 Points Breakdown Matrix",
        "📅 Fixture Multipliers & Opponent Index",
        "⚡ Prescriptive Solver & Sensitivity"
    ])
elif menu_category == "Real":
    app_mode = st.sidebar.radio("Select Module:", [
        "📅 Match Results & Fixtures",
        "📊 Live League Table",
        "📈 Team Trends (xG vs Actual)",
        "🌐 Understat Team Stats" 
    ])
elif menu_category == "Betting":
    app_mode = st.sidebar.radio("Select Module:", [
        "📈 For your information only"
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
            
            chance_val = int(p_data.get('chance_of_playing_next_round', 100)) if pd.notna(p_data.get('chance_of_playing_next_round')) else 100
            chance_color = "#01fc7a" if chance_val == 100 else ("#ffcc00" if chance_val > 0 else "#ff005a")
            
            st.markdown(f"""
            <div class="scout-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="margin-bottom: 12px;">
                            <span class="badge-cyan" style="margin-right: 8px;">{p_data['position']}</span>
                            <span class="badge-pink">{p_data['team_name']}</span>
                        </div>
                        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800; color: var(--text-color);">{p_data['first_name'].upper()} {p_data['second_name'].upper()}</h1>
                        <p style="margin: 8px 0 0 0; color: var(--text-color); opacity: 0.8; font-size: 1.1rem;">
                            Price: <b>£{p_data['cost_m']}M</b> &nbsp;|&nbsp; 
                            Ownership: <b>{p_data['selected_by_percent']}%</b> &nbsp;|&nbsp; 
                            Points: <b>{int(p_data['total_points'])}</b><br>
                            Next Opp: <b>{p_data.get('next_opponent', 'N/A')}</b> &nbsp;|&nbsp;
                            Proj Pts: <b style="color: #0088cc;">{p_data.get('predicted_points', 0.0)}</b> &nbsp;|&nbsp;
                            Fit: <b style="color: {chance_color};">{chance_val}%</b>
                        </p>
                    </div>
                    <div style="text-align: right; background: var(--background-color); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color);">
                        <h4 style="color: #0088cc; margin:0 0 5px 0; font-weight: 600;">xG: {p_data.get('expected_goals', 0.0):.2f}</h4>
                        <h4 style="color: #cc0066; margin:0 0 10px 0; font-weight: 600;">xA: {p_data.get('expected_assists', 0.0):.2f}</h4>
                        <div style="color: var(--text-color); font-size: 0.9rem;">Form: <b>{p_data['form']}</b> &nbsp;|&nbsp; ICT: <b>{p_data['ict_index']}</b></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat (Goal Danger)': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
            st.markdown("### 📊 Performance Percentiles")
            col1, col2 = st.columns(2)
            for i, (label, col_name) in enumerate(metrics.items()):
                if col_name in players_df.columns:
                    val = p_data[col_name]
                    percentile = int((players_df[col_name] < val).mean() * 100)
                    target_col = col1 if i < 3 else col2
                    with target_col:
                        st.markdown(f"<div style='margin-bottom:-10px; font-size: 14px; color: var(--text-color);'><b>{label}</b>: <span style='color:#0088cc;'>{val}</span> <span style='opacity: 0.6; font-size:12px;'>(Top {100-percentile}%)</span></div>", unsafe_allow_html=True)
                        st.progress(percentile / 100.0)
            
            st.markdown("<br><hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
            st.markdown("### 🏆 Top Performers by Metric")
            st.caption(f"Showing the best **{selected_pos if selected_pos != 'All' else 'Players'}** from **{selected_team if selected_team != 'All' else 'All Teams'}**.")
            
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            
            def display_top_5(df, metric_col, title, col):
                top_5 = df.sort_values(by=metric_col, ascending=False).head(5)
                with col:
                    st.markdown(f"<div style='background: var(--secondary-background-color); border: 1px solid var(--border-color); padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
                    st.markdown(f"<h5 style='color: var(--text-color); margin-top:0;'>{title}</h5>", unsafe_allow_html=True)
                    for _, row in top_5.iterrows():
                        st.markdown(f"<div class='leaderboard-item'><b>{row['first_name'][0]}. {row['second_name']}</b><br><span class='leaderboard-stat'>{row[metric_col]}</span> <span style='font-size:11px; opacity: 0.7;'>({row['team_name']})</span></div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                        
            display_top_5(filtered_df, 'threat', '🔥 Highest Threat', m_c1)
            display_top_5(filtered_df, 'creativity', '✨ Most Creative', m_c2)
            display_top_5(filtered_df, 'influence', '💪 Most Influential', m_c3)
            display_top_5(filtered_df, 'ict_index', '⭐ Overall ICT', m_c4)
            
            st.markdown("<br><hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
            st.markdown("### 🔍 Interactive Player Database")
            grid_cols = ['first_name', 'second_name', 'team_name', 'position', 'cost_m', 'total_points', 'next_opponent', 'predicted_points', 'expected_goals', 'expected_assists', 'ict_index', 'chance_of_playing_next_round']
            available_cols = [c for c in grid_cols if c in filtered_df.columns]
            
            st.dataframe(
                filtered_df[available_cols], 
                width="stretch", 
                hide_index=True,
                column_config={
                    "first_name": "First Name",
                    "second_name": "Last Name",
                    "team_name": "Club",
                    "position": "Pos",
                    "cost_m": st.column_config.NumberColumn("Price (£M)", format="£%.1f"),
                    "total_points": st.column_config.ProgressColumn("Total Pts", format="%d", min_value=0, max_value=int(players_df['total_points'].max())),
                    "next_opponent": "Next Match",
                    "predicted_points": st.column_config.NumberColumn("Proj Pts", format="%.1f"),
                    "expected_goals": st.column_config.NumberColumn("xG", format="%.2f"),
                    "expected_assists": st.column_config.NumberColumn("xA", format="%.2f"),
                    "ict_index": st.column_config.NumberColumn("ICT", format="%.1f"),
                    "chance_of_playing_next_round": st.column_config.NumberColumn("Fit %", format="%d%%")
                }
            )

        else:
            st.warning("No players found with these filters.")

# ==========================================
# MODULE 2: FPL SQUAD OPTIMIZER
# ==========================================
elif app_mode == "⚡ FPL Squad Optimizer":
    st.title("⚡ Prescriptive FPL Squad Optimizer")
    
    st.sidebar.header("1. Budget Constraints")
    budget = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.header("2. Bench Strategy")
    bench_weight = st.sidebar.slider("Bench Investment Weight", 0.0, 1.0, 0.1, 0.1, help="0.1 = Dump cheapest fodder on bench to maximize Starting XI. 1.0 = Spread budget equally (Bench Boost).")
    
    st.sidebar.header("3. Target Formation")
    formation_choices = ["Auto (Best Points)", "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"]
    target_formation = st.sidebar.selectbox("Preferred Starting Formation:", formation_choices)
    
    st.sidebar.header("4. Custom Strategy Weights")
    advanced_mode = st.sidebar.toggle("Advanced Metric Breakdown", value=False)
    
    if not advanced_mode:
        st.sidebar.info("💡 **Base Mode:** Uses bundled ICT Index alongside Form & Ownership.")
        w_form = st.sidebar.slider("Form (Short-Term)", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
        w_ict = st.sidebar.slider("ICT Index (Quality)", 0, 100, 40, 5)
        weights = {'form': w_form, 'selected_by_percent': w_own, 'ict_index': w_ict}
    else:
        st.sidebar.info("⚙️ **Advanced Mode:** Unbundles ICT into Influence, Creativity, and Threat.")
        w_form = st.sidebar.slider("Form", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership %", 0, 100, 20, 5)
        w_inf = st.sidebar.slider("Influence (Impact)", 0, 100, 20, 5)
        w_cre = st.sidebar.slider("Creativity (Assists)", 0, 100, 20, 5)
        w_thr = st.sidebar.slider("Threat (Goals)", 0, 100, 20, 5)
        weights = {'form': w_form, 'selected_by_percent': w_own, 'influence': w_inf, 'creativity': w_cre, 'threat': w_thr}

    total_w = sum(weights.values())
    if total_w > 0: weights = {k: v / total_w for k, v in weights.items()}

    st.sidebar.header("5. Locked Players (Optional)")
    if players_df is not None:
        player_choices = sorted((players_df['first_name'] + " " + players_df['second_name']).tolist())
        locked_players = st.sidebar.multiselect("Select up to 14 must-have players:", player_choices, max_selections=14)
    else:
        locked_players = []

    if st.button("🚀 Generate Optimal Squad", type="primary", width="stretch"):
        if players_df is not None:
            df = players_df.copy()
            df['full_name'] = df['first_name'] + " " + df['second_name']
            
            df = df[(df['status'] == 'a') | (df['full_name'].isin(locked_players))].copy()
            
            for metric in weights.keys():
                min_v, max_v = df[metric].min(), df[metric].max()
                df[f'{metric}_norm'] = (df[metric] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
            
            df['custom_score'] = sum(df[f'{metric}_norm'] * w for metric, w in weights.items())
                
            prob = pulp.LpProblem("Optimal_FPL_Squad", pulp.LpMaximize)
            squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
            starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
            bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
            
            prob += pulp.lpSum([df.loc[i, 'custom_score'] * starter_vars[i] + bench_weight * df.loc[i, 'custom_score'] * bench_vars[i] for i in df.index])
            
            for i in df.index:
                prob += squad_vars[i] == starter_vars[i] + bench_vars[i]
            
            prob += pulp.lpSum([df.loc[i, 'now_cost'] * squad_vars[i] for i in df.index]) <= (budget * 10) 
            prob += pulp.lpSum([squad_vars[i] for i in df.index]) == 15 
            prob += pulp.lpSum([starter_vars[i] for i in df.index]) == 11 
            prob += pulp.lpSum([bench_vars[i] for i in df.index]) == 4 
            
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3
            
            prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 1
            
            if target_formation == "Auto (Best Points)":
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) >= 3
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) >= 2
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) >= 1
            else:
                def_req, mid_req, fwd_req = map(int, target_formation.split('-'))
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == def_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == mid_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == fwd_req
            
            for t_id in df['team'].unique(): 
                prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
            
            locked_indices = df[df['full_name'].isin(locked_players)].index.tolist()
            for idx in locked_indices:
                prob += squad_vars[idx] == 1
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                squad = df.loc[[i for i in df.index if squad_vars[i].varValue == 1]].copy()
                starters = df.loc[[i for i in df.index if starter_vars[i].varValue == 1]].copy()
                bench_raw = df.loc[[i for i in df.index if bench_vars[i].varValue == 1]].copy()
                
                bench_gkp = bench_raw[bench_raw['element_type'] == 1]
                bench_outfield = bench_raw[bench_raw['element_type'] > 1].sort_values(by='custom_score', ascending=False)
                bench = pd.concat([bench_gkp, bench_outfield])

                # === CAPTAINCY & EXPECTED POINTS LOGIC ===
                captain_id = starters['predicted_points'].idxmax()
                captain_row = starters.loc[captain_id]
                
                # Sum of starting XI predicted points + Captain bonus (Captain points are doubled)
                total_expected_points = starters['predicted_points'].sum() + captain_row['predicted_points']

                st.success("✅ Optimization Complete!")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Spent", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget - squad['cost_m'].sum():.1f}M")
                c2.metric("Projected Points", f"{total_expected_points:.1f} pts", help="Starting XI xP + Captain Bonus")
                c3.metric("Starting XI Rating (/11.0)", f"{starters['custom_score'].sum():.2f}")
                c4.metric("Bench Rating (/4.0)", f"{bench['custom_score'].sum():.2f}")

                st.markdown("### 👑 Captaincy & Strategy")
                if captain_row['predicted_points'] >= 7.5:
                    st.success(f"🔥 **Triple Captain Alert:** **{captain_row['second_name']}** is projected for an elite **{captain_row['predicted_points']} points** against {captain_row.get('next_opponent', 'their next opponent')}. Consider using your Triple Captain chip!")
                else:
                    st.info(f"🛡️ **Captain Recommendation:** **{captain_row['second_name']}** (Projected: {captain_row['predicted_points']} pts). A Triple Captain chip is not highly advised this week.")


                st.markdown("### 🏟️ The Starting XI (with FDR)")
                st.caption("Dots indicate overall team strength: Green = Easy, Grey = Avg, Red = Hard")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                def get_fdr_style(val):
                    bg = {2: "#01fc7a", 3: "#94a3b8", 4: "#ff005a", 5: "#9f1239"}.get(val, "#94a3b8")
                    txt = "black" if val in [2, 3] else "white"
                    return f"background-color: {bg}; color: {txt};"

                def render_row(players_in_row, card_class='pitch-card'):
                    if not players_in_row.empty:
                        cols = st.columns(len(players_in_row))
                        for col, row_data in zip(cols, players_in_row.itertuples()):
                            strength_val = int(row_data.team_strength) if pd.notna(row_data.team_strength) else 3
                            inline_fdr = get_fdr_style(strength_val)
                            
                            chance_val = int(row_data.chance_of_playing_next_round) if pd.notna(row_data.chance_of_playing_next_round) else 100
                            chance_color = "#01fc7a" if chance_val == 100 else ("#ffcc00" if chance_val > 0 else "#ff005a")
                            
                            is_captain = (row_data.Index == captain_id)
                            cap_badge = "<span class='badge-cap'>C</span>" if is_captain and card_class == 'pitch-card' else ""
                            
                            col.markdown(f"""
                            <div class='{card_class}'>
                                <div style='position: absolute; top: -8px; right: -8px; padding: 4px 8px; border-radius: 50%; font-size: 11px; font-weight: bold; border: 1px solid var(--border-color); z-index: 10; {inline_fdr} box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                                    {strength_val}
                                </div>
                                <b style='color: var(--text-color); font-size: 14px;'>{row_data.second_name} {cap_badge}</b><br>
                                <span style='font-size:11px; opacity:0.8;'>{row_data.team_name}</span><br>
                                <span style='font-size:11px; color:#ff007f;'>vs {row_data.next_opponent}</span><br>
                                <span style='color:#0088cc; font-weight:800; font-size:13px;'>£{row_data.cost_m}m | xP: {row_data.predicted_points}</span><br>
                                <span style='font-size:10px; color:{chance_color}; font-weight:bold;'>Fit: {chance_val}%</span>
                            </div>
                            """, unsafe_allow_html=True)
                    st.write("") 

                render_row(starters[starters['element_type'] == 1]) 
                render_row(starters[starters['element_type'] == 2]) 
                render_row(starters[starters['element_type'] == 3]) 
                render_row(starters[starters['element_type'] == 4]) 
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("### 🪑 The Bench (Ordered by Priority)")
                render_row(bench, card_class='bench-card')

            else:
                st.error("⚠️ Optimizer could not find a valid squad. Try loosening your budget or removing locked players that violate rules/formation constraints.")

# ==========================================
# FANTASY V2 MODULE 1: MODEL CONTROL PANEL & DATA BANK
# ==========================================
elif app_mode == "📊 Model Control Panel & Data Bank":
    st.title("📊 Model Control Panel & Master Data Bank")
    st.write("Configure model multipliers and weights (Long-Form vs Short-Form, Understat corrections, Fantasy Assist Boost, and Home/Away factors).")
    
    c1, c2, c3, c4 = st.columns(4)
    w_long = c1.slider("Long-Form Form Weight", 0.0, 1.0, 0.80, 0.05, help="Weight given to full-season or rolling multi-season history.")
    w_short = c2.slider("Short-Form Form Weight", 0.0, 1.0, 0.20, 0.05, help="Weight given to recent 6 gameweeks.")
    fa_boost = c3.slider("Fantasy Assist Boost", 1.0, 1.8, 1.40, 0.05, help="The +40% multiplier for winning penalties, rebounds, and deflections.")
    ha_boost = c4.slider("Home / Away Factor", 0.0, 0.15, 0.05, 0.01, help="The 5% baseline advantage for home fixtures.")
    
    st.markdown("---")
    st.markdown("### 🗄️ Master Player Data Bank")
    
    v2_data = calculate_v2_metrics(players_df, teams_df, understat_shooting_df, w_long, w_short, fa_boost, ha_boost)
    if not v2_data.empty:
        cols_to_show = ['full_name', 'team_name', 'position', 'cost_m', 'minutes', 'xg_p90', 'xa_p90', 'team_xgc', 'opp_name', 'v2_xp']
        st.dataframe(
            v2_data[cols_to_show],
            width="stretch",
            hide_index=True,
            column_config={
                "full_name": "Player",
                "team_name": "Club",
                "position": "Pos",
                "cost_m": st.column_config.NumberColumn("Price (£M)", format="£%.1f"),
                "minutes": "Mins",
                "xg_p90": st.column_config.NumberColumn("xG / 90", format="%.2f"),
                "xa_p90": st.column_config.NumberColumn("xA / 90", format="%.2f"),
                "team_xgc": st.column_config.NumberColumn("Team xGC", format="%.2f"),
                "opp_name": "Opponent",
                "v2_xp": st.column_config.NumberColumn("Calculated xP", format="%.2f")
            }
        )

# ==========================================
# FANTASY V2 MODULE 2: POINTS BREAKDOWN MATRIX
# ==========================================
elif app_mode == "🧮 Points Breakdown Matrix":
    st.title("🧮 Points Breakdown Matrix")
    st.write("Detailed decomposition of expected points across Appearance, Attack, Poisson Defense, and Defcon/Bonus.")
    
    v2_data = calculate_v2_metrics(players_df, teams_df, understat_shooting_df)
    if not v2_data.empty:
        f1, f2 = st.columns(2)
        pos_filter = f1.selectbox("Filter Position:", ["All", "GKP", "DEF", "MID", "FWD"], key="matrix_pos")
        team_filter = f2.selectbox("Filter Club:", ["All"] + sorted(v2_data['team_name'].unique().tolist()), key="matrix_team")
        
        filtered_matrix = v2_data.copy()
        if pos_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['position'] == pos_filter]
        if team_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['team_name'] == team_filter]
        
        matrix_cols = ['full_name', 'position', 'team_name', 'exp_app_pts', 'exp_goal_pts', 'exp_assist_pts', 'prob_cs', 'exp_cs_pts', 'exp_conc_penalty', 'exp_bonus_pts', 'v2_xp']
        
        st.dataframe(
            filtered_matrix[matrix_cols].sort_values(by='v2_xp', ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "full_name": "Player",
                "position": "Pos",
                "team_name": "Club",
                "exp_app_pts": st.column_config.NumberColumn("App xP (1-60m)", format="%.2f"),
                "exp_goal_pts": st.column_config.NumberColumn("Goal xP", format="%.2f"),
                "exp_assist_pts": st.column_config.NumberColumn("Assist xP (FA+40%)", format="%.2f"),
                "prob_cs": st.column_config.NumberColumn("Poisson CS %", format="%.1f%%"),
                "exp_cs_pts": st.column_config.NumberColumn("Clean Sheet xP", format="%.2f"),
                "exp_conc_penalty": st.column_config.NumberColumn("2+ Goals Penalty", format="%.2f"),
                "exp_bonus_pts": st.column_config.NumberColumn("BPS / Defcon xP", format="%.2f"),
                "v2_xp": st.column_config.NumberColumn("Total xP", format="%.2f")
            }
        )

# ==========================================
# FANTASY V2 MODULE 3: FIXTURE MULTIPLIERS & OPPONENT INDEX
# ==========================================
elif app_mode == "📅 Fixture Multipliers & Opponent Index":
    st.title("📅 Fixture Multipliers & Opponent Index")
    st.write("Compare team attacks and defenses against the league average to view relative match difficulty multipliers.")
    
    v2_data = calculate_v2_metrics(players_df, teams_df, understat_shooting_df)
    if not v2_data.empty:
        team_summary = v2_data.groupby(['team_name', 'opp_name', 'is_home']).agg(
            Attack_Multiplier=('attack_mult', 'first'),
            Defensive_Multiplier=('def_mult', 'first'),
            Expected_CS_Chance=('prob_cs', 'first')
        ).reset_index()
        
        team_summary['Venue'] = np.where(team_summary['is_home'], 'Home', 'Away')
        
        st.dataframe(
            team_summary[['team_name', 'opp_name', 'Venue', 'Attack_Multiplier', 'Defensive_Multiplier', 'Expected_CS_Chance']],
            width="stretch",
            hide_index=True,
            column_config={
                "team_name": "Club",
                "opp_name": "Opponent",
                "Venue": "Venue",
                "Attack_Multiplier": st.column_config.NumberColumn("Attack Multiplier (xGC Rel)", format="%.2fx"),
                "Defensive_Multiplier": st.column_config.NumberColumn("Defense Multiplier (xG Rel)", format="%.2fx"),
                "Expected_CS_Chance": st.column_config.NumberColumn("Poisson Clean Sheet Prob", format="%.1f%%")
            }
        )

# ==========================================
# FANTASY V2 MODULE 4: PRESCRIPTIVE SOLVER & SENSITIVITY
# ==========================================
elif app_mode == "⚡ Prescriptive Solver & Sensitivity":
    st.title("⚡ Prescriptive Solver & Sensitivity Analysis")
    st.write("Integer programming squad optimizer powered by Benchwarmers Poisson and Opponent Multiplier metrics.")
    
    st.sidebar.header("1. Budget Constraints")
    budget_v2 = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5, key="solver_v2_budget")
    
    st.sidebar.header("2. Bench Strategy")
    bench_weight_v2 = st.sidebar.slider("Bench Investment Weight", 0.0, 1.0, 0.1, 0.1, key="solver_v2_bench")
    
    st.sidebar.header("3. Target Formation")
    formation_choices = ["Auto (Best Points)", "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"]
    target_formation_v2 = st.sidebar.selectbox("Preferred Starting Formation:", formation_choices, key="solver_v2_formation")

    v2_df = calculate_v2_metrics(players_df, teams_df, understat_shooting_df)
    
    if st.button("🚀 Run V2 Solver & Sensitivity", type="primary", width="stretch", key="solver_v2_btn"):
        if not v2_df.empty:
            df = v2_df[(v2_df['status'] == 'a')].copy()
            
            prob = pulp.LpProblem("Optimal_FPL_V2", pulp.LpMaximize)
            squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
            starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
            bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
            
            prob += pulp.lpSum([df.loc[i, 'v2_xp'] * starter_vars[i] + bench_weight_v2 * df.loc[i, 'v2_xp'] * bench_vars[i] for i in df.index])
            
            for i in df.index:
                prob += squad_vars[i] == starter_vars[i] + bench_vars[i]
            
            prob += pulp.lpSum([df.loc[i, 'now_cost'] * squad_vars[i] for i in df.index]) <= (budget_v2 * 10) 
            prob += pulp.lpSum([squad_vars[i] for i in df.index]) == 15 
            prob += pulp.lpSum([starter_vars[i] for i in df.index]) == 11 
            prob += pulp.lpSum([bench_vars[i] for i in df.index]) == 4 
            
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3
            
            prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 1
            
            if target_formation_v2 == "Auto (Best Points)":
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) >= 3
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) >= 2
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) >= 1
            else:
                def_req, mid_req, fwd_req = map(int, target_formation_v2.split('-'))
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == def_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == mid_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == fwd_req
            
            for t_id in df['team'].unique(): 
                prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                squad = df.loc[[i for i in df.index if squad_vars[i].varValue == 1]].copy()
                starters = df.loc[[i for i in df.index if starter_vars[i].varValue == 1]].copy()
                bench = df.loc[[i for i in df.index if bench_vars[i].varValue == 1]].copy()
                
                captain_id = starters['v2_xp'].idxmax()
                captain_row = starters.loc[captain_id]
                total_xp = starters['v2_xp'].sum() + captain_row['v2_xp']
                
                st.success("✅ V2 Squad Solution Computed!")
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Spent Budget", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget_v2 - squad['cost_m'].sum():.1f}M")
                sc2.metric("Projected Gameweek Points (xP)", f"{total_xp:.2f} pts")
                sc3.metric("Captain Pick", f"{captain_row['second_name']} ({captain_row['v2_xp']} xP)")
                
                st.markdown("### 🏟️ Starting XI")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                def render_v2_pitch(row_df):
                    if not row_df.empty:
                        cols = st.columns(len(row_df))
                        for col, p in zip(cols, row_df.itertuples()):
                            cap = "<span class='badge-cap'>C</span>" if p.Index == captain_id else ""
                            col.markdown(f"""
                            <div class='pitch-card'>
                                <b style='color: var(--text-color); font-size: 14px;'>{p.second_name} {cap}</b><br>
                                <span style='font-size:11px; opacity:0.8;'>{p.team_name}</span><br>
                                <span style='font-size:11px; color:#ff007f;'>vs {p.next_opponent}</span><br>
                                <span style='color:#0088cc; font-weight:800; font-size:13px;'>£{p.cost_m}m | xP: {p.v2_xp:.2f}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    st.write("")
                    
                render_v2_pitch(starters[starters['element_type'] == 1])
                render_v2_pitch(starters[starters['element_type'] == 2])
                render_v2_pitch(starters[starters['element_type'] == 3])
                render_v2_pitch(starters[starters['element_type'] == 4])
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("### 🔍 Sensitivity & Close Misses")
                st.caption("Top players with highest xP who barely missed the budget or team constraint thresholds:")
                
                unpicked = df[~df.index.isin(squad.index)].sort_values(by='v2_xp', ascending=False).head(8)
                st.dataframe(
                    unpicked[['full_name', 'team_name', 'position', 'cost_m', 'v2_xp', 'next_opponent']],
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "full_name": "Player",
                        "team_name": "Club",
                        "position": "Pos",
                        "cost_m": st.column_config.NumberColumn("Price (£M)", format="£%.1f"),
                        "v2_xp": st.column_config.NumberColumn("Expected Points (xP)", format="%.2f"),
                        "next_opponent": "Fixture"
                    }
                )
            else:
                st.error("No optimal solution found for the current constraints.")

# ==========================================
# MODULE 3: TEAM Betting EDGE (For your information only)
# ==========================================
elif app_mode == "📈 For your information only":
    st.title("📈 Predictive Match Analytics")
    
    if match_df is not None and not match_df.empty:
        available_seasons = sorted(match_df['Season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season to Analyze:", available_seasons, format_func=format_season)
        
        szn_match_df = match_df[match_df['Season'] == selected_season_raw]
        
        if not szn_match_df.empty:
            home_m = szn_match_df[['Match_ID', 'Home_Team', 'Home_Score_HT', 'Away_Score_HT', 'Home_Score_FT', 'Away_Score_FT']].copy()
            home_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
            home_m['Venue'] = 'Home'
            
            away_m = szn_match_df[['Match_ID', 'Away_Team', 'Away_Score_HT', 'Home_Score_HT', 'Away_Score_FT', 'Home_Score_FT']].copy()
            away_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
            away_m['Venue'] = 'Away'
            
            fact_matches = pd.concat([home_m, away_m], ignore_index=True)
            fact_matches['HT_Status'] = np.where(fact_matches['Scored_HT'] > fact_matches['Conceded_HT'], 'Winning',
                                                 np.where(fact_matches['Scored_HT'] < fact_matches['Conceded_HT'], 'Losing', 'Drawing'))
            fact_matches['FT_Status'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 'Win',
                                                 np.where(fact_matches['Scored_FT'] < fact_matches['Conceded_FT'], 'Loss', 'Draw'))
            
            tab1, tab2, tab3, tab4 = st.tabs(["🔄 Losing at HT", "🛡️ Winning at HT", "🏠 Home vs Away", "🎯 Chaos Quadrant"])
            
            with tab1:
                losing_ht = fact_matches[fact_matches['HT_Status'] == 'Losing']
                fig1 = px.histogram(losing_ht, y="Team", color="FT_Status", title=f"Match Outcomes When Trailing at HT ({format_season(selected_season_raw)})",
                                    color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig1, width="stretch")
                
            with tab2:
                winning_ht = fact_matches[fact_matches['HT_Status'] == 'Winning']
                fig2 = px.histogram(winning_ht, y="Team", color="FT_Status", title=f"Match Outcomes When Leading at HT ({format_season(selected_season_raw)})",
                                    color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig2, width="stretch")
                
            with tab3:
                ha_stats = fact_matches.groupby(['Team', 'Venue']).size().reset_index(name='Matches')
                ha_wins = fact_matches[fact_matches['FT_Status'] == 'Win'].groupby(['Team', 'Venue']).size().reset_index(name='Wins')
                ha_merged = pd.merge(ha_stats, ha_wins, on=['Team', 'Venue'], how='left').fillna(0)
                ha_merged['Win_Rate'] = (ha_merged['Wins'] / ha_merged['Matches']) * 100
                
                fig3 = px.bar(ha_merged, x="Team", y="Win_Rate", color="Venue", barmode="group", title=f"Win Rate %: Home vs Away ({format_season(selected_season_raw)})",
                              color_discrete_map={'Home': '#0088cc', 'Away': '#cc0066'})
                fig3.update_layout(template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig3, width="stretch")

            with tab4:
                pts_map = {'Win': 3, 'Draw': 1, 'Loss': 0}
                fact_matches['Pts'] = fact_matches['FT_Status'].map(pts_map)
                
                team_stats = fact_matches.groupby('Team').agg(
                    Avg_Scored=('Scored_FT', 'mean'), 
                    Avg_Conceded=('Conceded_FT', 'mean'),
                    Total_Pts=('Pts', 'sum')
                ).reset_index()
                
                fig4 = px.scatter(team_stats, x='Avg_Conceded', y='Avg_Scored', text='Team', 
                                  size='Total_Pts', size_max=25,
                                  color_discrete_sequence=['#0088cc'])
                fig4.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='DarkSlateGrey')))
                
                x_mean = team_stats['Avg_Conceded'].mean()
                y_mean = team_stats['Avg_Scored'].mean()
                x_min = max(0, team_stats['Avg_Conceded'].min() - 0.5)
                x_max = team_stats['Avg_Conceded'].max() + 0.5
                y_min = max(0, team_stats['Avg_Scored'].min() - 0.5)
                y_max = team_stats['Avg_Scored'].max() + 0.5
                
                fig4.add_hline(y=y_mean, line_dash="dash", line_color="#cc0066", annotation_text="Avg Scored")
                fig4.add_vline(x=x_mean, line_dash="dash", line_color="#cc0066", annotation_text="Avg Conceded")
                
                fig4.add_shape(type="rect", x0=x_min, x1=x_mean, y0=y_mean, y1=y_max, fillcolor="rgba(0, 136, 204, 0.1)", line_width=0, layer="below")
                fig4.add_shape(type="rect", x0=x_mean, x1=x_max, y0=y_min, y1=y_mean, fillcolor="rgba(204, 0, 102, 0.1)", line_width=0, layer="below")
                
                fig4.add_annotation(x=x_min + (x_mean-x_min)/2, y=y_max-0.1, text="🔥 Elite", showarrow=False, font=dict(color="#0088cc", size=16))
                fig4.add_annotation(x=x_max - (x_max-x_mean)/2, y=y_max-0.1, text="🎭 Entertainers", showarrow=False, font=dict(color="#8f9bba", size=14))
                fig4.add_annotation(x=x_min + (x_mean-x_min)/2, y=y_min+0.1, text="🛡️ Park the Bus", showarrow=False, font=dict(color="#8f9bba", size=14))
                fig4.add_annotation(x=x_max - (x_max-x_mean)/2, y=y_min+0.1, text="📉 Strugglers", showarrow=False, font=dict(color="#cc0066", size=14))
                
                fig4.update_layout(title=f"The Chaos Quadrant ({format_season(selected_season_raw)}) - Bubble Size = Total Points", 
                                   xaxis_title="Average Goals Conceded (Fewer is Better)",
                                   yaxis_title="Average Goals Scored (More is Better)",
                                   xaxis=dict(range=[x_min, x_max]),
                                   yaxis=dict(range=[y_min, y_max]),
                                   template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig4, width="stretch")
        else:
            st.warning("No matches found for this season/filter.")
    else:
        st.warning("Match dataset is currently loading or unavailable.")

# ==========================================
# MODULE 4: MATCH RESULTS & FIXTURES
# ==========================================
elif app_mode == "📅 Match Results & Fixtures":
    st.title("📅 Match Results & Fixtures")
    st.write("Browse actual match scores alongside Understat Expected Goals (xG), filtered by Gameweek.")
    
    if understat_shooting_df is not None and not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season:", available_seasons, format_func=format_season)
        
        szn_matches = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].copy()
        
        if not szn_matches.empty:
            szn_matches = szn_matches.sort_values('date', ascending=True)
            szn_matches['gameweek'] = (szn_matches.groupby('season').cumcount() // 10) + 1
            
            max_gw = int(szn_matches['gameweek'].max())
            gw_list = [f"Gameweek {i}" for i in range(1, max_gw + 1)]
            
            selected_gw_str = st.selectbox("Select Matchweek:", gw_list)
            selected_gw_num = int(selected_gw_str.split(" ")[1])
            
            gw_matches = szn_matches[szn_matches['gameweek'] == selected_gw_num].sort_values('date')
            
            st.markdown(f"### 🗓️ {format_season(selected_season_raw)} - {selected_gw_str}")
            st.markdown("---")
            
            if not gw_matches.empty:
                for _, row in gw_matches.iterrows():
                    match_date = row['date'].strftime('%d %b %Y')
                    h_team = row['home_team']
                    a_team = row['away_team']
                    h_score = int(row['home_goals'])
                    a_score = int(row['away_goals'])
                    
                    h_xg = float(row.get('home_xG', row.get('home_xg', 0.0)))
                    a_xg = float(row.get('away_xG', row.get('away_xg', 0.0)))
                    
                    st.markdown(f"""
                    <div class="fixture-card">
                        <div style="width: 35%; text-align: right;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-color);">{h_team}</div>
                            <div style="font-size: 0.85rem; color: #0088cc;">xG: {h_xg:.2f}</div>
                        </div>
                        <div style="width: 30%; display: flex; flex-direction: column; align-items: center;">
                            <div class="score-box">{h_score} <span style='opacity:0.5'>-</span> {a_score}</div>
                            <span style="font-size: 0.8rem; margin-top: 6px; color: var(--text-color); opacity: 0.7; text-transform: uppercase;">{match_date}</span>
                        </div>
                        <div style="width: 35%; text-align: left;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-color);">{a_team}</div>
                            <div style="font-size: 0.85rem; color: #cc0066;">xG: {a_xg:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No fixtures found for this gameweek.")
        else:
            st.warning("No matches found for this season.")
    else:
        st.warning("Understat Match dataset is currently loading or unavailable.")

# ==========================================
# MODULE 5: LIVE LEAGUE TABLE (Upgraded with xG)
# ==========================================
elif app_mode == "📊 Live League Table":
    st.title("📊 Expected vs Actual League Table")
    
    if understat_shooting_df is not None and not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season to Analyze:", available_seasons, format_func=format_season)
        
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date')
        
        if not szn_df.empty:
            teams = pd.concat([szn_df['home_team'], szn_df['away_team']]).unique()
            team_records = {team: {'W': 0, 'D': 0, 'L': 0, 'Pts': 0, 'GD': 0, 'GF': 0, 'GA': 0, 'xG': 0.0, 'xGA': 0.0, 'xPts': 0.0, 'Matches': 0} for team in teams}

            for _, row in szn_df.iterrows():
                home = row['home_team']
                away = row['away_team']
                h_score = row['home_goals']
                a_score = row['away_goals']
                
                team_records[home]['Matches'] += 1
                team_records[away]['Matches'] += 1
                
                team_records[home]['GF'] += h_score
                team_records[home]['GA'] += a_score
                team_records[home]['GD'] += (h_score - a_score)
                team_records[home]['xG'] += float(row.get('home_xG', row.get('home_xg', 0.0)))
                team_records[home]['xGA'] += float(row.get('away_xG', row.get('away_xg', 0.0)))
                team_records[home]['xPts'] += float(row.get('home_expected_points', row.get('home_xpts', 0.0)))
                
                team_records[away]['GF'] += a_score
                team_records[away]['GA'] += h_score
                team_records[away]['GD'] += (a_score - h_score)
                team_records[away]['xG'] += float(row.get('away_xG', row.get('away_xg', 0.0)))
                team_records[away]['xGA'] += float(row.get('home_xG', row.get('home_xg', 0.0)))
                team_records[away]['xPts'] += float(row.get('away_expected_points', row.get('away_xpts', 0.0)))
                
                if h_score > a_score:
                    team_records[home]['Pts'] += 3
                    team_records[home]['W'] += 1
                    team_records[away]['L'] += 1
                elif a_score > h_score:
                    team_records[away]['Pts'] += 3
                    team_records[away]['W'] += 1
                    team_records[home]['L'] += 1
                else:
                    team_records[home]['Pts'] += 1
                    team_records[away]['Pts'] += 1
                    team_records[home]['D'] += 1
                    team_records[away]['D'] += 1
            
            final_table = []
            for team, stats in team_records.items():
                final_table.append({'Club': team, 'MP': stats['Matches'], 'Pts': stats['Pts'], 'xPts': stats['xPts'], 'GD': stats['GD'], 'GF': stats['GF'], 'xG': stats['xG'], 'GA': stats['GA'], 'xGA': stats['xGA']})
            
            table_df = pd.DataFrame(final_table).sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
            table_df.index += 1
            
            st.dataframe(
                table_df, 
                width="stretch",
                column_config={
                    "Pts": st.column_config.ProgressColumn("Pts", format="%d", min_value=0, max_value=int(table_df['Pts'].max())),
                    "xPts": st.column_config.NumberColumn("xPts", format="%.1f"),
                    "GD": st.column_config.NumberColumn("GD"),
                    "xG": st.column_config.NumberColumn("xG", format="%.1f"),
                    "xGA": st.column_config.NumberColumn("xGA", format="%.1f")
                }
            )
        else:
            st.warning("No matches found for this filter.")
    else:
        st.warning("Understat dataset is currently loading or unavailable.")

# ==========================================
# MODULE 6: TEAM TRENDS (xG vs Actual)
# ==========================================
elif app_mode == "📈 Team Trends (xG vs Actual)":
    st.title("📈 Team Trends: Expected vs Actual")
    st.write("Track a team's cumulative performance over the season (up to 38 gameweeks), comparing actual results against expected metrics.")
    
    if understat_shooting_df is not None and not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season to Analyze:", available_seasons, format_func=format_season)
        
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date')
        
        if not szn_df.empty:
            teams = sorted(list(set(szn_df['home_team'].tolist() + szn_df['away_team'].tolist())))
            
            col1, col2 = st.columns(2)
            selected_team = col1.selectbox("Select Team:", teams, index=0)
            metric_choice = col2.selectbox("Select Metric:", ["Goals For", "Goals Against", "Points"])
            
            team_matches = szn_df[(szn_df['home_team'] == selected_team) | (szn_df['away_team'] == selected_team)].copy()
            
            if not team_matches.empty:
                actual_vals = []
                expected_vals = []
                
                for _, row in team_matches.iterrows():
                    is_home = (row['home_team'] == selected_team)
                    
                    h_score = row['home_goals']
                    a_score = row['away_goals']
                    h_xg = float(row.get('home_xG', row.get('home_xg', 0.0)))
                    a_xg = float(row.get('away_xG', row.get('away_xg', 0.0)))
                    h_xpts = float(row.get('home_expected_points', row.get('home_xpts', 0.0)))
                    a_xpts = float(row.get('away_expected_points', row.get('away_xpts', 0.0)))
                    
                    if metric_choice == "Goals For":
                        actual_vals.append(h_score if is_home else a_score)
                        expected_vals.append(h_xg if is_home else a_xg)
                    elif metric_choice == "Goals Against":
                        actual_vals.append(a_score if is_home else h_score)
                        expected_vals.append(a_xg if is_home else h_xg)
                    elif metric_choice == "Points":
                        gf = h_score if is_home else a_score
                        ga = a_score if is_home else h_score
                        pts = 3 if gf > ga else (1 if gf == ga else 0)
                        xpts = h_xpts if is_home else a_xpts
                        
                        actual_vals.append(pts)
                        expected_vals.append(xpts)
                        
                trend_df = pd.DataFrame({
                    'Gameweek': range(1, len(actual_vals) + 1),
                    'Actual': np.cumsum(actual_vals),
                    'Expected': np.cumsum(expected_vals)
                })
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=trend_df['Gameweek'], 
                    y=trend_df['Actual'], 
                    mode='lines+markers',
                    name=f'Actual {metric_choice}',
                    line=dict(color='#0088cc', width=3, dash='solid'),
                    marker=dict(size=6)
                ))
                
                fig.add_trace(go.Scatter(
                    x=trend_df['Gameweek'], 
                    y=trend_df['Expected'], 
                    mode='lines',
                    name=f'Expected {metric_choice} (xG/xPts)',
                    line=dict(color='#cc0066', width=3, dash='dot')
                ))
                
                fig.update_layout(
                    title=f"{selected_team} - Cumulative {metric_choice} ({format_season(selected_season_raw)})",
                    xaxis_title="Matches Played (Gameweek)",
                    yaxis_title=f"Cumulative {metric_choice}",
                    xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                    template=chart_theme,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    hovermode='x unified',
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No matches found for this team in the selected season.")
        else:
            st.warning("No matches found for this filter.")
    else:
        st.warning("Understat dataset is currently loading or unavailable.")

# ==========================================
# MODULE 7: UNDERSTAT TEAM STATS (soccerdata)
# ==========================================
elif app_mode == "🌐 Understat Team Stats":
    st.title("🌐 Understat Team Match Stats")
    st.write("Aggregated team match statistics directly from Understat (via `soccerdata`).")

    if understat_shooting_df is not None:
        st.dataframe(understat_shooting_df, width="stretch")
    else:
        st.error("⚠️ Understat data could not be loaded at this time. Please ensure the CSV exists in your repository.")
