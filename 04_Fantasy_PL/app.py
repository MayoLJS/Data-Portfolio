import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go
import re
import math
from streamlit_echarts import st_echarts

# ==========================================
# 1. PAGE CONFIG & CLAUDE AESTHETIC CSS
# ==========================================
st.set_page_config(page_title="EPL Hub", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Lora:ital,wght@0,400;0,600;1,400&family=Fira+Code:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #2D2D2D;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Lora', serif !important;
        color: #1A1A1A;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    .score-box, .stMetricValue, .leaderboard-stat {
        font-family: 'Fira Code', monospace !important;
    }

    .scout-card { 
        background: #FFFFFF; 
        border: 1px solid #E5E2DC; 
        border-radius: 12px; 
        padding: 24px; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); 
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .scout-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }
    
    /* Responsive Flexbox Pitch */
    .pitch-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 12px;
        margin-bottom: 20px;
    }
    
    .pitch-card-wrapper {
        flex: 1 1 120px;
        max-width: 150px;
    }

    .pitch-card, .bench-card { 
        background: #FFFFFF; 
        border-radius: 8px; 
        padding: 12px; 
        text-align: center; 
        position: relative;
        border: 1px solid #E5E2DC;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        height: 100%;
    }
    .pitch-card { border-top: 3px solid #D97757; } 
    .bench-card { border-top: 3px solid #8C8C8C; } 
    
    .pitch-container { 
        background: linear-gradient(180deg, #F5F4F0 0%, #EBEAE5 100%); 
        border-radius: 16px; 
        padding: 30px; 
        border: 1px solid #E5E2DC; 
        margin-bottom: 30px;
    }

    .fixture-card { 
        background: #FFFFFF; 
        border: 1px solid #E5E2DC; 
        border-radius: 12px; 
        padding: 18px 24px; 
        margin-bottom: 14px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        transition: all 0.2s ease;
    }
    .fixture-card:hover { 
        border-color: #D97757; 
        box-shadow: 0 4px 12px rgba(217, 119, 87, 0.08); 
    }
    
    .badge-cyan { background: #F4EBE8; color: #D97757; border: 1px solid #EADAD5; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
    .badge-pink { background: #F0EFEA; color: #555555; border: 1px solid #E0DFDA; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
    .badge-cap { background: #E5E2DC; color: #1A1A1A; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-left: 6px; border: 1px solid #D1CDC4;}
    
    .score-box { background: #F9F8F6; border: 1px solid #E5E2DC; border-radius: 8px; padding: 8px 18px; font-size: 20px; font-weight: 700; letter-spacing: 1px; color: #1A1A1A; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AUTHENTICATION GATEKEEPER
# ==========================================
try:
    VALID_USERS = st.secrets["passwords"]
except KeyError:
    VALID_USERS = {"olu": "admin123", "2783761": "2783761", "friend1": "passcode1", "2000000": "2000000"}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔐 EPL Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8C8C8C;'>Secure analytical access required.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='background: #FFFFFF; padding: 30px; border-radius: 12px; border: 1px solid #E5E2DC; box-shadow: 0 4px 16px rgba(0,0,0,0.03);'>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            user_str = str(username).strip()
            if user_str in VALID_USERS and str(VALID_USERS[user_str]) == str(password):
                st.session_state["authenticated"] = True
                
                if user_str.lower() == "olu" or user_str == "2783761":
                    st.session_state["default_manager_id"] = "2783761"
                    st.session_state["default_league_id"] = "685121"
                else:
                    st.session_state["default_manager_id"] = user_str if user_str.isdigit() else ""
                    st.session_state["default_league_id"] = ""
                    
                st.rerun()
            else:
                st.error("⚠️ Invalid Username or Password")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. TEAM NAME STANDARDIZATION
# ==========================================
TEAM_NAME_STANDARDIZATION = {
    "Man City": "Manchester City",
    "Man Utd": "Manchester United",
    "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest",
    "Spurs": "Tottenham",
    "Wolves": "Wolverhampton Wanderers",
    "Sheffield Utd": "Sheffield United",
    "Luton Town": "Luton"
}

def standardize_team(team_str):
    if not isinstance(team_str, str): return "Unknown"
    return TEAM_NAME_STANDARDIZATION.get(team_str.strip(), team_str.strip())

def format_season(season_str):
    season_str = str(season_str)
    if re.match(r'^20\d{2}$', season_str):
        next_year = int(season_str) + 1
        return f"{season_str}/{next_year} Season"
    elif re.match(r'^\d{4}$', season_str):
        return f"20{season_str[:2]}/20{season_str[2:]} Season"
    return season_str

# ==========================================
# 4. BULLETPROOF DATA LOADERS
# ==========================================
@st.cache_data(ttl=3600)
def get_current_event():
    try:
        r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=5).json()
        for e in r['events']:
            if e['is_current']: return e['id']
        return 1
    except requests.exceptions.RequestException: return 1

@st.cache_data(ttl=3600)
def fetch_manager_squad(manager_id, curr_event):
    try:
        r = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{curr_event}/picks/", timeout=10).json()
        if 'picks' in r:
            my_elements = [p['element'] for p in r['picks']]
            manager_bank = r['entry_history']['bank'] / 10.0
            return my_elements, manager_bank
    except Exception: pass
    return None, 0.0

@st.cache_data(ttl=3600)
def load_fpl_all_fixtures():
    try:
        r = requests.get("https://fantasy.premierleague.com/api/fixtures/", timeout=10).json()
        df_fix = pd.DataFrame(r)
        boot = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10).json()
        team_map = {t['id']: standardize_team(t['name']) for t in boot['teams']}
        df_fix['home_team'] = df_fix['team_h'].map(team_map)
        df_fix['away_team'] = df_fix['team_a'].map(team_map)
        return df_fix[['event', 'home_team', 'away_team', 'team_h_score', 'team_a_score', 'finished', 'kickoff_time']].dropna(subset=['event'])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return pd.DataFrame(), pd.DataFrame()
    except requests.exceptions.RequestException: 
        return pd.DataFrame(), pd.DataFrame()
    
    data = response.json()
    players = pd.DataFrame(data['elements'])
    teams = pd.DataFrame(data['teams'])
    
    teams['standard_name'] = teams['name'].apply(standardize_team)
    players['team_name'] = players['team'].map(dict(zip(teams['id'], teams['standard_name'])))
    players['team_strength'] = players['team'].map(dict(zip(teams['id'], teams['strength']))).fillna(3)
    players['predicted_points'] = pd.to_numeric(players.get('ep_next', 0), errors='coerce').fillna(0.0)
    
    try:
        fix_response = requests.get("https://fantasy.premierleague.com/api/fixtures/?future=1", timeout=10)
        if fix_response.status_code == 200:
            fixtures = pd.DataFrame(fix_response.json())
            if not fixtures.empty and 'event' in fixtures.columns:
                future_events = sorted(fixtures['event'].dropna().unique())[:5]
                team_mapping = dict(zip(teams['id'], teams['short_name']))
                team_fixtures = {t_id: {'opps': [], 'is_home': [], 'fdr': []} for t_id in teams['id']}
                
                for event in future_events:
                    ev_fix = fixtures[fixtures['event'] == event]
                    for _, row in ev_fix.iterrows():
                        h_id, a_id = row['team_h'], row['team_a']
                        h_fdr, a_fdr = row['team_h_difficulty'], row['team_a_difficulty']
                        
                        team_fixtures[h_id]['opps'].append(team_mapping.get(a_id, 'UNK'))
                        team_fixtures[h_id]['is_home'].append(True)
                        team_fixtures[h_id]['fdr'].append(h_fdr)
                        
                        team_fixtures[a_id]['opps'].append(team_mapping.get(h_id, 'UNK'))
                        team_fixtures[a_id]['is_home'].append(False)
                        team_fixtures[a_id]['fdr'].append(a_fdr)
                        
                players['next_5_opps'] = players['team'].map(lambda x: team_fixtures.get(x, {}).get('opps', []))
                players['next_5_is_home'] = players['team'].map(lambda x: team_fixtures.get(x, {}).get('is_home', []))
                players['next_5_fdr'] = players['team'].map(lambda x: team_fixtures.get(x, {}).get('fdr', []))
                
                players['next_opponent'] = players['team'].map(
                    lambda x: f"{team_fixtures.get(x, {}).get('opps', [''])[0]} ({'H' if team_fixtures.get(x, {}).get('is_home', [True])[0] else 'A'})" if team_fixtures.get(x, {}).get('opps') else "Blank GW"
                )
    except Exception:
        players['next_5_opps'] = [[] for _ in range(len(players))]
        players['next_5_is_home'] = [[] for _ in range(len(players))]
        players['next_5_fdr'] = [[] for _ in range(len(players))]
        players['next_opponent'] = "N/A"
    
    players['status'] = players.get('status', 'a').fillna('a')
    players['chance_of_playing_next_round'] = pd.to_numeric(players.get('chance_of_playing_next_round', 100), errors='coerce').fillna(100.0)
    
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'expected_goals', 'expected_assists', 'bps', 'minutes', 'goals_conceded', 'saves']
    for col in num_cols: 
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors='coerce').fillna(0.0)
            
    players['cost_m'] = players['now_cost'] / 10.0
    players['position'] = players['element_type'].map({1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'})
    
    return players, teams

@st.cache_data(ttl=3600)
def load_match_data():
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/04_Fantasy_PL/data/pl_rolling_3_years_latest.csv"
    try:
        df = pd.read_csv(raw_url)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_understat_data(fpl_fixtures_df):
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/04_Fantasy_PL/data/team_shooting.csv"
    try:
        df = pd.read_csv(raw_url)
        df['date'] = pd.to_datetime(df['date'])
        
        # Protect against KeyErrors
        if 'home_team' not in df.columns and 'h_team' in df.columns: df['home_team'] = df['h_team']
        if 'away_team' not in df.columns and 'a_team' in df.columns: df['away_team'] = df['a_team']
            
        df['home_team_std'] = df['home_team'].apply(standardize_team)
        df['away_team_std'] = df['away_team'].apply(standardize_team)
        
        # BRIDGE: Perfect Gameweek Sync via FPL Fixture Map (Fixes Monday/DGW bug)
        if not fpl_fixtures_df.empty:
            fpl_map = fpl_fixtures_df.set_index(['home_team', 'away_team'])['event'].to_dict()
            df['gameweek'] = df.apply(lambda r: fpl_map.get((r['home_team_std'], r['away_team_std']), np.nan), axis=1)
            df['gameweek'] = df['gameweek'].fillna((df.groupby('season').cumcount() // 10) + 1).astype(int)
        else:
            df['gameweek'] = (df.groupby('season').cumcount() // 10) + 1
            
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_understat_shots():
    """Robust scraper mapper ensuring no KeyErrors occur regardless of source formatting."""
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/04_Fantasy_PL/data/understat_shots.csv"
    try:
        df = pd.read_csv(raw_url)
        
        # 1. Exhaustive Column Normalization
        col_map = {}
        for c in df.columns:
            cl = str(c).lower().strip()
            if cl in ['xg', 'expected_goals', 'shot_expected_goals']: col_map[c] = 'xG'
            elif cl in ['x', 'start_x', 'location_x', 'pos_x']: col_map[c] = 'X'
            elif cl in ['y', 'start_y', 'location_y', 'pos_y']: col_map[c] = 'Y'
            elif cl in ['result', 'outcome', 'shot_result', 'event_type']: col_map[c] = 'result'
            elif cl in ['player', 'player_name', 'name', 'player_id']: col_map[c] = 'player'
            elif cl in ['minute', 'min', 'time']: col_map[c] = 'minute'
            elif cl in ['h_team', 'home_team', 'home']: col_map[c] = 'home_team'
            elif cl in ['a_team', 'away_team', 'away']: col_map[c] = 'away_team'
            elif cl in ['h_a', 'is_home', 'home_away']: col_map[c] = 'h_a'
            elif cl in ['team', 'team_name', 'squad']: col_map[c] = 'team'
            elif cl in ['game', 'match', 'match_id', 'game_id']: col_map[c] = 'game'
        df = df.rename(columns=col_map)
        
        # 2. Safety Defaults
        if 'X' not in df.columns: df['X'] = 0.5
        if 'Y' not in df.columns: df['Y'] = 0.5
        if 'xG' not in df.columns: df['xG'] = 0.0
        if 'minute' not in df.columns: df['minute'] = 1
        if 'result' not in df.columns: df['result'] = 'Missed'
        if 'player' not in df.columns: df['player'] = 'Unknown'
        
        # Normalize result strings
        df['result'] = df['result'].astype(str).str.title()
        
        # Safely extract home_team and away_team if missing
        if 'home_team' not in df.columns:
            if 'game' in df.columns and df['game'].dtype == 'O' and '-' in str(df['game'].iloc[0]):
                df['home_team'] = df['game'].apply(lambda g: str(g).split(' ', 1)[-1].split('-')[0].strip() if '-' in str(g) else 'Unknown')
                df['away_team'] = df['game'].apply(lambda g: str(g).split(' ', 1)[-1].split('-')[1].strip() if '-' in str(g) else 'Unknown')
            else:
                df['home_team'], df['away_team'] = 'Unknown', 'Unknown'
                
        # Resolve the active team that took the shot
        if 'team' in df.columns:
            df['team_std'] = df['team'].apply(standardize_team)
        elif 'h_a' in df.columns:
            df['team_std'] = np.where(df['h_a'].astype(str).str.lower() == 'h', df['home_team'], df['away_team'])
            df['team_std'] = df['team_std'].apply(standardize_team)
        else:
            df['team_std'] = 'Unknown'
            
        df['home_team'] = df['home_team'].apply(standardize_team)
        df['away_team'] = df['away_team'].apply(standardize_team)
        
        return df
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 5. ENHANCED HYBRID MATHEMATICAL ENGINE
# ==========================================
@st.cache_data(ttl=3600)
def calculate_hybrid_metrics(p_df, t_df, u_df, shots_df, w_long, w_short, fa_boost, ha_boost, min_mins, w_form, w_own, w_ict, blend_factor, horizon, w_finishing, w_zone):
    if p_df.empty or t_df.empty: return pd.DataFrame()
        
    df = p_df.copy()
    df['full_name'] = df['first_name'] + " " + df['second_name']
    short_to_full = dict(zip(t_df['short_name'], t_df['name']))
    
    df['mins_played'] = pd.to_numeric(df.get('minutes', 0), errors='coerce').fillna(0)
    max_possible_games = max(1.0, round(df['mins_played'].max() / 90.0))
    df['mins_per_game'] = (df['mins_played'] / max_possible_games).round(1)
    is_eligible = df['mins_per_game'] >= min_mins
    
    df['is_pen_taker'] = pd.to_numeric(df.get('penalties_order', 0), errors='coerce') == 1
    
    dampener = np.clip(df['mins_per_game'] / 60.0, 0.4, 1.0)
    df['xg_p90_base'] = np.where(is_eligible & (df['mins_played'] > 0), (df['expected_goals'] / df['mins_played']) * 90.0 * dampener, 0.0)
    df['xg_p90'] = np.where(df['is_pen_taker'], df['xg_p90_base'] + 0.15, df['xg_p90_base'])
    df['xa_p90'] = np.where(is_eligible & (df['mins_played'] > 0), (df['expected_assists'] / df['mins_played']) * 90.0 * dampener, 0.0)
    
    # Granular Finishing Skill & Danger-Zone Threat Multiplier
    if shots_df is not None and not shots_df.empty:
        p_shots = shots_df.groupby('player').agg(
            total_shots=('xG', 'count'),
            sum_xg=('xG', 'sum'),
            box_shots=('X', lambda x: (x >= 0.82).sum()),
            goals=('result', lambda r: (r == 'Goal').sum())
        ).reset_index()
        p_shots['finishing_delta'] = (p_shots['goals'] - p_shots['sum_xg']).clip(-2.0, 3.0)
        p_shots['box_threat_ratio'] = (p_shots['box_shots'] / p_shots['total_shots'].clip(lower=1.0)).clip(0.2, 1.0)
        
        df = df.merge(p_shots[['player', 'finishing_delta', 'box_threat_ratio']], left_on='second_name', right_on='player', how='left')
        
        finish_scale = (w_finishing / 50.0) * 0.04
        zone_scale = (w_zone / 50.0) * 0.1
        
        df['finishing_boost'] = (1.0 + df['finishing_delta'].fillna(0.0) * finish_scale).clip(0.85, 1.25)
        df['zone_boost'] = (1.0 + (df['box_threat_ratio'].fillna(0.6) - 0.5) * zone_scale).clip(0.85, 1.25)
    else:
        df['finishing_boost'] = 1.0
        df['zone_boost'] = 1.0
        
    t_stats = {}
    if not u_df.empty:
        latest_szn = u_df['season'].max()
        curr = u_df[u_df['season'] == latest_szn]
        for t in curr['home_team_std'].unique():
            h = curr[curr['home_team_std'] == t]
            a = curr[curr['away_team_std'] == t]
            h_xg_col = 'home_xg' if 'home_xg' in curr.columns else 'home_xG'
            a_xg_col = 'away_xg' if 'away_xg' in curr.columns else 'away_xG'
            tot_xg = h[h_xg_col].sum() + a[a_xg_col].sum()
            tot_xgc = h[a_xg_col].sum() + a[h_xg_col].sum()
            m = len(h) + len(a)
            if m > 0: t_stats[t] = {'xg_p90': tot_xg / m, 'xgc_p90': tot_xgc / m}
                
    league_avg_xg = np.mean([v['xg_p90'] for v in t_stats.values()]) if t_stats else 1.35
    league_avg_xgc = np.mean([v['xgc_p90'] for v in t_stats.values()]) if t_stats else 1.35
    
    def get_stat(team_name, stat):
        name = standardize_team(team_name)
        return t_stats.get(name, {}).get(stat, league_avg_xg)
        
    df['team_xgc'] = df['team_name'].apply(lambda x: get_stat(x, 'xgc_p90'))
    
    fit_prob = df['chance_of_playing_next_round'] / 100.0
    df['p_app_1'] = np.where(is_eligible, np.clip(df['mins_per_game'] / 25.0, 0.0, 1.0) * 0.95 * fit_prob, 0.0)
    df['p_app_2'] = np.where(is_eligible, np.clip((df['mins_per_game'] - 40.0) / 40.0, 0.0, 1.0) * 0.85 * fit_prob, 0.0)
    df['exp_app_pts_base'] = df['p_app_1'] * 1.0 + df['p_app_2'] * 1.0
    df['exp_bonus_pts_base'] = np.where(is_eligible & (df['mins_played'] > 0), (df['bps'] / df['mins_played']) * 90.0 * 0.04 * dampener, 0.0)
    
    goal_pts_map = {1: 6, 2: 6, 3: 5, 4: 4}
    df['goal_val'] = df['element_type'].map(goal_pts_map)
    df['cs_val'] = df['element_type'].map({1: 4.0, 2: 4.0, 3: 1.0, 4: 0.0})
    df['conc_penalty_val'] = df['element_type'].map({1: -1.0, 2: -1.0, 3: 0.0, 4: 0.0})
    
    base_weights = [1.0, 0.8, 0.6, 0.4, 0.2]
    gw_weights = base_weights[:horizon]
    
    df['v2_xp'], df['exp_goal_pts_acc'], df['exp_assist_pts_acc'] = 0.0, 0.0, 0.0
    df['exp_cs_pts_acc'], df['exp_conc_penalty_acc'], df['exp_app_pts_acc'], df['exp_bonus_pts_acc'] = 0.0, 0.0, 0.0, 0.0
    
    for gw_idx, weight in enumerate(gw_weights):
        opp_short = df['next_5_opps'].apply(lambda x: x[gw_idx] if isinstance(x, list) and len(x) > gw_idx else 'Blank')
        is_home = df['next_5_is_home'].apply(lambda x: x[gw_idx] if isinstance(x, list) and len(x) > gw_idx else False)
        fdr = df['next_5_fdr'].apply(lambda x: x[gw_idx] if isinstance(x, list) and len(x) > gw_idx else 3)
        
        opp_name = opp_short.map(short_to_full).fillna('Average Team').apply(standardize_team)
        opp_xg = opp_name.apply(lambda x: get_stat(x, 'xg_p90'))
        opp_xgc = opp_name.apply(lambda x: get_stat(x, 'xgc_p90'))
        
        fdr_mult = 1.0 + (3 - fdr) * 0.1
        attack_mult = (opp_xgc / league_avg_xgc).clip(0.5, 2.0) * fdr_mult
        def_mult = (opp_xg / league_avg_xg).clip(0.5, 2.0) * (1.0 / fdr_mult)
        ha_factor = np.where(is_home, 1.0 + ha_boost, 1.0 - ha_boost)
        
        gw_goal = np.where(is_eligible & (opp_short != 'Blank'), (df['xg_p90'] * df['goal_val'] * df['finishing_boost'] * df['zone_boost']) * attack_mult * ha_factor, 0.0)
        gw_assist = np.where(is_eligible & (opp_short != 'Blank'), (df['xa_p90'] * 3.0 * fa_boost) * attack_mult * ha_factor, 0.0)
        
        match_xgc = df['team_xgc'] * def_mult
        prob_cs = np.where(is_eligible & (opp_short != 'Blank'), np.exp(-match_xgc), 0.0)
        prob_conc_2plus = np.where(is_eligible & (opp_short != 'Blank'), 1.0 - np.exp(-match_xgc) * (1.0 + match_xgc), 0.0)
        
        gw_cs = np.where(is_eligible & (opp_short != 'Blank'), prob_cs * df['cs_val'] * df['p_app_2'] * ha_factor, 0.0)
        gw_conc_pen = np.where(is_eligible & (opp_short != 'Blank'), prob_conc_2plus * df['conc_penalty_val'] * df['p_app_1'] * ha_factor, 0.0)
        gw_app = np.where(is_eligible & (opp_short != 'Blank'), df['exp_app_pts_base'] * ha_factor, 0.0)
        gw_bonus = np.where(is_eligible & (opp_short != 'Blank'), df['exp_bonus_pts_base'] * ha_factor, 0.0)
        
        df['exp_goal_pts_acc'] += gw_goal * weight
        df['exp_assist_pts_acc'] += gw_assist * weight
        df['exp_cs_pts_acc'] += gw_cs * weight
        df['exp_conc_penalty_acc'] += gw_conc_pen * weight
        df['exp_app_pts_acc'] += gw_app * weight
        df['exp_bonus_pts_acc'] += gw_bonus * weight
        
        if gw_idx == 0:
            df['attack_mult'] = attack_mult
            df['def_mult'] = def_mult
            df['prob_cs'] = prob_cs
            df['is_home'] = is_home
            df['opp_name'] = opp_name

    df['exp_goal_pts'] = df['exp_goal_pts_acc']
    df['exp_assist_pts'] = df['exp_assist_pts_acc']
    df['exp_cs_pts'] = df['exp_cs_pts_acc']
    df['exp_conc_penalty'] = df['exp_conc_penalty_acc']
    df['exp_app_pts'] = df['exp_app_pts_acc']
    df['exp_bonus_pts'] = df['exp_bonus_pts_acc']
    df['v2_xp'] = (df['exp_goal_pts'] + df['exp_assist_pts'] + df['exp_cs_pts'] + df['exp_conc_penalty'] + df['exp_app_pts'] + df['exp_bonus_pts']).round(2)

    weights_dict = {'form': w_form, 'selected_by_percent': w_own, 'ict_index': w_ict}
    total_w = sum(weights_dict.values())
    if total_w > 0:
        for metric, w in weights_dict.items():
            min_v, max_v = df[metric].min(), df[metric].max()
            df[f'{metric}_norm'] = (df[metric] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
        
        df['custom_v1_score'] = sum(df[f'{metric}_norm'] * (w / total_w) for metric, w in weights_dict.items())
        df['hybrid_multiplier'] = 1.0 + ((df['custom_v1_score'] - 0.5) * 2.0 * (blend_factor / 100.0))
    else:
        df['hybrid_multiplier'] = 1.0
        
    df['final_xp'] = np.where(is_eligible, (df['v2_xp'] * df['hybrid_multiplier']).round(2), 0.0)
    return df

@st.cache_data(ttl=3600)
def fetch_league_history(league_id):
    try:
        r_boot = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10).json()
        gw_to_month = {}
        completed_gws = []
        for e in r_boot['events']:
            if e['finished']:
                month = pd.to_datetime(e['deadline_time']).strftime('%B %Y')
                gw_to_month[e['id']] = month
                completed_gws.append(e['id'])
                
        r_standings = requests.get(f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/", timeout=10).json()
        entries = r_standings.get('standings', {}).get('results', [])[:50] 
        league_name = r_standings.get('league', {}).get('name', 'Unknown League')
        
        history_data = []
        for entry in entries:
            try:
                r_hist = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry['entry']}/history/", timeout=5).json()
                for gw in r_hist['current']:
                    if gw['event'] in completed_gws:
                        history_data.append({
                            'Manager': entry['player_name'],
                            'Team': entry['entry_name'],
                            'GW': gw['event'],
                            'Net Points': gw['points'] - gw['event_transfers_cost'],
                            'Month': gw_to_month.get(gw['event'], 'Unknown')
                        })
            except Exception: continue
                
        return pd.DataFrame(history_data), league_name, r_standings.get('standings', {}).get('results', []), completed_gws
    except Exception: return pd.DataFrame(), "Error", [], []

# ==========================================
# 6. PLOTLY PITCH & MOMENTUM CHART HELPERS
# ==========================================
def draw_pitch_plotly(title="Shot Map"):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=1, line=dict(color="#D1CDC4", width=2), fillcolor="#FBFBF9")
    fig.add_shape(type="line", x0=0.5, y0=0, x1=0.5, y1=1, line=dict(color="#E5E2DC", width=2))
    fig.add_shape(type="circle", x0=0.4, y0=0.35, x1=0.6, y1=0.65, line=dict(color="#E5E2DC", width=2))
    fig.add_shape(type="rect", x0=0, y0=0.21, x1=0.17, y1=0.79, line=dict(color="#E5E2DC", width=2))
    fig.add_shape(type="rect", x0=0, y0=0.37, x1=0.06, y1=0.63, line=dict(color="#E5E2DC", width=2))
    fig.add_shape(type="rect", x0=0.83, y0=0.21, x1=1.0, y1=0.79, line=dict(color="#E5E2DC", width=2))
    fig.add_shape(type="rect", x0=0.94, y0=0.37, x1=1.0, y1=0.63, line=dict(color="#E5E2DC", width=2))
    
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.02, 1.02])
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.02, 1.02])
    fig.update_layout(title=title, height=420, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="#FBFBF9")
    return fig

# Initialize Global Data Pipeline
fpl_fixtures_all = load_fpl_all_fixtures()
players_df, teams_df = load_fpl_data()
match_df = load_match_data()
understat_shooting_df = load_understat_data(fpl_fixtures_all)
understat_shots_df = load_understat_shots()

if players_df.empty:
    st.error("🚨 FPL API is currently unreachable. Please try again later.")
    st.stop()

# ==========================================
# 7. SIDEBAR NAVIGATION 
# ==========================================
st.sidebar.title("⚽ EPL HUB")
st.sidebar.markdown("---")

menu_category = st.sidebar.selectbox("Select Category:", ["🏆 Fantasy Premier League", "⚽ EPL Matches & Stats", "📈 Betting Advisor"])
st.sidebar.markdown("---")

st.sidebar.header("👤 Your FPL Context")
user_manager_id = st.sidebar.text_input("My Manager ID:", value=st.session_state.get("default_manager_id", ""))
user_league_id = st.sidebar.text_input("My Mini-League ID:", value=st.session_state.get("default_league_id", ""))
st.sidebar.markdown("---")

# Global weights placeholders
w_finishing, w_zone = 50, 50

if menu_category == "🏆 Fantasy Premier League":
    app_mode = st.sidebar.radio("Select Module:", [
        "🏠 Gameweek Dashboard",
        "👤 Advanced Player Scout",
        "🗄️ Model Data & Points Matrix",
        "📅 Fixture Multipliers",
        "⚡ Unified Squad Optimizer",
        "🔄 Transfer Suggester",
        "🏆 Live Mini-League Standings"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Unified Model Tuning")
    preset = st.sidebar.selectbox("🎯 Strategy Preset:", ["The Sweet Spot", "The xG Data Analyst", "Custom", "The Form Chaser", "The Crowd Chaser", "The ICT Chaser"])
    
    if preset != "Custom":
        if "Sweet Spot" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 3, 50.0, 1.35, 0.06
            w_form, w_own, w_ict, blend_factor_g = 5, 5, 90, 10.0
            w_finishing, w_zone = 50, 50
        elif "The xG Data Analyst" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 3, 40.0, 1.35, 0.06
            w_form, w_own, w_ict, blend_factor_g = 10, 10, 80, 5.0
            w_finishing, w_zone = 100, 100 
        elif "Form Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 1, 25.0, 1.40, 0.05
            w_form, w_own, w_ict, blend_factor_g = 80, 10, 10, 40.0
            w_finishing, w_zone = 25, 25
        elif "Crowd Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 1, 25.0, 1.40, 0.05
            w_form, w_own, w_ict, blend_factor_g = 10, 80, 10, 40.0
            w_finishing, w_zone = 10, 10
        elif "ICT Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 3, 45.0, 1.35, 0.05
            w_form, w_own, w_ict, blend_factor_g = 0, 0, 100, 25.0
            w_finishing, w_zone = 0, 0
            
        st.sidebar.info(f"Using **{preset}** settings.")
    else:
        horizon_g = st.sidebar.slider("Planning Horizon (Gameweeks)", 1, 5, 3, 1)
        min_mins_g = st.sidebar.slider("Min Mins/Game Filter", 10.0, 90.0, 25.0, 5.0)
        
        st.sidebar.markdown("**Granular Shot Data Weights**")
        w_finishing = st.sidebar.slider("Finishing Skill Impact (%)", 0, 100, 50, 10)
        w_zone = st.sidebar.slider("High-Value Zone Impact (%)", 0, 100, 50, 10)
        
        st.sidebar.markdown("**Poisson Model Weights**")
        fa_boost_g = st.sidebar.slider("Fantasy Assist Boost", 1.0, 1.8, 1.40, 0.05)
        ha_boost_g = st.sidebar.slider("Home/Away Factor", 0.0, 0.15, 0.05, 0.01)
        
        st.sidebar.markdown("**ICT / Form Hybrid Weights**")
        w_form = st.sidebar.slider("Form (Short-Term)", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
        w_ict = st.sidebar.slider("ICT Index (Quality)", 0, 100, 40, 5)
        blend_factor_g = st.sidebar.slider("ICT Impact on xP (%)", 0.0, 50.0, 15.0, 5.0)

elif menu_category == "⚽ EPL Matches & Stats":
    app_mode = st.sidebar.radio("Select Module:", ["📅 Match Results & Match Center", "📊 Live League Table", "📈 Team Trends (xG vs Actual)", "🛡️ Defensive Vulnerability Map"])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g, horizon_g = 0.8, 0.2, 1.4, 0.05, 25.0, 3
    w_form, w_own, w_ict, blend_factor_g = 0, 0, 0, 0.0

elif menu_category == "📈 Betting Advisor":
    app_mode = st.sidebar.radio("Select Module:", ["🎲 Monte Carlo Match Simulator", "📈 Chaos Quadrant & Match Trends"])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g, horizon_g = 0.8, 0.2, 1.4, 0.05, 25.0, 3
    w_form, w_own, w_ict, blend_factor_g = 0, 0, 0, 0.0

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

if menu_category == "🏆 Fantasy Premier League":
    master_df = calculate_hybrid_metrics(players_df, teams_df, understat_shooting_df, understat_shots_df, 0.8, 0.2, fa_boost_g, ha_boost_g, min_mins_g, w_form, w_own, w_ict, blend_factor_g, horizon_g, w_finishing, w_zone)

# ==========================================
# MODULE: FPL GAMWEEK DASHBOARD
# ==========================================
if menu_category == "🏆 Fantasy Premier League" and app_mode == "🏠 Gameweek Dashboard":
    st.title("🏠 EPL Hub Control Center")
    current_gw = get_current_event()
    st.markdown(f"### 📅 Current Gameweek: **GW {current_gw}**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='scout-card'><h3>⚡ Top Form Players</h3>", unsafe_allow_html=True)
        top_form = master_df.sort_values(by='form', ascending=False).head(5)
        for _, r in top_form.iterrows():
            st.markdown(f"**{r['full_name']}** ({r['team_name']}) - Form: {r['form']}", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"<div class='scout-card'><h3>📈 Top {horizon_g}-GW Projections</h3>", unsafe_allow_html=True)
        top_proj = master_df.sort_values(by='final_xp', ascending=False).head(5)
        for _, r in top_proj.iterrows():
            st.markdown(f"**{r['full_name']}** ({r['team_name']}) - xP: {r['final_xp']:.2f}", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# MODULE: ADVANCED PLAYER SCOUT
# ==========================================
elif app_mode == "👤 Advanced Player Scout":
    st.title("👤 Advanced Player Scout Profile")
    
    if not master_df.empty:
        view_mode = st.radio("Select View Mode:", ["Single Profile", "⚔️ Head-to-Head Comparison"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        f_col1, f_col2 = st.columns(2)
        teams_list = ["All"] + sorted(master_df['team_name'].unique().tolist())
        selected_team = f_col1.selectbox("Filter by Team:", teams_list)
        selected_pos = f_col2.selectbox("Filter by Position:", ["All", "GKP", "DEF", "MID", "FWD"])
        
        filtered_df = master_df.copy()
        if selected_team != "All": filtered_df = filtered_df[filtered_df['team_name'] == selected_team]
        if selected_pos != "All": filtered_df = filtered_df[filtered_df['position'] == selected_pos]
        
        player_list = sorted(filtered_df['full_name'].tolist())
        
        if len(player_list) > 0:
            def render_scout_card(p_data):
                chance_val = int(p_data.get('chance_of_playing_next_round', 100))
                chance_color = "#4E7A5E" if chance_val == 100 else ("#D97757" if chance_val > 0 else "#B34D4D")
                boost_pct = ((p_data['hybrid_multiplier'] - 1.0) * 100)
                boost_color = "#4E7A5E" if boost_pct >= 0 else "#B34D4D"
                boost_sign = "+" if boost_pct >= 0 else ""
                pen_badge = "🎯 PEN TAKER | " if p_data.get('is_pen_taker', False) else ""
                
                return f"""
                <div class="scout-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="margin-bottom: 12px;">
                                <span class="badge-cyan" style="margin-right: 8px;">{p_data['position']}</span>
                                <span class="badge-pink">{p_data['team_name']}</span>
                            </div>
                            <h2 style="margin: 0; font-size: 2.0rem; color: #1A1A1A;">{p_data['first_name'].upper()} {p_data['second_name'].upper()}</h2>
                            <p style="margin: 8px 0 0 0; color: #555555; opacity: 0.9; font-size: 1.0rem;">
                                Price: <b style="font-family: 'Fira Code', monospace;">£{p_data['cost_m']}M</b> &nbsp;|&nbsp; 
                                Pts: <b style="font-family: 'Fira Code', monospace;">{int(p_data['total_points'])}</b><br>
                                Next: <b>{p_data.get('next_opponent', 'N/A')}</b><br>
                                Fit: <b style="color: {chance_color}; font-family: 'Fira Code', monospace;">{chance_val}%</b>
                            </p>
                        </div>
                        <div style="text-align: right; background: #F9F8F6; padding: 15px; border-radius: 8px; border: 1px solid #E5E2DC;">
                            <div style="color: #555555; font-size: 0.8rem; margin-bottom: 5px;">{horizon_g}-GW Horizon xP: {p_data['v2_xp']:.2f} | ICT Nudge: <span style="color: {boost_color};">{boost_sign}{boost_pct:.1f}%</span></div>
                            <h3 style="color: #D97757; margin:0 0 5px 0; font-weight: 800;">Final Proj xP: {p_data['final_xp']:.2f}</h3>
                            <div style="color: #555555; font-size: 0.9rem;">
                                {pen_badge} GW1 Atk Mult: <b style="font-family: 'Fira Code', monospace;">{p_data['attack_mult']:.2f}x</b> &nbsp;|&nbsp; 
                                GW1 CS Odds: <b style="color: #4E7A5E; font-family: 'Fira Code', monospace;">{p_data['prob_cs']*100:.0f}%</b>
                            </div>
                        </div>
                    </div>
                </div>
                """

            if view_mode == "Single Profile":
                selected_player = st.selectbox("Select Player:", player_list)
                p_data = filtered_df[filtered_df['full_name'] == selected_player].iloc[0]
                st.markdown(render_scout_card(p_data), unsafe_allow_html=True)
                
                tab_radar, tab_shots = st.tabs(["📊 Radar & Percentiles", "🎯 Shot Coordinates Profile"])
                
                with tab_radar:
                    rc1, rc2 = st.columns([1, 1])
                    with rc1:
                        st.markdown("### 📊 Market Percentiles")
                        metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
                        for label, col_name in metrics.items():
                            if col_name in players_df.columns:
                                val = p_data[col_name]
                                percentile = int((players_df[col_name] < val).mean() * 100)
                                st.markdown(f"<div style='margin-bottom:-10px; font-size: 14px; color: #555555;'><b>{label}</b>: <span style='color:#D97757; font-family: \"Fira Code\", monospace;'>{val}</span> <span style='opacity: 0.6; font-size:12px;'>(Top {100-percentile}%)</span></div>", unsafe_allow_html=True)
                                st.progress(percentile / 100.0)
                    with rc2:
                        st.markdown("### 🕸️ Player Profile vs League")
                        pct_thr = int((players_df['threat'] < p_data['threat']).mean() * 100)
                        pct_cre = int((players_df['creativity'] < p_data['creativity']).mean() * 100)
                        pct_inf = int((players_df['influence'] < p_data['influence']).mean() * 100)
                        pct_xg = int((players_df['expected_goals'] < p_data['expected_goals']).mean() * 100)
                        pct_xa = int((players_df['expected_assists'] < p_data['expected_assists']).mean() * 100)
                        
                        radar_options = {
                            "tooltip": {"trigger": "item"},
                            "radar": {
                                "indicator": [{"name": "Threat", "max": 100}, {"name": "Creativity", "max": 100}, {"name": "Influence", "max": 100}, {"name": "xG", "max": 100}, {"name": "xA", "max": 100}],
                                "splitArea": {"show": False}, "axisName": {"color": "#555555"}
                            },
                            "series": [{
                                "name": "Player Profile vs League", "type": "radar",
                                "data": [{"value": [pct_thr, pct_cre, pct_inf, pct_xg, pct_xa], "name": p_data['second_name'], "itemStyle": {"color": "#D97757"}, "areaStyle": {"color": "rgba(217, 119, 87, 0.3)"}}]
                            }]
                        }
                        st_echarts(radar_options, height="300px")
                        
                with tab_shots:
                    st.markdown("### 🎯 Interactive Shot Map")
                    if understat_shots_df is not None and not understat_shots_df.empty:
                        p_shots = understat_shots_df[understat_shots_df['player'] == p_data['second_name']]
                        if not p_shots.empty:
                            p_fig = draw_pitch_plotly(f"All Recorded Shots: {p_data['second_name']}")
                            p_fig.add_trace(go.Scatter(
                                x=p_shots['X'], y=p_shots['Y'], mode='markers',
                                marker=dict(size=p_shots['xG']*35 + 6, color=np.where(p_shots['result'] == 'Goal', '#4E7A5E', '#D97757'), opacity=0.8),
                                text=p_shots.apply(lambda r: f"Minute: {r['minute']}' | xG: {r['xG']:.2f} | {r['result']}", axis=1), hoverinfo='text'
                            ))
                            st.plotly_chart(p_fig, use_container_width=True)
                        else: st.info("No individual shot tracking events found for this player in the database.")
                    else: st.info("Understat shot dataset currently synchronizing...")
            else:
                c_a, c_b = st.columns(2)
                with c_a: player_a = st.selectbox("Select Player A:", player_list, index=0)
                with c_b: player_b = st.selectbox("Select Player B:", player_list, index=1 if len(player_list) > 1 else 0)
                p_data_a = filtered_df[filtered_df['full_name'] == player_a].iloc[0]
                p_data_b = filtered_df[filtered_df['full_name'] == player_b].iloc[0]
                
                c_a.markdown(render_scout_card(p_data_a), unsafe_allow_html=True)
                c_b.markdown(render_scout_card(p_data_b), unsafe_allow_html=True)
                
                st.markdown("### ⚔️ Profile Comparison")
                rc1, rc2 = st.columns([1, 1])
                metrics = ['threat', 'creativity', 'influence', 'expected_goals', 'expected_assists']
                pct_a = [int((players_df[m] < p_data_a[m]).mean() * 100) if m in players_df.columns else 0 for m in metrics]
                pct_b = [int((players_df[m] < p_data_b[m]).mean() * 100) if m in players_df.columns else 0 for m in metrics]
                
                with rc1:
                    st.markdown("#### 🕸️ Market Percentiles Radar")
                    radar_options = {
                        "tooltip": {"trigger": "item"},
                        "legend": {"data": [p_data_a['second_name'], p_data_b['second_name']], "bottom": 0},
                        "radar": {
                            "indicator": [{"name": "Threat", "max": 100}, {"name": "Creativity", "max": 100}, {"name": "Influence", "max": 100}, {"name": "xG", "max": 100}, {"name": "xA", "max": 100}],
                            "splitArea": {"show": False}, "axisName": {"color": "#555555"}
                        },
                        "series": [{
                            "type": "radar",
                            "data": [
                                {"value": pct_a, "name": p_data_a['second_name'], "itemStyle": {"color": "#D97757"}, "areaStyle": {"color": "rgba(217, 119, 87, 0.3)"}},
                                {"value": pct_b, "name": p_data_b['second_name'], "itemStyle": {"color": "#4E7A5E"}, "areaStyle": {"color": "rgba(78, 122, 94, 0.3)"}}
                            ]
                        }]
                    }
                    st_echarts(radar_options, height="350px")
                    
                with rc2:
                    st.markdown("#### 📊 Metric Comparison")
                    comp_df = pd.DataFrame({
                        "Metric": ["Cost (£M)", "Total Points", "Form", "ICT Index", "Proj xP (Horizon)"],
                        p_data_a['second_name']: [p_data_a['cost_m'], p_data_a['total_points'], p_data_a['form'], p_data_a['ict_index'], p_data_a['final_xp']],
                        p_data_b['second_name']: [p_data_b['cost_m'], p_data_b['total_points'], p_data_b['form'], p_data_b['ict_index'], p_data_b['final_xp']]
                    })
                    st.dataframe(comp_df, width="stretch", hide_index=True)

# ==========================================
# MODULE: MODEL DATA & POINTS MATRIX
# ==========================================
elif app_mode == "🗄️ Model Data & Points Matrix":
    st.title(f"🗄️ Model Data & {horizon_g}-GW Expected Points")
    tab1, tab2 = st.tabs([f"🧮 {horizon_g}-GW xP Breakdown Matrix", "🗄️ Master Player Data Bank"])
    
    with tab1:
        f1, f2 = st.columns(2)
        pos_filter = f1.selectbox("Filter Position:", ["All", "GKP", "DEF", "MID", "FWD"], key="matrix_pos")
        team_filter = f2.selectbox("Filter Club:", ["All"] + sorted(master_df['team_name'].unique().tolist()), key="matrix_team")
        
        filtered_matrix = master_df.copy()
        if pos_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['position'] == pos_filter]
        if team_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['team_name'] == team_filter]
        
        top_df = filtered_matrix.sort_values(by='final_xp', ascending=False).head(15).iloc[::-1]
        
        if not top_df.empty:
            st.markdown(f"### 📊 Top 15 Players xP Decomposition ({horizon_g}-GW Horizon)")
            stacked_options = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ["Appearance", "Attack", "Defense", "Bonus"], "textStyle": {"color": "#555555"}},
                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                "xAxis": {"type": "value", "splitLine": {"show": False}},
                "yAxis": {"type": "category", "data": top_df['full_name'].tolist()},
                "color": ["#8C8C8C", "#D97757", "#4E7A5E", "#F6D365"],
                "series": [
                    {"name": "Appearance", "type": "bar", "stack": "total", "data": top_df['exp_app_pts'].round(2).tolist()},
                    {"name": "Attack", "type": "bar", "stack": "total", "data": (top_df['exp_goal_pts'] + top_df['exp_assist_pts']).round(2).tolist()},
                    {"name": "Defense", "type": "bar", "stack": "total", "data": (top_df['exp_cs_pts'] + top_df['exp_conc_penalty']).clip(lower=0).round(2).tolist()},
                    {"name": "Bonus", "type": "bar", "stack": "total", "data": top_df['exp_bonus_pts'].round(2).tolist()}
                ]
            }
            st_echarts(stacked_options, height="450px")
            
        matrix_cols = ['full_name', 'position', 'team_name', 'v2_xp', 'finishing_boost', 'zone_boost', 'hybrid_multiplier', 'final_xp']
        
        col_configs = {
            "full_name": st.column_config.TextColumn("Player"),
            "v2_xp": st.column_config.NumberColumn("Base Poisson xP", help="Expected Points from pure fixture odds"),
            "finishing_boost": st.column_config.NumberColumn("Finishing Skill Mult", format="%.2f", help="Shot data modifier based on player xG vs Goals"),
            "zone_boost": st.column_config.NumberColumn("Shot Zone Mult", format="%.2f", help="Modifier based on shots taken inside the 6-yard box"),
            "hybrid_multiplier": st.column_config.NumberColumn("Form/ICT Mult", format="%.2f", help="Final blend modifier applying short-term form vs crowd ownership"),
            "final_xp": st.column_config.NumberColumn("Final Proj xP", format="%.2f", help="The absolute final projected points for the optimizer to solve with.")
        }
        st.dataframe(filtered_matrix[matrix_cols].sort_values(by='final_xp', ascending=False), width="stretch", hide_index=True, column_config=col_configs)

    with tab2:
        cols_to_show = ['full_name', 'team_name', 'position', 'cost_m', 'minutes', 'mins_per_game', 'xg_p90', 'xa_p90', 'is_pen_taker', 'team_xgc', 'opp_name']
        st.dataframe(master_df[cols_to_show], width="stretch", hide_index=True)

# ==========================================
# MODULE: FIXTURE MULTIPLIERS
# ==========================================
elif app_mode == "📅 Fixture Multipliers":
    st.title("📅 Fixture Multipliers & Opponent Index")
    if not master_df.empty:
        team_summary = master_df.groupby(['team_name', 'opp_name', 'is_home']).agg(
            Attack_Multiplier=('attack_mult', 'first'), Defensive_Multiplier=('def_mult', 'first'), Expected_CS_Chance=('prob_cs', 'first')
        ).reset_index()
        team_summary['Venue'] = np.where(team_summary['is_home'], 'Home', 'Away')
        st.dataframe(team_summary[['team_name', 'Venue', 'Attack_Multiplier', 'Defensive_Multiplier', 'Expected_CS_Chance', 'opp_name']], width="stretch", hide_index=True)

# ==========================================
# MODULE: UNIFIED SQUAD OPTIMIZER
# ==========================================
elif app_mode == "⚡ Unified Squad Optimizer":
    st.title("⚡ Prescriptive Squad Optimizer (Hybrid Model)")
    st.sidebar.markdown("---")
    budget_v2 = st.sidebar.number_input("1. Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    bench_weight_v2 = st.sidebar.slider("2. Bench Investment Weight", 0.0, 1.0, 0.1, 0.1)
    target_formation_v2 = st.sidebar.selectbox("3. Preferred Starting Formation:", ["Auto (Best Points)", "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"])
    exclude_injured = st.sidebar.checkbox("4. Hide Injured/Suspended Players", value=True)
    
    if master_df is not None: locked_players_v2 = st.sidebar.multiselect("5. Select up to 14 must-have players:", sorted(master_df['full_name'].tolist()), max_selections=14)
    else: locked_players_v2 = []

    if st.button("🚀 Run Hybrid Solver", type="primary", width="stretch"):
        if not master_df.empty:
            df = master_df.copy()
            if exclude_injured: df = df[df['status'] == 'a']
            df = df[(df['mins_per_game'] >= min_mins_g) | (df['full_name'].isin(locked_players_v2))]
            
            prob = pulp.LpProblem("Optimal_FPL_Hybrid", pulp.LpMaximize)
            squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
            starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
            bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
            
            prob += pulp.lpSum([df.loc[i, 'final_xp'] * starter_vars[i] + bench_weight_v2 * df.loc[i, 'final_xp'] * bench_vars[i] for i in df.index])
            for i in df.index: prob += squad_vars[i] == starter_vars[i] + bench_vars[i]
            
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
            
            for t_id in df['team'].unique(): prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
            for idx in df[df['full_name'].isin(locked_players_v2)].index.tolist(): prob += squad_vars[idx] == 1
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                squad = df.loc[[i for i in df.index if squad_vars[i].varValue > 0.5]].copy()
                starters = df.loc[[i for i in df.index if starter_vars[i].varValue > 0.5]].copy()
                bench_raw = df.loc[[i for i in df.index if bench_vars[i].varValue > 0.5]].copy()
                bench = pd.concat([bench_raw[bench_raw['element_type'] == 1], bench_raw[bench_raw['element_type'] > 1].sort_values(by='final_xp', ascending=False)])
                
                captain_id = starters['final_xp'].idxmax()
                captain_row = starters.loc[captain_id]
                total_xp = starters['final_xp'].sum() + captain_row['final_xp']
                
                st.success("✅ Hybrid Squad Solution Computed!")
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Spent Budget", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget_v2 - squad['cost_m'].sum():.1f}M")
                sc2.metric("Proj Points (Final xP)", f"{total_xp:.2f} pts")
                sc3.metric("Captain Pick", f"{captain_row['second_name']} ({captain_row['final_xp']:.2f} xP)")
                
                st.markdown("### 🏟️ Starting XI")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                def render_responsive_pitch(row_df, card_class='pitch-card'):
                    if not row_df.empty:
                        st.markdown("<div class='pitch-row'>", unsafe_allow_html=True)
                        for p in row_df.itertuples():
                            cap = "<span class='badge-cap'>C</span>" if p.Index == captain_id and card_class == 'pitch-card' else ""
                            st.markdown(f"""
                            <div class='pitch-card-wrapper'>
                                <div class='{card_class}'>
                                    <b style='color: #1A1A1A; font-size: 13px; font-weight: 600;'>{p.second_name} {cap}</b><br>
                                    <span style='font-size:10px; color:#8C8C8C;'>{p.team_name}</span><br>
                                    <span style='font-size:10px; color:#D97757;'>vs {p.next_opponent}</span><br>
                                    <span style='color:#2D2D2D; font-weight:700; font-size:12px; font-family: "Fira Code", monospace;'>£{p.cost_m} | {p.final_xp:.1f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                render_responsive_pitch(starters[starters['element_type'] == 1])
                render_responsive_pitch(starters[starters['element_type'] == 2])
                render_responsive_pitch(starters[starters['element_type'] == 3])
                render_responsive_pitch(starters[starters['element_type'] == 4])
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("### 🪑 The Bench")
                render_responsive_pitch(bench, card_class='bench-card')

# ==========================================
# MODULE: TRANSFER SUGGESTER
# ==========================================
elif app_mode == "🔄 Transfer Suggester":
    st.title("🔄 Transfer Suggester")
    transfer_bench_weight = st.sidebar.slider("Bench Investment Weight (Transfers)", 0.0, 1.0, 0.1, 0.1)
    
    if user_manager_id and master_df is not None and not master_df.empty:
        curr_event = get_current_event()
        my_elements, manager_bank = fetch_manager_squad(user_manager_id, curr_event)
        
        if my_elements:
            df = master_df[(master_df['status'] == 'a') | (master_df['id'].isin(my_elements))].copy()
            current_squad_indices = df[df['id'].isin(my_elements)].index.tolist()
            current_squad_df = df.loc[current_squad_indices]
            
            if len(current_squad_indices) == 15:
                c1, c2 = st.columns(2)
                forced_out_names = c1.multiselect("Targeted Sales (Optional):", sorted(current_squad_df['full_name'].tolist()))
                num_transfers = c2.selectbox("Number of Transfers:", list(range(max(1, len(forced_out_names)), 16)))
                
                if st.button("🚀 Analyze Best Transfers", type="primary", width="stretch"):
                    total_available_budget = current_squad_df['cost_m'].sum() + manager_bank
                    prob = pulp.LpProblem("Optimal_Transfer", pulp.LpMaximize)
                    squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
                    starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
                    bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
                    
                    prob += pulp.lpSum([df.loc[i, 'final_xp'] * starter_vars[i] + transfer_bench_weight * df.loc[i, 'final_xp'] * bench_vars[i] for i in df.index])
                    for i in df.index: prob += squad_vars[i] == starter_vars[i] + bench_vars[i]
                    prob += pulp.lpSum([df.loc[i, 'now_cost'] * squad_vars[i] for i in df.index]) <= (total_available_budget * 10)
                    prob += pulp.lpSum([squad_vars[i] for i in df.index]) == 15
                    prob += pulp.lpSum([starter_vars[i] for i in df.index]) == 11
                    prob += pulp.lpSum([bench_vars[i] for i in df.index]) == 4
                    prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2
                    prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5
                    prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5
                    prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3
                    prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 1
                    prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) >= 3
                    prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) >= 2
                    prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) >= 1
                    for t_id in df['team'].unique(): prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                    prob += pulp.lpSum([squad_vars[i] for i in current_squad_indices]) >= (15 - num_transfers)
                    for idx in current_squad_df[current_squad_df['full_name'].isin(forced_out_names)].index.tolist(): prob += squad_vars[idx] == 0
                    
                    prob.solve(pulp.PULP_CBC_CMD(msg=False))
                    
                    if pulp.LpStatus[prob.status] == 'Optimal':
                        new_squad_indices = [i for i in df.index if squad_vars[i].varValue > 0.5]
                        transfers_out = current_squad_df[~current_squad_df.index.isin(new_squad_indices)]
                        transfers_in = df.loc[new_squad_indices][~df.loc[new_squad_indices].index.isin(current_squad_indices)]
                        
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            st.markdown("<h3 style='color: #B34D4D;'>🛑 Players Out</h3>", unsafe_allow_html=True)
                            for _, row in transfers_out.iterrows(): st.markdown(f"<div style='border-left: 4px solid #B34D4D; padding-left: 10px; margin-bottom: 5px;'><b style='font-size: 16px;'>{row['second_name']}</b> <span style='font-size:12px; color:#8C8C8C;'>xP: {row['final_xp']:.2f}</span></div>", unsafe_allow_html=True)
                        with cc2:
                            st.markdown("<h3 style='color: #4E7A5E;'>✅ Players In</h3>", unsafe_allow_html=True)
                            for _, row in transfers_in.iterrows(): st.markdown(f"<div style='border-left: 4px solid #4E7A5E; padding-left: 10px; margin-bottom: 5px;'><b style='font-size: 16px;'>{row['second_name']}</b> <span style='font-size:12px; color:#8C8C8C;'>xP: {row['final_xp']:.2f}</span></div>", unsafe_allow_html=True)
            else: st.error("Could not load a complete 15-man squad.")
        else: st.error("Invalid or unverified Manager ID.")

# ==========================================
# MODULE: LIVE MINI-LEAGUE STANDINGS
# ==========================================
elif app_mode == "🏆 Live Mini-League Standings":
    st.title("🏆 Granular Mini-League Analyzer")
    if user_league_id:
        with st.spinner("Crunching mini-league history..."):
            history_df, l_name, standings_res, completed_gws = fetch_league_history(user_league_id)
            
        if standings_res:
            st.markdown(f"### 🏅 {l_name}")
            tab1, tab2, tab3 = st.tabs(["🏆 Live Overall Standings", "📅 Gameweek Winners", "🗓️ Monthly Awards"])
            
            with tab1:
                st.dataframe(pd.DataFrame(standings_res)[['rank', 'entry_name', 'player_name', 'event_total', 'total']], width="stretch", hide_index=True)
            
            with tab2:
                gw_summary = []
                for gw in range(1, 39):
                    if gw in completed_gws and not history_df.empty:
                        gw_df = history_df[history_df['GW'] == gw].sort_values(by='Net Points', ascending=False)
                        if not gw_df.empty:
                            winner = gw_df.iloc[0]
                            gw_summary.append({"Gameweek": f"GW {gw}", "Team Name": winner['Team'], "Manager": winner['Manager'], "Points": winner['Net Points']})
                    else:
                        gw_summary.append({"Gameweek": f"GW {gw}", "Team Name": "-", "Manager": "-", "Points": None})
                
                st.dataframe(pd.DataFrame(gw_summary), width="stretch", hide_index=True, column_config={"Points": st.column_config.NumberColumn("Points", format="%d")})

            with tab3:
                if not history_df.empty:
                    month_summary = []
                    for month in history_df.sort_values('GW')['Month'].unique():
                        m_df = history_df[history_df['Month'] == month].groupby(['Manager', 'Team'])['Net Points'].sum().reset_index().sort_values(by='Net Points', ascending=False).head(3)
                        pos_labels = ["Winner 🥇", "Runner up 🥈", "Second Runner up 🥉"]
                        for idx, (_, r) in enumerate(m_df.iterrows()):
                            month_summary.append({"Month": month, "Position": pos_labels[idx], "Team Name": r['Team'], "Points": r['Net Points']})
                    st.dataframe(pd.DataFrame(month_summary), width="stretch", hide_index=True, column_config={"Points": st.column_config.NumberColumn("Points", format="%d")})
                else: st.info("No monthly data available yet.")
        else: st.error("Failed to load league standings. Please verify your Mini-League ID.")

# ==========================================
# MODULE: EPL MATCH RESULTS & INTERACTIVE MATCH CENTER
# ==========================================
elif app_mode == "📅 Match Results & Match Center":
    st.title("📅 Match Results & Interactive Match Center")
    if not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season:", available_seasons, format_func=format_season)
        szn_matches = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date', ascending=True)
        
        max_gw = int(szn_matches['gameweek'].max())
        selected_gw_num = int(st.selectbox("Select Official Matchweek:", [f"Gameweek {i}" for i in range(1, max_gw + 1)]).split(" ")[1])
        gw_matches = szn_matches[szn_matches['gameweek'] == selected_gw_num].sort_values('date')
        
        for _, row in gw_matches.iterrows():
            h_xg = float(row.get('home_xg', row.get('home_xG', 0.0)))
            a_xg = float(row.get('away_xg', row.get('away_xG', 0.0)))
            st.markdown(f"""
            <div class="fixture-card">
                <div style="width: 35%; text-align: right;">
                    <div style="font-size: 1.15rem; font-weight: 600;">{row['home_team_std']}</div>
                    <div style="font-size: 0.85rem; color: #D97757;">xG: {h_xg:.2f}</div>
                </div>
                <div style="width: 30%; text-align: center;">
                    <div class="score-box">{int(row['home_goals'])} - {int(row['away_goals'])}</div>
                </div>
                <div style="width: 35%; text-align: left;">
                    <div style="font-size: 1.15rem; font-weight: 600;">{row['away_team_std']}</div>
                    <div style="font-size: 0.85rem; color: #8C8C8C;">xG: {a_xg:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        st.markdown("### 🏟️ Deep-Dive Match Center")
        match_options = [f"{r['home_team_std']} vs {r['away_team_std']} ({pd.to_datetime(r['date']).strftime('%b %d')})" for _, r in gw_matches.iterrows()]
        if match_options:
            sel_match_str = st.selectbox("Select Match to Analyze:", match_options)
            sel_home_team = sel_match_str.split(" vs ")[0]
            sel_away_team = sel_match_str.split(" vs ")[1].split(" (")[0]
            
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("#### ⏱️ Cumulative xG Momentum Chart")
                if understat_shots_df is not None and not understat_shots_df.empty:
                    m_shots = understat_shots_df[(understat_shots_df['home_team'] == sel_home_team) & (understat_shots_df['away_team'] == sel_away_team)].copy()
                    if not m_shots.empty:
                        m_shots = m_shots.sort_values('minute')
                        h_shots = m_shots[m_shots['team_std'] == sel_home_team]
                        a_shots = m_shots[m_shots['team_std'] == sel_away_team]
                        
                        h_mins = [0] + h_shots['minute'].tolist() + [90] if not h_shots.empty else [0, 90]
                        h_xgs = [0] + h_shots['xG'].cumsum().tolist() + [h_shots['xG'].sum()] if not h_shots.empty else [0, 0]
                        
                        a_mins = [0] + a_shots['minute'].tolist() + [90] if not a_shots.empty else [0, 90]
                        a_xgs = [0] + a_shots['xG'].cumsum().tolist() + [a_shots['xG'].sum()] if not a_shots.empty else [0, 0]
                        
                        fig_mom = go.Figure()
                        fig_mom.add_trace(go.Scatter(x=h_mins, y=h_xgs, mode='lines', name=sel_home_team, line=dict(color='#D97757', width=3, shape='hv')))
                        fig_mom.add_trace(go.Scatter(x=a_mins, y=a_xgs, mode='lines', name=sel_away_team, line=dict(color='#8C8C8C', width=3, shape='hv')))
                        fig_mom.update_layout(xaxis_title="Match Minute", yaxis_title="Cumulative xG", height=380, plot_bgcolor="#FBFBF9")
                        st.plotly_chart(fig_mom, use_container_width=True)
                    else: st.info("Granular shot timeline not available for this historical game.")
            
            with mc2:
                st.markdown("#### 🎯 Match Pitch & Shot Map")
                if understat_shots_df is not None and not understat_shots_df.empty and not m_shots.empty:
                    pitch_fig = draw_pitch_plotly(f"{sel_home_team} vs {sel_away_team}")
                    pitch_fig.add_trace(go.Scatter(
                        x=m_shots['X'], y=m_shots['Y'], mode='markers',
                        marker=dict(size=m_shots['xG']*35 + 6, color=np.where(m_shots['team_std'] == sel_home_team, '#D97757', '#4E7A5E'), opacity=0.8),
                        text=m_shots.apply(lambda r: f"{r['minute']}' {r['player']} ({r['team_std']}) - xG: {r['xG']:.2f} [{r['result']}]", axis=1),
                        hoverinfo='text'
                    ))
                    st.plotly_chart(pitch_fig, use_container_width=True)

# ==========================================
# MODULE: LIVE LEAGUE TABLE
# ==========================================
elif app_mode == "📊 Live League Table":
    st.title("📊 Expected vs Actual League Table")
    if not understat_shooting_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(understat_shooting_df['season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date')
        
        team_records = {team: {'W': 0, 'D': 0, 'L': 0, 'Pts': 0, 'GD': 0, 'GF': 0, 'GA': 0, 'xG': 0.0, 'xGA': 0.0} for team in pd.concat([szn_df['home_team_std'], szn_df['away_team_std']]).unique()}
        for _, row in szn_df.iterrows():
            h, a, h_g, a_g = row['home_team_std'], row['away_team_std'], row['home_goals'], row['away_goals']
            team_records[h]['GF'] += h_g; team_records[h]['GA'] += a_g; team_records[h]['GD'] += (h_g - a_g); team_records[h]['xG'] += float(row.get('home_xg', row.get('home_xG', 0.0))); team_records[h]['xGA'] += float(row.get('away_xg', row.get('away_xG', 0.0)))
            team_records[a]['GF'] += a_g; team_records[a]['GA'] += h_g; team_records[a]['GD'] += (a_g - h_g); team_records[a]['xG'] += float(row.get('away_xg', row.get('away_xG', 0.0))); team_records[a]['xGA'] += float(row.get('home_xg', row.get('home_xG', 0.0)))
            if h_g > a_g: team_records[h]['Pts'] += 3; team_records[h]['W'] += 1; team_records[a]['L'] += 1
            elif a_g > h_g: team_records[a]['Pts'] += 3; team_records[a]['W'] += 1; team_records[h]['L'] += 1
            else: team_records[h]['Pts'] += 1; team_records[a]['Pts'] += 1; team_records[h]['D'] += 1; team_records[a]['D'] += 1
            
        table_df = pd.DataFrame([{'Club': k, 'Pts': v['Pts'], 'GD': v['GD'], 'GF': v['GF'], 'xG': round(v['xG'], 2), 'GA': v['GA'], 'xGA': round(v['xGA'], 2)} for k, v in team_records.items()]).sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
        table_df.index += 1
        
        col_configs = {
            "Pts": st.column_config.NumberColumn("Pts", help="Total League Points"),
            "xG": st.column_config.NumberColumn("xG", help="Expected Goals For (Attack Quality)"),
            "xGA": st.column_config.NumberColumn("xGA", help="Expected Goals Against (Defensive Vulnerability)"),
            "GD": st.column_config.NumberColumn("GD", help="Actual Goal Difference")
        }
        st.dataframe(table_df, width="stretch", column_config=col_configs)

# ==========================================
# MODULE: DEFENSIVE VULNERABILITY MAP
# ==========================================
elif app_mode == "🛡️ Defensive Vulnerability Map":
    st.title("🛡️ Defensive Vulnerability Map")
    st.write("Analyze where Premier League defenses are conceding high-danger shots across the pitch.")
    if understat_shots_df is not None and not understat_shots_df.empty:
        all_teams = sorted(understat_shots_df['team_std'].dropna().unique().tolist())
        target_team = st.selectbox("Select Defending Club:", all_teams)
        
        conceded_shots = understat_shots_df[(understat_shots_df['home_team'] == target_team) | (understat_shots_df['away_team'] == target_team)].copy()
        conceded_shots = conceded_shots[conceded_shots['team_std'] != target_team]
        
        if not conceded_shots.empty:
            vm1, vm2 = st.columns([2, 1])
            with vm1:
                v_fig = draw_pitch_plotly(f"Shots Conceded by {target_team}")
                v_fig.add_trace(go.Scatter(
                    x=conceded_shots['X'], y=conceded_shots['Y'], mode='markers',
                    marker=dict(size=conceded_shots['xG']*35 + 5, color=np.where(conceded_shots['result'] == 'Goal', '#B34D4D', '#D97757'), opacity=0.7),
                    text=conceded_shots.apply(lambda r: f"xG: {r['xG']:.2f} | {r['result']}", axis=1), hoverinfo='text'
                ))
                st.plotly_chart(v_fig, use_container_width=True)
            with vm2:
                st.markdown("#### 🚨 Vulnerability Summary")
                box_pct = (conceded_shots['X'] >= 0.82).mean() * 100
                high_xg_count = (conceded_shots['xG'] >= 0.30).sum()
                st.metric("Total Shots Conceded", len(conceded_shots))
                st.metric("In-Box Threat Ratio", f"{box_pct:.1f}%")
                st.metric("Big Chances Conceded (xG > 0.3)", high_xg_count)
        else: st.info("No shot events logged for this team.")

# ==========================================
# MODULE: MONTE CARLO BETTING SIMULATOR
# ==========================================
elif app_mode == "🎲 Monte Carlo Match Simulator":
    st.title("🎲 Monte Carlo Match Simulator")
    st.write("Simulate 10,000 match outcomes based on underlying team $xG$, venue dominance, and Goalkeeper shot-stopping form adjustments.")
    
    if not understat_shooting_df.empty:
        latest_szn = understat_shooting_df['season'].max()
        curr_df = understat_shooting_df[understat_shooting_df['season'] == latest_szn]
        teams = sorted(list(set(curr_df['home_team_std'].tolist() + curr_df['away_team_std'].tolist())))
        
        c1, c2 = st.columns(2)
        home_t = c1.selectbox("Home Team:", teams, index=0)
        away_t = c2.selectbox("Away Team:", teams, index=1 if len(teams) > 1 else 0)
        
        sim_iterations = st.sidebar.slider("Simulation Iterations:", 1000, 10000, 5000, 1000)
        gk_adjustment = st.sidebar.slider("Goalkeeper Form Factor (Delta xG Conceded):", -0.4, 0.4, 0.0, 0.05)
        
        h_data = curr_df[curr_df['home_team_std'] == home_t]
        a_data = curr_df[curr_df['away_team_std'] == away_t]
        
        h_xg = (h_data.get('home_xg', h_data.get('home_xG', pd.Series([1.45]))).mean() if not h_data.empty else 1.45)
        a_xg = (a_data.get('away_xg', a_data.get('away_xG', pd.Series([1.15]))).mean() if not a_data.empty else 1.15)
        
        h_lam = max(0.2, h_xg * 1.05 - gk_adjustment)
        a_lam = max(0.2, a_xg * 0.95 + gk_adjustment)
        
        np.random.seed(42)
        sim_home_goals = np.random.poisson(h_lam, sim_iterations)
        sim_away_goals = np.random.poisson(a_lam, sim_iterations)
        
        h_wins = (sim_home_goals > sim_away_goals).mean()
        draws = (sim_home_goals == sim_away_goals).mean()
        a_wins = (sim_home_goals < sim_away_goals).mean()
        over_25 = ((sim_home_goals + sim_away_goals) > 2.5).mean()
        btts = ((sim_home_goals > 0) & (sim_away_goals > 0)).mean()
        
        st.markdown(f"### {home_t} ({h_wins*100:.1f}%) | Draw ({draws*100:.1f}%) | {away_t} ({a_wins*100:.1f}%)")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Home Expected Goals", f"{h_lam:.2f}")
        sc2.metric("Over 2.5 Goals Odds", f"{over_25*100:.1f}%")
        sc3.metric("Both Teams To Score (BTTS)", f"{btts*100:.1f}%")
        
        score_counts = pd.Series([f"{h}-{a}" for h, a in zip(sim_home_goals, sim_away_goals)]).value_counts(normalize=True).head(5) * 100
        st.markdown("#### 🎯 Top 5 Most Likely Scorelines")
        st.dataframe(pd.DataFrame({'Scoreline': score_counts.index, 'Probability': score_counts.values.round(1)}), width="stretch", hide_index=True)

# ==========================================
# MODULE: PREDICTIVE MATCH ANALYTICS
# ==========================================
elif app_mode == "📈 Chaos Quadrant & Match Trends":
    st.title("📈 Chaos Quadrant & Match Trends")
    if not match_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(match_df['Season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_match_df = match_df[match_df['Season'] == selected_season_raw]
        
        home_m = szn_match_df[['Match_ID', 'Home_Team', 'Home_Score_FT', 'Away_Score_FT']].copy().rename(columns={'Home_Team': 'Team', 'Home_Score_FT': 'Scored_FT', 'Away_Score_FT': 'Conceded_FT'})
        away_m = szn_match_df[['Match_ID', 'Away_Team', 'Away_Score_FT', 'Home_Score_FT']].copy().rename(columns={'Away_Team': 'Team', 'Away_Score_FT': 'Scored_FT', 'Home_Score_FT': 'Conceded_FT'})
        fact_matches = pd.concat([home_m, away_m], ignore_index=True)
        fact_matches['Pts'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 3, np.where(fact_matches['Scored_FT'] == fact_matches['Conceded_FT'], 1, 0))
        
        team_stats = fact_matches.groupby('Team').agg(Avg_Scored=('Scored_FT', 'mean'), Avg_Conceded=('Conceded_FT', 'mean'), Total_Pts=('Pts', 'sum')).reset_index()
        fig4 = px.scatter(team_stats, x='Avg_Conceded', y='Avg_Scored', text='Team', size='Total_Pts', size_max=25, color_discrete_sequence=['#D97757'])
        fig4.update_traces(textposition='top center')
        fig4.add_hline(y=team_stats['Avg_Scored'].mean(), line_dash="dash", line_color="#8C8C8C")
        fig4.add_vline(x=team_stats['Avg_Conceded'].mean(), line_dash="dash", line_color="#8C8C8C")
        fig4.update_layout(title="The Chaos Quadrant", xaxis_title="Avg Goals Conceded", yaxis_title="Avg Goals Scored", plot_bgcolor="#FBFBF9")
        st.plotly_chart(fig4, use_container_width=True)

elif app_mode == "📈 Team Trends (xG vs Actual)":
    st.title("📈 Team Trends: Expected vs Actual")
    if not understat_shooting_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(understat_shooting_df['season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw]
        col1, col2 = st.columns(2)
        selected_team = col1.selectbox("Select Team:", sorted(list(set(szn_df['home_team_std'].tolist() + szn_df['away_team_std'].tolist()))))
        metric_choice = col2.selectbox("Select Metric:", ["Goals For", "Goals Against"])
        
        team_matches = szn_df[(szn_df['home_team_std'] == selected_team) | (szn_df['away_team_std'] == selected_team)].copy()
        actual_vals, expected_vals = [], []
        for _, row in team_matches.iterrows():
            is_home = (row['home_team_std'] == selected_team)
            if metric_choice == "Goals For":
                actual_vals.append(row['home_goals'] if is_home else row['away_goals'])
                expected_vals.append(float(row.get('home_xg', row.get('home_xG', 0.0))) if is_home else float(row.get('away_xg', row.get('away_xG', 0.0))))
            else:
                actual_vals.append(row['away_goals'] if is_home else row['home_goals'])
                expected_vals.append(float(row.get('away_xg', row.get('away_xG', 0.0))) if is_home else float(row.get('home_xg', row.get('home_xG', 0.0))))
                
        trend_df = pd.DataFrame({'Gameweek': range(1, len(actual_vals) + 1), 'Actual': np.cumsum(actual_vals), 'Expected': np.cumsum(expected_vals)})
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Actual'], mode='lines+markers', name=f'Actual {metric_choice}', line=dict(color='#D97757', width=3)))
        fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Expected'], mode='lines', name=f'Expected {metric_choice}', line=dict(color='#8C8C8C', width=3, dash='dot')))
        fig.update_layout(plot_bgcolor="#FBFBF9", xaxis_title="Match Number", yaxis_title=f"Cumulative {metric_choice}")
        st.plotly_chart(fig, use_container_width=True)
