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
    
    h1, h2, h3 {
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
        padding: 20px; 
        margin-bottom: 12px; 
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
    
    .score-box { background: #F9F8F6; border: 1px solid #E5E2DC; border-radius: 8px; padding: 10px 20px; font-size: 22px; font-weight: 700; letter-spacing: 1px; color: #1A1A1A; }
    
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
    VALID_USERS = {"olu": "admin123", "friend1": "passcode1"}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h1 style='text-align: center; margin-top: 50px; font-family: \"Lora\", serif;'>🔐 EPL Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8C8C8C;'>Secure access required.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='background: #FFFFFF; padding: 30px; border-radius: 12px; border: 1px solid #E5E2DC; box-shadow: 0 4px 16px rgba(0,0,0,0.03);'>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if username in VALID_USERS and VALID_USERS[username] == password:
                st.session_state["authenticated"] = True
                
                # Dynamic ID assignment based on login
                if username.lower() == "olu" or username == "2783761":
                    st.session_state["default_manager_id"] = "2783761"
                    st.session_state["default_league_id"] = "685121"
                else:
                    st.session_state["default_manager_id"] = username if username.isdigit() else ""
                    st.session_state["default_league_id"] = ""
                    
                st.rerun()
            else:
                st.error("⚠️ Invalid Username or Password")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

chart_theme = "streamlit"

def format_season(season_str):
    season_str = str(season_str)
    if re.match(r'^20\d{2}$', season_str):
        next_year = int(season_str) + 1
        return f"{season_str}/{next_year} Season"
    elif re.match(r'^\d{4}$', season_str):
        return f"20{season_str[:2]}/20{season_str[2:]} Season"
    return season_str

# ==========================================
# 3. DATA LOADERS & MULTI-GW MATH ENGINE
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
    
    players['team_name'] = players['team'].map(dict(zip(teams['id'], teams['name'])))
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
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def calculate_hybrid_metrics(p_df, t_df, u_df, w_long, w_short, fa_boost, ha_boost, min_mins, w_form, w_own, w_ict, blend_factor, horizon):
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
    
    t_stats = {}
    if not u_df.empty:
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
            if m > 0: t_stats[t] = {'xg_p90': tot_xg / m, 'xgc_p90': tot_xgc / m}
                
    league_avg_xg = np.mean([v['xg_p90'] for v in t_stats.values()]) if t_stats else 1.35
    league_avg_xgc = np.mean([v['xgc_p90'] for v in t_stats.values()]) if t_stats else 1.35
    
    def get_stat(team_name, stat):
        m = {"Man City": "Manchester City", "Man Utd": "Manchester United", "Newcastle": "Newcastle United", "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Wolves": "Wolverhampton Wanderers"}
        name = m.get(team_name, team_name)
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
        
        opp_name = opp_short.map(short_to_full).fillna('Average Team')
        opp_xg = opp_name.apply(lambda x: get_stat(x, 'xg_p90'))
        opp_xgc = opp_name.apply(lambda x: get_stat(x, 'xgc_p90'))
        
        fdr_mult = 1.0 + (3 - fdr) * 0.1
        attack_mult = (opp_xgc / league_avg_xgc).clip(0.5, 2.0) * fdr_mult
        def_mult = (opp_xg / league_avg_xg).clip(0.5, 2.0) * (1.0 / fdr_mult)
        ha_factor = np.where(is_home, 1.0 + ha_boost, 1.0 - ha_boost)
        
        gw_goal = np.where(is_eligible & (opp_short != 'Blank'), (df['xg_p90'] * df['goal_val']) * attack_mult * ha_factor, 0.0)
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

def get_poisson_probability(lam, k):
    return (math.exp(-lam) * (lam**k)) / math.factorial(k)

players_df, teams_df = load_fpl_data()
match_df = load_match_data()
understat_shooting_df = load_understat_data() 

if players_df.empty:
    st.error("🚨 FPL API is currently unreachable. Please try again later.")
    st.stop()

# ==========================================
# 4. SIDEBAR NAVIGATION 
# ==========================================
st.sidebar.title("⚽ EPL HUB")
st.sidebar.markdown("---")

menu_category = st.sidebar.selectbox("Select Category:", ["🏆 Fantasy Premier League", "⚽ EPL Matches & Stats", "📈 Betting Advisor"])
st.sidebar.markdown("---")

st.sidebar.header("👤 Your FPL Context")
user_manager_id = st.sidebar.text_input("My Manager ID:", value=st.session_state.get("default_manager_id", ""))
user_league_id = st.sidebar.text_input("My Mini-League ID:", value=st.session_state.get("default_league_id", ""))
st.sidebar.markdown("---")

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
    preset = st.sidebar.selectbox("🎯 Strategy Preset:", ["The Sweet Spot", "Custom", "The Form Chaser", "The Crowd Chaser", "The ICT Chaser"])
    
    if preset != "Custom":
        if "Sweet Spot" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 3, 50.0, 1.35, 0.06
            w_form, w_own, w_ict, blend_factor_g = 5, 5, 90, 10.0
        elif "Form Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 1, 25.0, 1.40, 0.05
            w_form, w_own, w_ict, blend_factor_g = 80, 10, 10, 40.0
        elif "Crowd Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 1, 25.0, 1.40, 0.05
            w_form, w_own, w_ict, blend_factor_g = 10, 80, 10, 40.0
        elif "ICT Chaser" in preset:
            horizon_g, min_mins_g, fa_boost_g, ha_boost_g = 3, 45.0, 1.35, 0.05
            w_form, w_own, w_ict, blend_factor_g = 0, 0, 100, 25.0
            
        st.sidebar.info(f"Using **{preset}** settings.")
    else:
        horizon_g = st.sidebar.slider("Planning Horizon (Gameweeks)", 1, 5, 3, 1)
        min_mins_g = st.sidebar.slider("Min Mins/Game Filter", 10.0, 90.0, 25.0, 5.0)
        st.sidebar.markdown("**Poisson Model Weights**")
        fa_boost_g = st.sidebar.slider("Fantasy Assist Boost", 1.0, 1.8, 1.40, 0.05)
        ha_boost_g = st.sidebar.slider("Home/Away Factor", 0.0, 0.15, 0.05, 0.01)
        st.sidebar.markdown("**ICT / Form Hybrid Weights**")
        w_form = st.sidebar.slider("Form (Short-Term)", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
        w_ict = st.sidebar.slider("ICT Index (Quality)", 0, 100, 40, 5)
        blend_factor_g = st.sidebar.slider("ICT Impact on xP (%)", 0.0, 50.0, 15.0, 5.0)

elif menu_category == "⚽ EPL Matches & Stats":
    app_mode = st.sidebar.radio("Select Module:", ["📅 Match Results & Fixtures", "📊 Live League Table", "📈 Team Trends (xG vs Actual)"])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g, horizon_g = 0.8, 0.2, 1.4, 0.05, 25.0, 3
    w_form, w_own, w_ict, blend_factor_g = 0, 0, 0, 0.0

elif menu_category == "📈 Betting Advisor":
    app_mode = st.sidebar.radio("Select Module:", ["📈 Predictive Match Analytics", "🎯 Poisson Match Predictor"])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g, horizon_g = 0.8, 0.2, 1.4, 0.05, 25.0, 3
    w_form, w_own, w_ict, blend_factor_g = 0, 0, 0, 0.0

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

if menu_category == "🏆 Fantasy Premier League":
    master_df = calculate_hybrid_metrics(players_df, teams_df, understat_shooting_df, 0.8, 0.2, fa_boost_g, ha_boost_g, min_mins_g, w_form, w_own, w_ict, blend_factor_g, horizon_g)

# ==========================================
# FPL MODULE 0: DASHBOARD
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
        
    st.info("👈 Select a module from the sidebar to dive deeper into analytics, squad optimization, and mini-league tracking.")

# ==========================================
# FPL MODULE 1: ADVANCED PLAYER SCOUT
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
                            <div style="color: #555555; font-size: 0.8rem; margin-bottom: 5px;">{horizon_g}-GW Horizon xP: {p_data['v2_xp']:.2f} | ICT Form Nudge: <span style="color: {boost_color};">{boost_sign}{boost_pct:.1f}%</span></div>
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
                
                st.markdown("### 📊 Performance Percentiles & Market Profile")
                rc1, rc2 = st.columns([1, 1])
                with rc1:
                    metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat (Goal Danger)': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
                    for label, col_name in metrics.items():
                        if col_name in players_df.columns:
                            val = p_data[col_name]
                            percentile = int((players_df[col_name] < val).mean() * 100)
                            st.markdown(f"<div style='margin-bottom:-10px; font-size: 14px; color: #555555;'><b>{label}</b>: <span style='color:#D97757; font-family: \"Fira Code\", monospace; font-weight:600;'>{val}</span> <span style='opacity: 0.6; font-size:12px;'>(Top {100-percentile}%)</span></div>", unsafe_allow_html=True)
                            st.progress(percentile / 100.0)
                
                with rc2:
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
            else:
                c_a, c_b = st.columns(2)
                with c_a: player_a = st.selectbox("Select Player A:", player_list, index=0)
                with c_b: player_b = st.selectbox("Select Player B:", player_list, index=1 if len(player_list) > 1 else 0)
                
                p_data_a = filtered_df[filtered_df['full_name'] == player_a].iloc[0]
                p_data_b = filtered_df[filtered_df['full_name'] == player_b].iloc[0]
                
                c_a.markdown(render_scout_card(p_data_a), unsafe_allow_html=True)
                c_b.markdown(render_scout_card(p_data_b), unsafe_allow_html=True)

# ==========================================
# FPL MODULE 2: UNIFIED DATA & POINTS MATRIX
# ==========================================
elif app_mode == "🗄️ Model Data & Points Matrix":
    st.title(f"🗄️ Model Data & {horizon_g}-GW Expected Points")
    st.write(f"Explore the underlying data bank and see exactly how the unified Multi-GW model calculates every expected point across your selected {horizon_g}-GW horizon.")
    
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
        
        st.markdown(f"### 🧮 Granular Data Matrix (Aggregated {horizon_g}-GW Horizon)")
        matrix_cols = ['full_name', 'position', 'team_name', 'mins_per_game', 'exp_app_pts', 'exp_goal_pts', 'exp_assist_pts', 'prob_cs', 'exp_cs_pts', 'hybrid_multiplier', 'v2_xp', 'final_xp']
        
        export_df = filtered_matrix[matrix_cols].sort_values(by='final_xp', ascending=False)
        st.download_button("💾 Export Matrix to CSV (For Power BI)", export_df.to_csv(index=False), "fpl_matrix_export.csv", "text/csv", use_container_width=True)
        
        st.dataframe(export_df, width="stretch", hide_index=True, column_config={"full_name": st.column_config.TextColumn("Player")})

    with tab2:
        st.markdown("### 🗄️ Raw Underlying Player Data Bank")
        cols_to_show = ['full_name', 'team_name', 'position', 'cost_m', 'minutes', 'mins_per_game', 'xg_p90', 'xa_p90', 'is_pen_taker', 'team_xgc', 'opp_name']
        st.dataframe(master_df[cols_to_show], width="stretch", hide_index=True)

# ==========================================
# FPL MODULE 3: FIXTURE MULTIPLIERS
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
# FPL MODULE 4: UNIFIED SOLVER
# ==========================================
elif app_mode == "⚡ Unified Squad Optimizer":
    st.title("⚡ Prescriptive Squad Optimizer (Hybrid Model)")
    
    st.sidebar.markdown("---")
    budget_v2 = st.sidebar.number_input("1. Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    bench_weight_v2 = st.sidebar.slider("2. Bench Investment Weight", 0.0, 1.0, 0.1, 0.1)
    target_formation_v2 = st.sidebar.selectbox("3. Preferred Starting Formation:", ["Auto (Best Points)", "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"])
    exclude_injured = st.sidebar.checkbox("4. Hide Injured/Suspended Players", value=True)
    
    if master_df is not None:
        locked_players_v2 = st.sidebar.multiselect("5. Select up to 14 must-have players:", sorted(master_df['full_name'].tolist()), max_selections=14)
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
            else: st.error("No optimal solution found for the current constraints.")

# ==========================================
# FPL MODULE 5: TRANSFER SUGGESTER
# ==========================================
elif app_mode == "🔄 Transfer Suggester":
    st.title("🔄 Transfer Suggester")
    st.sidebar.markdown("---")
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
                    squad_vars, starter_vars, bench_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary'), pulp.LpVariable.dicts("starter", df.index, cat='Binary'), pulp.LpVariable.dicts("bench", df.index, cat='Binary')
                    
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
                    else: st.error("No valid transfer sequence found.")
            else: st.error("Could not load a complete 15-man squad.")
        else: st.error("Invalid Manager ID.")

# ==========================================
# FPL MODULE 6: MINI-LEAGUE VIEWER
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
                            gw_summary.append({"Gameweek": f"GW {gw}", "Team Name": "Data Unavailable", "Manager": "-", "Points": None})
                    else:
                        gw_summary.append({"Gameweek": f"GW {gw}", "Team Name": "-", "Manager": "-", "Points": None})
                
                st.markdown("### 📅 Weekly Champions")
                st.dataframe(
                    pd.DataFrame(gw_summary), 
                    width="stretch", 
                    hide_index=True,
                    column_config={"Points": st.column_config.NumberColumn("Points", format="%d")}
                )

            with tab3:
                if not history_df.empty:
                    month_summary = []
                    chronological_months = history_df.sort_values('GW')['Month'].unique()
                    
                    for month in chronological_months:
                        month_df = history_df[history_df['Month'] == month]
                        month_totals = month_df.groupby(['Manager', 'Team'])['Net Points'].sum().reset_index()
                        month_totals = month_totals.sort_values(by='Net Points', ascending=False).head(3)
                        
                        positions = ["Winner 🥇", "Runner up 🥈", "Second Runner up 🥉"]
                        for idx, (_, row) in enumerate(month_totals.iterrows()):
                            month_summary.append({
                                "Month": month,
                                "Position": positions[idx],
                                "Team Name": row['Team'],
                                "Points": row['Net Points']
                            })
                    
                    st.markdown("### 🗓️ Manager of the Month Awards")
                    st.dataframe(
                        pd.DataFrame(month_summary), 
                        width="stretch", 
                        hide_index=True,
                        column_config={"Points": st.column_config.NumberColumn("Points", format="%d")}
                    )
                else:
                    st.info("No monthly data available yet. Check back after a few gameweeks have finished!")
        else: 
            st.error("Failed to load league standings. Please check your Mini-League ID.")

# ==========================================
# MODULE: REAL EPL MATCHES & STATS
# ==========================================
elif app_mode == "📅 Match Results & Fixtures":
    st.title("📅 Match Results & Fixtures")
    if understat_shooting_df is not None and not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season:", available_seasons, format_func=format_season)
        szn_matches = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].copy()
        if not szn_matches.empty:
            szn_matches = szn_matches.sort_values('date', ascending=True)
            szn_matches['gameweek'] = (szn_matches.groupby('season').cumcount() // 10) + 1
            max_gw = int(szn_matches['gameweek'].max())
            selected_gw_num = int(st.selectbox("Select Matchweek:", [f"Gameweek {i}" for i in range(1, max_gw + 1)]).split(" ")[1])
            gw_matches = szn_matches[szn_matches['gameweek'] == selected_gw_num].sort_values('date')
            
            for _, row in gw_matches.iterrows():
                st.markdown(f"""
                <div class="fixture-card">
                    <div style="width: 35%; text-align: right;">
                        <div style="font-size: 1.1rem; font-weight: 600;">{row['home_team']}</div>
                        <div style="font-size: 0.85rem; color: #D97757;">xG: {float(row.get('home_xG', row.get('home_xg', 0.0))):.2f}</div>
                    </div>
                    <div style="width: 30%; text-align: center;">
                        <div class="score-box">{int(row['home_goals'])} - {int(row['away_goals'])}</div>
                    </div>
                    <div style="width: 35%; text-align: left;">
                        <div style="font-size: 1.1rem; font-weight: 600;">{row['away_team']}</div>
                        <div style="font-size: 0.85rem; color: #8C8C8C;">xG: {float(row.get('away_xG', row.get('away_xg', 0.0))):.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

elif app_mode == "📊 Live League Table":
    st.title("📊 Expected vs Actual League Table")
    if not understat_shooting_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(understat_shooting_df['season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date')
        
        team_records = {team: {'W': 0, 'D': 0, 'L': 0, 'Pts': 0, 'GD': 0, 'GF': 0, 'GA': 0, 'xG': 0.0, 'xGA': 0.0} for team in pd.concat([szn_df['home_team'], szn_df['away_team']]).unique()}
        for _, row in szn_df.iterrows():
            h, a, h_g, a_g = row['home_team'], row['away_team'], row['home_goals'], row['away_goals']
            team_records[h]['GF'] += h_g; team_records[h]['GA'] += a_g; team_records[h]['GD'] += (h_g - a_g); team_records[h]['xG'] += float(row.get('home_xG', row.get('home_xg', 0.0))); team_records[h]['xGA'] += float(row.get('away_xG', row.get('away_xg', 0.0)))
            team_records[a]['GF'] += a_g; team_records[a]['GA'] += h_g; team_records[a]['GD'] += (a_g - h_g); team_records[a]['xG'] += float(row.get('away_xG', row.get('away_xg', 0.0))); team_records[a]['xGA'] += float(row.get('home_xG', row.get('home_xg', 0.0)))
            
            if h_g > a_g: team_records[h]['Pts'] += 3; team_records[h]['W'] += 1; team_records[a]['L'] += 1
            elif a_g > h_g: team_records[a]['Pts'] += 3; team_records[a]['W'] += 1; team_records[h]['L'] += 1
            else: team_records[h]['Pts'] += 1; team_records[a]['Pts'] += 1; team_records[h]['D'] += 1; team_records[a]['D'] += 1
            
        table_df = pd.DataFrame([{'Club': k, 'Pts': v['Pts'], 'GD': v['GD'], 'GF': v['GF'], 'xG': v['xG'], 'GA': v['GA'], 'xGA': v['xGA']} for k, v in team_records.items()]).sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
        table_df.index += 1
        st.dataframe(table_df, width="stretch")

elif app_mode == "📈 Team Trends (xG vs Actual)":
    st.title("📈 Team Trends: Expected vs Actual")
    if not understat_shooting_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(understat_shooting_df['season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw]
        col1, col2 = st.columns(2)
        selected_team = col1.selectbox("Select Team:", sorted(list(set(szn_df['home_team'].tolist() + szn_df['away_team'].tolist()))))
        metric_choice = col2.selectbox("Select Metric:", ["Goals For", "Goals Against"])
        
        team_matches = szn_df[(szn_df['home_team'] == selected_team) | (szn_df['away_team'] == selected_team)].copy()
        actual_vals, expected_vals = [], []
        for _, row in team_matches.iterrows():
            is_home = (row['home_team'] == selected_team)
            if metric_choice == "Goals For":
                actual_vals.append(row['home_goals'] if is_home else row['away_goals'])
                expected_vals.append(float(row.get('home_xG', row.get('home_xg', 0.0))) if is_home else float(row.get('away_xG', row.get('away_xg', 0.0))))
            else:
                actual_vals.append(row['away_goals'] if is_home else row['home_goals'])
                expected_vals.append(float(row.get('away_xG', row.get('away_xg', 0.0))) if is_home else float(row.get('home_xG', row.get('home_xg', 0.0))))
                
        trend_df = pd.DataFrame({'Gameweek': range(1, len(actual_vals) + 1), 'Actual': np.cumsum(actual_vals), 'Expected': np.cumsum(expected_vals)})
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Actual'], mode='lines+markers', name=f'Actual {metric_choice}', line=dict(color='#D97757', width=3)))
        fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Expected'], mode='lines', name=f'Expected {metric_choice}', line=dict(color='#8C8C8C', width=3, dash='dot')))
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Show Raw Data Table"):
            st.dataframe(understat_shooting_df, width="stretch")

# ==========================================
# MODULE 6: BETTING ADVISOR
# ==========================================
elif app_mode == "📈 Predictive Match Analytics":
    st.title("📈 Chaos Quadrant & Match Trends")
    if not match_df.empty:
        selected_season_raw = st.selectbox("Select Season:", sorted(match_df['Season'].unique().tolist(), reverse=True), format_func=format_season)
        szn_match_df = match_df[match_df['Season'] == selected_season_raw]
        
        home_m, away_m = szn_match_df[['Match_ID', 'Home_Team', 'Home_Score_FT', 'Away_Score_FT']].copy(), szn_match_df[['Match_ID', 'Away_Team', 'Away_Score_FT', 'Home_Score_FT']].copy()
        home_m.columns, away_m.columns = ['Match_ID', 'Team', 'Scored_FT', 'Conceded_FT'], ['Match_ID', 'Team', 'Scored_FT', 'Conceded_FT']
        fact_matches = pd.concat([home_m, away_m], ignore_index=True)
        fact_matches['Pts'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 3, np.where(fact_matches['Scored_FT'] == fact_matches['Conceded_FT'], 1, 0))
        
        team_stats = fact_matches.groupby('Team').agg(Avg_Scored=('Scored_FT', 'mean'), Avg_Conceded=('Conceded_FT', 'mean'), Total_Pts=('Pts', 'sum')).reset_index()
        fig4 = px.scatter(team_stats, x='Avg_Conceded', y='Avg_Scored', text='Team', size='Total_Pts', size_max=25, color_discrete_sequence=['#D97757'])
        fig4.update_traces(textposition='top center')
        fig4.add_hline(y=team_stats['Avg_Scored'].mean(), line_dash="dash", line_color="#8C8C8C"); fig4.add_vline(x=team_stats['Avg_Conceded'].mean(), line_dash="dash", line_color="#8C8C8C")
        fig4.update_layout(title="The Chaos Quadrant", xaxis_title="Avg Goals Conceded", yaxis_title="Avg Goals Scored")
        st.plotly_chart(fig4, width="stretch")

elif app_mode == "🎯 Poisson Match Predictor":
    st.title("🎯 Bivariate Poisson Match Predictor")
    st.write("Calculates theoretical match outcomes based on average team xG and xGA across the selected season.")
    if not understat_shooting_df.empty:
        latest_szn = understat_shooting_df['season'].max()
        curr_df = understat_shooting_df[understat_shooting_df['season'] == latest_szn]
        
        teams = sorted(list(set(curr_df['home_team'].tolist() + curr_df['away_team'].tolist())))
        c1, c2 = st.columns(2)
        home_t = c1.selectbox("Select Home Team:", teams, index=0)
        away_t = c2.selectbox("Select Away Team:", teams, index=1 if len(teams) > 1 else 0)
        
        h_data_home = curr_df[curr_df['home_team'] == home_t]
        h_data_away = curr_df[curr_df['away_team'] == home_t]
        avg_home_xg = (h_data_home.get('home_xG', h_data_home.get('home_xg', pd.Series([1.35]))).sum() + h_data_away.get('away_xG', h_data_away.get('away_xg', pd.Series([1.35]))).sum()) / max(1, len(h_data_home) + len(h_data_away))
        
        a_data_home = curr_df[curr_df['home_team'] == away_t]
        a_data_away = curr_df[curr_df['away_team'] == away_t]
        avg_away_xg = (a_data_home.get('home_xG', a_data_home.get('home_xg', pd.Series([1.35]))).sum() + a_data_away.get('away_xG', a_data_away.get('away_xg', pd.Series([1.35]))).sum()) / max(1, len(a_data_home) + len(a_data_away))
        
        h_win, draw, a_win = 0.0, 0.0, 0.0
        for i in range(7):
            for j in range(7):
                prob = get_poisson_probability(avg_home_xg, i) * get_poisson_probability(avg_away_xg, j)
                if i > j: h_win += prob
                elif i == j: draw += prob
                else: a_win += prob
                
        st.markdown(f"### {home_t} ({h_win*100:.1f}%) | Draw ({draw*100:.1f}%) | {away_t} ({a_win*100:.1f}%)")
        st.progress(h_win)
        st.progress(draw)
        st.progress(a_win)
