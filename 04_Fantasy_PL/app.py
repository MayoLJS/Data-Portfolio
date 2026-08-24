import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go
import re
from streamlit_echarts import st_echarts

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

# ==========================================
# 2. AUTHENTICATION GATEKEEPER
# ==========================================
VALID_USERS = {
    "olu": "admin123",
    "friend1": "passcode1"
}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔐 Welcome to EPL Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Please enter your credentials to access the app.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='background: var(--secondary-background-color); padding: 30px; border-radius: 12px; border: 1px solid var(--border-color);'>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if username in VALID_USERS and VALID_USERS[username] == password:
                st.session_state["authenticated"] = True
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
# 3. DATA LOADERS & HYBRID MATH ENGINE
# ==========================================
@st.cache_data(ttl=3600)
def get_current_event():
    try:
        r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=5).json()
        for e in r['events']:
            if e['is_current']: return e['id']
        return 1
    except: return 1

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
    players['predicted_points'] = pd.to_numeric(players.get('ep_next', 0), errors='coerce').fillna(0.0)
    players['next_opponent'] = "N/A"
    
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
        return None

def calculate_hybrid_metrics(p_df, t_df, u_df, w_long, w_short, fa_boost, ha_boost, min_mins, weights_dict, blend_factor):
    if p_df is None or t_df is None: return pd.DataFrame()
        
    df = p_df.copy()
    df['full_name'] = df['first_name'] + " " + df['second_name']
    
    df['mins_played'] = pd.to_numeric(df.get('minutes', 0), errors='coerce').fillna(0)
    max_possible_games = max(1.0, round(df['mins_played'].max() / 90.0))
    df['mins_per_game'] = (df['mins_played'] / max_possible_games).round(1)
    is_eligible = df['mins_per_game'] >= min_mins
    
    dampener = np.clip(df['mins_per_game'] / 60.0, 0.4, 1.0)
    df['xg_p90'] = np.where(is_eligible & (df['mins_played'] > 0), (df['expected_goals'] / df['mins_played']) * 90.0 * dampener, 0.0)
    df['xa_p90'] = np.where(is_eligible & (df['mins_played'] > 0), (df['expected_assists'] / df['mins_played']) * 90.0 * dampener, 0.0)
    
    df['is_home'] = df['next_opponent'].str.contains(r'\(H\)', regex=True)
    df['opp_short'] = df['next_opponent'].str.replace(' (H)', '', regex=False).str.replace(' (A)', '', regex=False)
    short_to_full = dict(zip(t_df['short_name'], t_df['name']))
    df['opp_name'] = df['opp_short'].map(short_to_full).fillna('Average Team')
    
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
            if m > 0: t_stats[t] = {'xg_p90': tot_xg / m, 'xgc_p90': tot_xgc / m}
                
    league_avg_xg = np.mean([v['xg_p90'] for v in t_stats.values()]) if t_stats else 1.35
    league_avg_xgc = np.mean([v['xgc_p90'] for v in t_stats.values()]) if t_stats else 1.35
    
    def get_stat(team_name, stat):
        m = {"Man City": "Manchester City", "Man Utd": "Manchester United", "Newcastle": "Newcastle United", "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Wolves": "Wolverhampton Wanderers"}
        name = m.get(team_name, team_name)
        return t_stats.get(name, {}).get(stat, league_avg_xg)
        
    df['team_xgc'] = df['team_name'].apply(lambda x: get_stat(x, 'xgc_p90'))
    df['opp_xg'] = df['opp_name'].apply(lambda x: get_stat(x, 'xg_p90'))
    df['opp_xgc'] = df['opp_name'].apply(lambda x: get_stat(x, 'xgc_p90'))
    
    fit_prob = df['chance_of_playing_next_round'] / 100.0
    df['p_app_1'] = np.where(is_eligible, np.clip(df['mins_per_game'] / 25.0, 0.0, 1.0) * 0.95 * fit_prob, 0.0)
    df['p_app_2'] = np.where(is_eligible, np.clip((df['mins_per_game'] - 40.0) / 40.0, 0.0, 1.0) * 0.85 * fit_prob, 0.0)
    df['exp_app_pts'] = df['p_app_1'] * 1.0 + df['p_app_2'] * 1.0
    
    goal_pts_map = {1: 6, 2: 6, 3: 5, 4: 4}
    df['goal_val'] = df['element_type'].map(goal_pts_map)
    df['attack_mult'] = (df['opp_xgc'] / league_avg_xgc).clip(0.5, 2.0)
    df['exp_goal_pts'] = np.where(is_eligible, (df['xg_p90'] * df['goal_val']) * df['attack_mult'], 0.0)
    df['exp_assist_pts'] = np.where(is_eligible, (df['xa_p90'] * 3.0 * fa_boost) * df['attack_mult'], 0.0)
    
    df['def_mult'] = (df['opp_xg'] / league_avg_xg).clip(0.5, 2.0)
    df['match_xgc'] = df['team_xgc'] * df['def_mult']
    df['prob_cs'] = np.where(is_eligible, np.exp(-df['match_xgc']), 0.0)
    df['prob_conc_2plus'] = np.where(is_eligible, 1.0 - np.exp(-df['match_xgc']) * (1.0 + df['match_xgc']), 0.0)
    
    df['cs_val'] = df['element_type'].map({1: 4.0, 2: 4.0, 3: 1.0, 4: 0.0})
    df['conc_penalty_val'] = df['element_type'].map({1: -1.0, 2: -1.0, 3: 0.0, 4: 0.0})
    df['exp_cs_pts'] = np.where(is_eligible, df['prob_cs'] * df['cs_val'] * df['p_app_2'], 0.0)
    df['exp_conc_penalty'] = np.where(is_eligible, df['prob_conc_2plus'] * df['conc_penalty_val'] * df['p_app_1'], 0.0)
    df['exp_bonus_pts'] = np.where(is_eligible & (df['mins_played'] > 0), (df['bps'] / df['mins_played']) * 90.0 * 0.04 * dampener, 0.0)
    
    df['raw_xp'] = df['exp_app_pts'] + df['exp_goal_pts'] + df['exp_assist_pts'] + df['exp_cs_pts'] + df['exp_conc_penalty'] + df['exp_bonus_pts']
    ha_factor = np.where(df['is_home'], 1.0 + ha_boost, 1.0 - ha_boost)
    df['v2_xp'] = np.where(is_eligible, (df['raw_xp'] * ha_factor).round(2), 0.0)

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
    r_boot = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
    gw_to_month = {}
    completed_gws = []
    for e in r_boot['events']:
        if e['finished']:
            month = pd.to_datetime(e['deadline_time']).strftime('%B %Y')
            gw_to_month[e['id']] = month
            completed_gws.append(e['id'])
            
    r_standings = requests.get(f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/").json()
    entries = r_standings.get('standings', {}).get('results', [])[:50] 
    league_name = r_standings.get('league', {}).get('name', 'Unknown League')
    
    history_data = []
    for entry in entries:
        try:
            r_hist = requests.get(f"https://fantasy.premierleague.com/api/entry/{entry['entry']}/history/").json()
            for gw in r_hist['current']:
                if gw['event'] in completed_gws:
                    history_data.append({
                        'Manager': entry['player_name'],
                        'Team': entry['entry_name'],
                        'GW': gw['event'],
                        'Net Points': gw['points'] - gw['event_transfers_cost'],
                        'Month': gw_to_month.get(gw['event'], 'Unknown')
                    })
        except:
            continue
            
    return pd.DataFrame(history_data), league_name, r_standings.get('standings', {}).get('results', []), completed_gws

players_df, teams_df = load_fpl_data()
match_df = load_match_data()
understat_shooting_df = load_understat_data() 

# ==========================================
# 4. SIDEBAR NAVIGATION 
# ==========================================
st.sidebar.title("⚽ EPL HUB")
st.sidebar.markdown("---")

menu_category = st.sidebar.selectbox("Select Category:", ["🏆 Fantasy Premier League", "⚽ EPL Matches & Stats", "📈 Betting Advisor"])

st.sidebar.markdown("---")
st.sidebar.header("👤 Your FPL Context")
user_manager_id = st.sidebar.text_input("My Manager ID:", value="2783761")
user_league_id = st.sidebar.text_input("My Mini-League ID:", value="685121")
st.sidebar.markdown("---")

if menu_category == "🏆 Fantasy Premier League":
    app_mode = st.sidebar.radio("Select Module:", [
        "👤 Advanced Player Scout",
        "🗄️ Model Data & Points Matrix",
        "📅 Fixture Multipliers",
        "⚡ Unified Squad Optimizer",
        "🔄 AI Transfer Suggester",
        "🏆 Live Mini-League Standings"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Unified Model Tuning")
    min_mins_g = st.sidebar.slider("Min Mins/Game Filter", 10.0, 90.0, 25.0, 5.0, help="Filters out benchwarmers and aggressively scales down expected points for players with low minutes.")
    
    st.sidebar.markdown("**Poisson Model Weights**")
    fa_boost_g = st.sidebar.slider("Fantasy Assist Boost", 1.0, 1.8, 1.40, 0.05, help="Multiplier for unrecorded FPL assists (rebounds/penalties).")
    ha_boost_g = st.sidebar.slider("Home/Away Factor", 0.0, 0.15, 0.05, 0.01, help="Percentage advantage given to home teams.")

    st.sidebar.markdown("**ICT / Form Hybrid Weights**")
    advanced_mode = st.sidebar.toggle("Advanced ICT Breakdown", value=False)
    
    if not advanced_mode:
        w_form = st.sidebar.slider("Form (Short-Term)", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
        w_ict = st.sidebar.slider("ICT Index (Quality)", 0, 100, 40, 5)
        weights_g = {'form': w_form, 'selected_by_percent': w_own, 'ict_index': w_ict}
    else:
        w_form = st.sidebar.slider("Form", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership %", 0, 100, 20, 5)
        w_inf = st.sidebar.slider("Influence", 0, 100, 20, 5)
        w_cre = st.sidebar.slider("Creativity", 0, 100, 20, 5)
        w_thr = st.sidebar.slider("Threat", 0, 100, 20, 5)
        weights_g = {'form': w_form, 'selected_by_percent': w_own, 'influence': w_inf, 'creativity': w_cre, 'threat': w_thr}
        
    blend_factor_g = st.sidebar.slider("ICT Impact on xP (%)", 0.0, 50.0, 15.0, 5.0, help="How much should the subjective ICT/Form sliders above boost or penalize the pure objective Poisson xP?")

elif menu_category == "⚽ EPL Matches & Stats":
    app_mode = st.sidebar.radio("Select Module:", [
        "📅 Match Results & Fixtures",
        "📊 Live League Table",
        "📈 Team Trends (xG vs Actual)",
        "🌐 Understat Team Stats" 
    ])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g = 0.8, 0.2, 1.4, 0.05, 25.0
    weights_g, blend_factor_g = {}, 0.0

elif menu_category == "📈 Betting Advisor":
    app_mode = st.sidebar.radio("Select Module:", [
        "📈 For your information only"
    ])
    w_long_g, w_short_g, fa_boost_g, ha_boost_g, min_mins_g = 0.8, 0.2, 1.4, 0.05, 25.0
    weights_g, blend_factor_g = {}, 0.0

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

# Pre-calculate master data for FPL modules
if menu_category == "🏆 Fantasy Premier League":
    master_df = calculate_hybrid_metrics(players_df, teams_df, understat_shooting_df, 0.8, 0.2, fa_boost_g, ha_boost_g, min_mins_g, weights_g, blend_factor_g)

# ==========================================
# FPL MODULE 1: ADVANCED PLAYER SCOUT
# ==========================================
if app_mode == "👤 Advanced Player Scout":
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
                chance_color = "#01fc7a" if chance_val == 100 else ("#ffcc00" if chance_val > 0 else "#ff005a")
                boost_pct = ((p_data['hybrid_multiplier'] - 1.0) * 100)
                boost_color = "#01fc7a" if boost_pct >= 0 else "#ff005a"
                boost_sign = "+" if boost_pct >= 0 else ""
                
                return f"""
                <div class="scout-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="margin-bottom: 12px;">
                                <span class="badge-cyan" style="margin-right: 8px;">{p_data['position']}</span>
                                <span class="badge-pink">{p_data['team_name']}</span>
                            </div>
                            <h2 style="margin: 0; font-size: 2.0rem; font-weight: 800; color: var(--text-color);">{p_data['first_name'].upper()} {p_data['second_name'].upper()}</h2>
                            <p style="margin: 8px 0 0 0; color: var(--text-color); opacity: 0.8; font-size: 1.0rem;">
                                Price: <b>£{p_data['cost_m']}M</b> &nbsp;|&nbsp; 
                                Pts: <b>{int(p_data['total_points'])}</b><br>
                                Next: <b>{p_data.get('next_opponent', 'N/A')}</b><br>
                                Fit: <b style="color: {chance_color};">{chance_val}%</b>
                            </p>
                        </div>
                        <div style="text-align: right; background: var(--background-color); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="color: var(--text-color); font-size: 0.8rem; margin-bottom: 5px;">Pure Poisson xP: {p_data['v2_xp']:.2f} | ICT Form Nudge: <span style="color: {boost_color};">{boost_sign}{boost_pct:.1f}%</span></div>
                            <h3 style="color: #0088cc; margin:0 0 5px 0; font-weight: 800;">Final Proj xP: {p_data['final_xp']:.2f}</h3>
                            <div style="color: var(--text-color); font-size: 0.9rem;">
                                Atk Mult: <b>{p_data['attack_mult']:.2f}x</b> &nbsp;|&nbsp; 
                                Poisson CS Odds: <b style="color: #01fc7a;">{p_data['prob_cs']*100:.0f}%</b>
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
                    for i, (label, col_name) in enumerate(metrics.items()):
                        if col_name in players_df.columns:
                            val = p_data[col_name]
                            percentile = int((players_df[col_name] < val).mean() * 100)
                            st.markdown(f"<div style='margin-bottom:-10px; font-size: 14px; color: var(--text-color);'><b>{label}</b>: <span style='color:#0088cc;'>{val}</span> <span style='opacity: 0.6; font-size:12px;'>(Top {100-percentile}%)</span></div>", unsafe_allow_html=True)
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
                            "indicator": [
                                {"name": "Threat", "max": 100},
                                {"name": "Creativity", "max": 100},
                                {"name": "Influence", "max": 100},
                                {"name": "xG", "max": 100},
                                {"name": "xA", "max": 100}
                            ],
                            "splitArea": {"show": False},
                            "axisName": {"color": "#8f9bba"}
                        },
                        "series": [{
                            "name": "Player Profile vs League",
                            "type": "radar",
                            "data": [
                                {
                                    "value": [pct_thr, pct_cre, pct_inf, pct_xg, pct_xa],
                                    "name": p_data['second_name'],
                                    "itemStyle": {"color": "#0088cc"},
                                    "areaStyle": {"color": "rgba(0, 136, 204, 0.4)"}
                                }
                            ]
                        }]
                    }
                    st_echarts(radar_options, height="300px")

            else:
                c_a, c_b = st.columns(2)
                with c_a:
                    player_a = st.selectbox("Select Player A:", player_list, index=0)
                with c_b:
                    idx_b = 1 if len(player_list) > 1 else 0
                    player_b = st.selectbox("Select Player B:", player_list, index=idx_b)
                
                p_data_a = filtered_df[filtered_df['full_name'] == player_a].iloc[0]
                p_data_b = filtered_df[filtered_df['full_name'] == player_b].iloc[0]
                
                c_a.markdown(render_scout_card(p_data_a), unsafe_allow_html=True)
                c_b.markdown(render_scout_card(p_data_b), unsafe_allow_html=True)
                
                st.markdown("### ⚔️ Dual-Radar Profile")
                def get_pct(col, p_data): return int((players_df[col] < p_data[col]).mean() * 100)
                
                radar_dual_opts = {
                    "tooltip": {"trigger": "item"},
                    "legend": {"data": [p_data_a['second_name'], p_data_b['second_name']], "textStyle": {"color": "#8f9bba"}},
                    "radar": {
                        "indicator": [
                            {"name": "Threat", "max": 100},
                            {"name": "Creativity", "max": 100},
                            {"name": "Influence", "max": 100},
                            {"name": "xG", "max": 100},
                            {"name": "xA", "max": 100}
                        ],
                        "splitArea": {"show": False},
                        "axisName": {"color": "#8f9bba"}
                    },
                    "series": [{
                        "name": "H2H Comparison",
                        "type": "radar",
                        "data": [
                            {
                                "value": [get_pct('threat', p_data_a), get_pct('creativity', p_data_a), get_pct('influence', p_data_a), get_pct('expected_goals', p_data_a), get_pct('expected_assists', p_data_a)],
                                "name": p_data_a['second_name'],
                                "itemStyle": {"color": "#0088cc"},
                                "areaStyle": {"color": "rgba(0, 136, 204, 0.4)"}
                            },
                            {
                                "value": [get_pct('threat', p_data_b), get_pct('creativity', p_data_b), get_pct('influence', p_data_b), get_pct('expected_goals', p_data_b), get_pct('expected_assists', p_data_b)],
                                "name": p_data_b['second_name'],
                                "itemStyle": {"color": "#cc0066"},
                                "areaStyle": {"color": "rgba(204, 0, 102, 0.4)"}
                            }
                        ]
                    }]
                }
                st_echarts(radar_dual_opts, height="400px")
                
# ==========================================
# FPL MODULE 2: UNIFIED DATA & POINTS MATRIX
# ==========================================
elif app_mode == "🗄️ Model Data & Points Matrix":
    st.title("🗄️ Model Data & Expected Points Decomposition")
    st.write("Explore the underlying data bank and see exactly how the unified Hybrid model calculates every expected point.")
    
    tab1, tab2 = st.tabs(["🧮 xP Breakdown Matrix", "🗄️ Master Player Data Bank"])
    
    with tab1:
        f1, f2 = st.columns(2)
        pos_filter = f1.selectbox("Filter Position:", ["All", "GKP", "DEF", "MID", "FWD"], key="matrix_pos")
        team_filter = f2.selectbox("Filter Club:", ["All"] + sorted(master_df['team_name'].unique().tolist()), key="matrix_team")
        
        filtered_matrix = master_df.copy()
        if pos_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['position'] == pos_filter]
        if team_filter != "All": filtered_matrix = filtered_matrix[filtered_matrix['team_name'] == team_filter]
        
        top_df = filtered_matrix.sort_values(by='final_xp', ascending=False).head(15).iloc[::-1]
        
        if not top_df.empty:
            st.markdown("### 📊 Top 15 Players xP Decomposition")
            stacked_options = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ["Appearance", "Attack", "Defense", "Bonus"], "textStyle": {"color": "#8f9bba"}},
                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                "xAxis": {"type": "value", "splitLine": {"show": False}},
                "yAxis": {"type": "category", "data": top_df['full_name'].tolist()},
                "color": ["#8f9bba", "#0088cc", "#01fc7a", "#ffcc00"],
                "series": [
                    {"name": "Appearance", "type": "bar", "stack": "total", "data": top_df['exp_app_pts'].round(2).tolist()},
                    {"name": "Attack", "type": "bar", "stack": "total", "data": (top_df['exp_goal_pts'] + top_df['exp_assist_pts']).round(2).tolist()},
                    {"name": "Defense", "type": "bar", "stack": "total", "data": (top_df['exp_cs_pts'] + top_df['exp_conc_penalty']).clip(lower=0).round(2).tolist()},
                    {"name": "Bonus", "type": "bar", "stack": "total", "data": top_df['exp_bonus_pts'].round(2).tolist()}
                ]
            }
            st_echarts(stacked_options, height="450px")
        
        st.markdown("### 🧮 Granular Data Matrix")
        matrix_cols = ['full_name', 'position', 'team_name', 'mins_per_game', 'exp_app_pts', 'exp_goal_pts', 'exp_assist_pts', 'prob_cs', 'exp_cs_pts', 'hybrid_multiplier', 'v2_xp', 'final_xp']
        st.dataframe(
            filtered_matrix[matrix_cols].sort_values(by='final_xp', ascending=False),
            width="stretch", hide_index=True,
            column_config={
                "full_name": st.column_config.TextColumn("Player"),
                "position": st.column_config.TextColumn("Pos"),
                "team_name": st.column_config.TextColumn("Club"),
                "mins_per_game": st.column_config.NumberColumn("Mins/Game", format="%.1f"),
                "exp_app_pts": st.column_config.NumberColumn("App xP", format="%.2f", help="Points from playing time."),
                "exp_goal_pts": st.column_config.NumberColumn("Goal xP", format="%.2f"),
                "exp_assist_pts": st.column_config.NumberColumn("Assist xP", format="%.2f"),
                "prob_cs": st.column_config.NumberColumn("CS Odds", format="%.2f", help="Poisson probability of Clean Sheet."),
                "exp_cs_pts": st.column_config.NumberColumn("CS xP", format="%.2f"),
                "hybrid_multiplier": st.column_config.NumberColumn("ICT Form Boost", format="%.2fx", help="Modifier applied from the subjective ICT/Form sliders."),
                "v2_xp": st.column_config.NumberColumn("Pure Poisson xP", format="%.2f"),
                "final_xp": st.column_config.NumberColumn("Final Blended xP", format="%.2f", help="Used by the Optimizer.")
            }
        )

    with tab2:
        st.markdown("### 🗄️ Raw Underlying Player Data Bank")
        cols_to_show = ['full_name', 'team_name', 'position', 'cost_m', 'minutes', 'mins_per_game', 'xg_p90', 'xa_p90', 'team_xgc', 'opp_name']
        st.dataframe(
            master_df[cols_to_show],
            width="stretch", hide_index=True,
            column_config={
                "full_name": st.column_config.TextColumn("Player"),
                "team_name": st.column_config.TextColumn("Club"),
                "position": st.column_config.TextColumn("Pos"),
                "cost_m": st.column_config.NumberColumn("Price (£M)", format="£%.1f"),
                "minutes": st.column_config.NumberColumn("Total Mins"),
                "mins_per_game": st.column_config.NumberColumn("Mins/Game", format="%.1f"),
                "xg_p90": st.column_config.NumberColumn("xG / 90", format="%.2f", help="Expected Goals per 90 (Dampened if low minutes)"),
                "xa_p90": st.column_config.NumberColumn("xA / 90", format="%.2f"),
                "team_xgc": st.column_config.NumberColumn("Team xGC", format="%.2f"),
                "opp_name": st.column_config.TextColumn("Next Opponent")
            }
        )

# ==========================================
# FPL MODULE 3: FIXTURE MULTIPLIERS
# ==========================================
elif app_mode == "📅 Fixture Multipliers":
    st.title("📅 Fixture Multipliers & Opponent Index")
    st.write("Compare team attacks and defenses against the league average to view relative match difficulty multipliers.")
    
    if not master_df.empty:
        team_summary = master_df.groupby(['team_name', 'opp_name', 'is_home']).agg(
            Attack_Multiplier=('attack_mult', 'first'),
            Defensive_Multiplier=('def_mult', 'first'),
            Expected_CS_Chance=('prob_cs', 'first')
        ).reset_index()
        
        team_summary['Venue'] = np.where(team_summary['is_home'], 'Home', 'Away')
        
        st.dataframe(
            team_summary[['team_name', 'Venue', 'Attack_Multiplier', 'Defensive_Multiplier', 'Expected_CS_Chance', 'opp_name']],
            width="stretch", hide_index=True,
            column_config={
                "team_name": st.column_config.TextColumn("Club"),
                "Venue": st.column_config.TextColumn("Venue"),
                "Attack_Multiplier": st.column_config.NumberColumn("Attack Multiplier (xGC Rel)", format="%.2fx", help="Boost applied to attacking players. Based on opponent defense compared to average."),
                "Defensive_Multiplier": st.column_config.NumberColumn("Defense Multiplier (xG Rel)", format="%.2fx", help="Modifier applied to team xGC. Based on opponent attack compared to average."),
                "Expected_CS_Chance": st.column_config.NumberColumn("Poisson CS Prob", format="%.2f", help="Exact probability of 0 goals conceded derived from adjusted xGC."),
                "opp_name": st.column_config.TextColumn("Opponent")
            }
        )

# ==========================================
# FPL MODULE 4: UNIFIED SOLVER
# ==========================================
elif app_mode == "⚡ Unified Squad Optimizer":
    st.title("⚡ Prescriptive Squad Optimizer (Hybrid Model)")
    st.write("Integer programming solver maximizing the **Final Blended xP** (Pure Poisson Math + ICT/Form Sliders).")
    
    st.sidebar.markdown("---")
    st.sidebar.header("1. Budget Constraints")
    budget_v2 = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.header("2. Bench Strategy")
    bench_weight_v2 = st.sidebar.slider("Bench Investment Weight", 0.0, 1.0, 0.1, 0.1)
    
    st.sidebar.header("3. Target Formation")
    formation_choices = ["Auto (Best Points)", "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"]
    target_formation_v2 = st.sidebar.selectbox("Preferred Starting Formation:", formation_choices)

    st.sidebar.header("4. Locked Players (Optional)")
    if master_df is not None:
        player_choices_v2 = sorted(master_df['full_name'].tolist())
        locked_players_v2 = st.sidebar.multiselect("Select up to 14 must-have players:", player_choices_v2, max_selections=14)
    else:
        locked_players_v2 = []

    if st.button("🚀 Run Hybrid Solver & Sensitivity", type="primary", width="stretch"):
        if not master_df.empty:
            df = master_df[(master_df['status'] == 'a') & ((master_df['mins_per_game'] >= min_mins_g) | (master_df['full_name'].isin(locked_players_v2)))].copy()
            
            prob = pulp.LpProblem("Optimal_FPL_Hybrid", pulp.LpMaximize)
            squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
            starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
            bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
            
            prob += pulp.lpSum([df.loc[i, 'final_xp'] * starter_vars[i] + bench_weight_v2 * df.loc[i, 'final_xp'] * bench_vars[i] for i in df.index])
            
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
                
            locked_indices_v2 = df[df['full_name'].isin(locked_players_v2)].index.tolist()
            for idx in locked_indices_v2:
                prob += squad_vars[idx] == 1
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                squad = df.loc[[i for i in df.index if squad_vars[i].varValue == 1]].copy()
                starters = df.loc[[i for i in df.index if starter_vars[i].varValue == 1]].copy()
                bench_raw = df.loc[[i for i in df.index if bench_vars[i].varValue == 1]].copy()
                
                bench_gkp = bench_raw[bench_raw['element_type'] == 1]
                bench_outfield = bench_raw[bench_raw['element_type'] > 1].sort_values(by='final_xp', ascending=False)
                bench = pd.concat([bench_gkp, bench_outfield])
                
                captain_id = starters['final_xp'].idxmax()
                captain_row = starters.loc[captain_id]
                total_xp = starters['final_xp'].sum() + captain_row['final_xp']
                
                st.success("✅ Hybrid Squad Solution Computed!")
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Spent Budget", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget_v2 - squad['cost_m'].sum():.1f}M")
                sc2.metric("Proj Points (Final xP)", f"{total_xp:.2f} pts")
                sc3.metric("Captain Pick", f"{captain_row['second_name']} ({captain_row['final_xp']:.2f} xP)")
                
                st.markdown("### 💰 Budget Allocation Treemap")
                treemap_data = [
                    {
                        "name": "Starting XI",
                        "itemStyle": {"color": "#0088cc"},
                        "children": [{"name": row.second_name, "value": row.cost_m} for row in starters.itertuples()]
                    },
                    {
                        "name": "Bench",
                        "itemStyle": {"color": "#cc0066"},
                        "children": [{"name": row.second_name, "value": row.cost_m} for row in bench.itertuples()]
                    }
                ]
                treemap_opts = {
                    "tooltip": {"trigger": "item", "formatter": "{b}: £{c}M"},
                    "series": [{
                        "type": "treemap",
                        "roam": False,
                        "nodeClick": False,
                        "breadcrumb": {"show": False},
                        "data": treemap_data,
                        "label": {"show": True, "formatter": "{b}\n£{c}M"}
                    }]
                }
                st_echarts(treemap_opts, height="250px")

                st.markdown("### 🏟️ Starting XI")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                def render_v2_pitch(row_df, card_class='pitch-card'):
                    if not row_df.empty:
                        cols = st.columns(len(row_df))
                        for col, p in zip(cols, row_df.itertuples()):
                            cap = "<span class='badge-cap'>C</span>" if p.Index == captain_id and card_class == 'pitch-card' else ""
                            col.markdown(f"""
                            <div class='{card_class}'>
                                <b style='color: var(--text-color); font-size: 14px;'>{p.second_name} {cap}</b><br>
                                <span style='font-size:11px; opacity:0.8;'>{p.team_name}</span><br>
                                <span style='font-size:11px; color:#ff007f;'>vs {p.next_opponent}</span><br>
                                <span style='color:#0088cc; font-weight:800; font-size:13px;'>£{p.cost_m}m | xP: {p.final_xp:.2f}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    st.write("")
                    
                render_v2_pitch(starters[starters['element_type'] == 1])
                render_v2_pitch(starters[starters['element_type'] == 2])
                render_v2_pitch(starters[starters['element_type'] == 3])
                render_v2_pitch(starters[starters['element_type'] == 4])
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("### 🪑 The Bench (Ordered by Priority)")
                render_v2_pitch(bench, card_class='bench-card')
                
                st.markdown("### 🔍 Sensitivity & Close Misses")
                st.caption("Top players with highest Final xP who barely missed the budget or team constraint thresholds:")
                
                unpicked = df[~df.index.isin(squad.index)].sort_values(by='final_xp', ascending=False).head(8)
                st.dataframe(
                    unpicked[['full_name', 'team_name', 'position', 'cost_m', 'v2_xp', 'final_xp', 'next_opponent']],
                    width="stretch", hide_index=True,
                    column_config={
                        "full_name": st.column_config.TextColumn("Player"),
                        "team_name": st.column_config.TextColumn("Club"),
                        "position": st.column_config.TextColumn("Pos"),
                        "cost_m": st.column_config.NumberColumn("Price (£M)", format="£%.1f"),
                        "v2_xp": st.column_config.NumberColumn("Poisson Base xP", format="%.2f"),
                        "final_xp": st.column_config.NumberColumn("Final Blended xP", format="%.2f", help="The final score used by the solver."),
                        "next_opponent": st.column_config.TextColumn("Fixture")
                    }
                )
            else:
                st.error("No optimal solution found for the current constraints.")

# ==========================================
# FPL MODULE 5: AI TRANSFER SUGGESTER
# ==========================================
elif app_mode == "🔄 AI Transfer Suggester":
    st.title("🔄 AI Transfer Suggester")
    st.write("Extract your actual FPL team and let the AI optimizer calculate the best mathematically sound transfers based on your live Hybrid settings.")
    
    num_transfers = st.selectbox("Number of Transfers to make:", [1, 2, 3])
    
    st.sidebar.markdown("---")
    st.sidebar.header("Bench Strategy")
    transfer_bench_weight = st.sidebar.slider("Bench Investment Weight (Transfers)", 0.0, 1.0, 0.1, 0.1)
    
    if st.button("🚀 Analyze Best Transfers", type="primary", width="stretch"):
        if user_manager_id and master_df is not None and not master_df.empty:
            curr_event = get_current_event()
            
            with st.spinner(f"Fetching live squad for Manager {user_manager_id}..."):
                try:
                    r = requests.get(f"https://fantasy.premierleague.com/api/entry/{user_manager_id}/event/{curr_event}/picks/", timeout=5).json()
                    if 'picks' in r:
                        my_elements = [p['element'] for p in r['picks']]
                        manager_bank = r['entry_history']['bank'] / 10.0
                        
                        df = master_df[(master_df['status'] == 'a') | (master_df['id'].isin(my_elements))].copy()
                        
                        current_squad_indices = df[df['id'].isin(my_elements)].index.tolist()
                        current_squad_df = df.loc[current_squad_indices]
                        
                        if len(current_squad_indices) == 15:
                            current_team_value = current_squad_df['cost_m'].sum()
                            total_available_budget = current_team_value + manager_bank
                            
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
                            
                            for t_id in df['team'].unique():
                                prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                                
                            prob += pulp.lpSum([squad_vars[i] for i in current_squad_indices]) >= (15 - num_transfers)
                            
                            prob.solve(pulp.PULP_CBC_CMD(msg=False))
                            
                            if pulp.LpStatus[prob.status] == 'Optimal':
                                new_squad_indices = [i for i in df.index if squad_vars[i].varValue == 1]
                                new_squad_df = df.loc[new_squad_indices]
                                
                                transfers_out = current_squad_df[~current_squad_df.index.isin(new_squad_indices)]
                                transfers_in = new_squad_df[~new_squad_df.index.isin(current_squad_indices)]
                                
                                st.success("✅ AI Transfer Calculation Complete!")
                                
                                cc1, cc2 = st.columns(2)
                                with cc1:
                                    st.markdown("<h3 style='color: #ff005a;'>🛑 Players Out</h3>", unsafe_allow_html=True)
                                    for _, row in transfers_out.iterrows():
                                        st.markdown(f"<div style='border-left: 4px solid #ff005a; padding-left: 10px; margin-bottom: 5px; background: rgba(255, 0, 90, 0.1); border-radius: 4px;'><b style='font-size: 16px;'>{row['second_name']}</b> <span style='font-size:12px; color:#8f9bba;'>({row['position']} - £{row['cost_m']}M)</span><br><span style='font-size:12px;'>xP: {row['final_xp']:.2f}</span></div>", unsafe_allow_html=True)
                                with cc2:
                                    st.markdown("<h3 style='color: #01fc7a;'>✅ Players In</h3>", unsafe_allow_html=True)
                                    for _, row in transfers_in.iterrows():
                                        st.markdown(f"<div style='border-left: 4px solid #01fc7a; padding-left: 10px; margin-bottom: 5px; background: rgba(1, 252, 122, 0.1); border-radius: 4px;'><b style='font-size: 16px;'>{row['second_name']}</b> <span style='font-size:12px; color:#8f9bba;'>({row['position']} - £{row['cost_m']}M)</span><br><span style='font-size:12px;'>xP: {row['final_xp']:.2f}</span></div>", unsafe_allow_html=True)
                                
                                xp_diff = sum(transfers_in['final_xp']) - sum(transfers_out['final_xp'])
                                st.markdown(f"<div style='margin-top: 20px; margin-bottom: 30px; text-align: center; padding: 15px; border: 1px solid var(--border-color); border-radius: 8px;'><b>Total Expected Points Gained:</b> <span style='color:#01fc7a; font-size: 24px; font-weight: bold;'>+{xp_diff:.2f} xP</span></div>", unsafe_allow_html=True)
                                
                                # Render the NEW full squad
                                new_starters = df.loc[[i for i in df.index if starter_vars[i].varValue == 1]].copy()
                                new_bench_raw = df.loc[[i for i in df.index if bench_vars[i].varValue == 1]].copy()
                                new_bench_gkp = new_bench_raw[new_bench_raw['element_type'] == 1]
                                new_bench_outfield = new_bench_raw[new_bench_raw['element_type'] > 1].sort_values(by='final_xp', ascending=False)
                                new_bench = pd.concat([new_bench_gkp, new_bench_outfield])
                                
                                new_captain_id = new_starters['final_xp'].idxmax()
                                
                                st.markdown("### 🏟️ New Starting XI (After Transfers)")
                                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                                
                                def render_v2_pitch(row_df, card_class='pitch-card'):
                                    if not row_df.empty:
                                        cols = st.columns(len(row_df))
                                        for col, p in zip(cols, row_df.itertuples()):
                                            cap = "<span class='badge-cap'>C</span>" if p.Index == new_captain_id and card_class == 'pitch-card' else ""
                                            is_new = "style='border-color: #01fc7a; box-shadow: 0 0 10px rgba(1,252,122,0.3);'" if p.Index in new_squad_indices and p.Index not in current_squad_indices else ""
                                            col.markdown(f"""
                                            <div class='{card_class}' {is_new}>
                                                <b style='color: var(--text-color); font-size: 14px;'>{p.second_name} {cap}</b><br>
                                                <span style='font-size:11px; opacity:0.8;'>{p.team_name}</span><br>
                                                <span style='font-size:11px; color:#ff007f;'>vs {p.next_opponent}</span><br>
                                                <span style='color:#0088cc; font-weight:800; font-size:13px;'>£{p.cost_m}m | xP: {p.final_xp:.2f}</span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                    st.write("")
                                    
                                render_v2_pitch(new_starters[new_starters['element_type'] == 1])
                                render_v2_pitch(new_starters[new_starters['element_type'] == 2])
                                render_v2_pitch(new_starters[new_starters['element_type'] == 3])
                                render_v2_pitch(new_starters[new_starters['element_type'] == 4])
                                st.markdown("</div>", unsafe_allow_html=True)
                                
                                st.markdown("### 🪑 New Bench (Ordered by Priority)")
                                render_v2_pitch(new_bench, card_class='bench-card')
                                
                            else:
                                st.error("No valid transfer sequence found. Ensure your team structure allows affordable moves.")
                        else:
                            st.error("Could not load a complete 15-man squad for this Manager ID.")
                    else:
                        st.error("Invalid Manager ID or no team selected for the current event.")
                except Exception as e:
                    st.error(f"Failed to fetch FPL API data. Please ensure the Manager ID is valid. Error: {e}")
        else:
            st.warning("Please ensure your Manager ID is entered in the sidebar.")

# ==========================================
# FPL MODULE 6: MINI-LEAGUE VIEWER
# ==========================================
elif app_mode == "🏆 Live Mini-League Standings":
    st.title("🏆 Granular Mini-League Analyzer")
    st.write("Track the live leaderboard, view weekly winners, and see monthly awards for the top 50 managers in your league.")
    
    if user_league_id:
        with st.spinner(f"Fetching historical data for League {user_league_id}... (This takes a few seconds)"):
            history_df, l_name, standings_res, completed_gws = fetch_league_history(user_league_id)
            
        if standings_res:
            st.markdown(f"### 🏅 {l_name}")
            tab1, tab2, tab3 = st.tabs(["🏆 Live Overall Standings", "📅 Gameweek Winners", "🗓️ Monthly Awards"])
            
            with tab1:
                display_cols = ['rank', 'entry_name', 'player_name', 'event_total', 'total']
                st.dataframe(
                    pd.DataFrame(standings_res)[display_cols], 
                    width="stretch", hide_index=True,
                    column_config={
                        "rank": st.column_config.NumberColumn("Rank"),
                        "entry_name": st.column_config.TextColumn("Team Name"),
                        "player_name": st.column_config.TextColumn("Manager Name"),
                        "event_total": st.column_config.NumberColumn("GW Points"),
                        "total": st.column_config.NumberColumn("Total Points")
                    }
                )
                
            with tab2:
                if not history_df.empty and completed_gws:
                    selected_gw = st.selectbox("Select Gameweek:", sorted(completed_gws, reverse=True), format_func=lambda x: f"Gameweek {x}")
                    gw_df = history_df[history_df['GW'] == selected_gw].sort_values(by='Net Points', ascending=False).reset_index(drop=True)
                    gw_df.index += 1
                    
                    if not gw_df.empty:
                        winner = gw_df.iloc[0]
                        st.success(f"👑 **Gameweek {selected_gw} Winner:** {winner['Manager']} ({winner['Team']}) with **{winner['Net Points']} net points!**")
                        st.dataframe(gw_df[['Manager', 'Team', 'Net Points']], width="stretch")
                else:
                    st.info("No completed gameweeks available yet.")
                    
            with tab3:
                if not history_df.empty:
                    available_months = history_df['Month'].unique().tolist()
                    selected_month = st.selectbox("Select Month:", available_months)
                    month_df = history_df[history_df['Month'] == selected_month]
                    
                    if not month_df.empty:
                        month_totals = month_df.groupby(['Manager', 'Team'])['Net Points'].sum().reset_index()
                        month_totals = month_totals.sort_values(by='Net Points', ascending=False).reset_index(drop=True)
                        month_totals.index += 1
                        
                        m1, m2, m3 = st.columns(3)
                        if len(month_totals) >= 1:
                            m1.markdown(f"<div style='background: rgba(255, 215, 0, 0.1); border: 2px solid gold; padding: 20px; border-radius: 10px; text-align: center;'><h1 style='margin:0;'>🥇</h1><h3 style='margin:0;'>{month_totals.iloc[0]['Manager']}</h3><p>{month_totals.iloc[0]['Team']}<br><b style='font-size:20px; color:gold;'>{month_totals.iloc[0]['Net Points']} pts</b></p></div>", unsafe_allow_html=True)
                        if len(month_totals) >= 2:
                            m2.markdown(f"<div style='background: rgba(192, 192, 192, 0.1); border: 2px solid silver; padding: 20px; border-radius: 10px; text-align: center;'><h1 style='margin:0;'>🥈</h1><h3 style='margin:0;'>{month_totals.iloc[1]['Manager']}</h3><p>{month_totals.iloc[1]['Team']}<br><b style='font-size:20px; color:silver;'>{month_totals.iloc[1]['Net Points']} pts</b></p></div>", unsafe_allow_html=True)
                        if len(month_totals) >= 3:
                            m3.markdown(f"<div style='background: rgba(205, 127, 50, 0.1); border: 2px solid #cd7f32; padding: 20px; border-radius: 10px; text-align: center;'><h1 style='margin:0;'>🥉</h1><h3 style='margin:0;'>{month_totals.iloc[2]['Manager']}</h3><p>{month_totals.iloc[2]['Team']}<br><b style='font-size:20px; color:#cd7f32;'>{month_totals.iloc[2]['Net Points']} pts</b></p></div>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.dataframe(month_totals, width="stretch")
                else:
                    st.info("No monthly data available yet.")
        else:
            st.error("Failed to load league standings. Please check the League ID.")
    else:
        st.warning("Please ensure your League ID is entered in the sidebar.")

# ==========================================
# MODULE 5: REAL EPL MATCHES & STATS
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
            selected_gw_str = st.selectbox("Select Matchweek:", [f"Gameweek {i}" for i in range(1, max_gw + 1)])
            selected_gw_num = int(selected_gw_str.split(" ")[1])
            gw_matches = szn_matches[szn_matches['gameweek'] == selected_gw_num].sort_values('date')
            
            if not gw_matches.empty:
                for _, row in gw_matches.iterrows():
                    st.markdown(f"""
                    <div class="fixture-card">
                        <div style="width: 35%; text-align: right;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-color);">{row['home_team']}</div>
                            <div style="font-size: 0.85rem; color: #0088cc;">xG: {float(row.get('home_xG', row.get('home_xg', 0.0))):.2f}</div>
                        </div>
                        <div style="width: 30%; display: flex; flex-direction: column; align-items: center;">
                            <div class="score-box">{int(row['home_goals'])} <span style='opacity:0.5'>-</span> {int(row['away_goals'])}</div>
                            <span style="font-size: 0.8rem; margin-top: 6px; color: var(--text-color); opacity: 0.7; text-transform: uppercase;">{row['date'].strftime('%d %b %Y')}</span>
                        </div>
                        <div style="width: 35%; text-align: left;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-color);">{row['away_team']}</div>
                            <div style="font-size: 0.85rem; color: #cc0066;">xG: {float(row.get('away_xG', row.get('away_xg', 0.0))):.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("No fixtures found.")
        else: st.warning("No matches found for this season.")

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
                h, a = row['home_team'], row['away_team']
                h_g, a_g = row['home_goals'], row['away_goals']
                
                team_records[h]['Matches'] += 1
                team_records[a]['Matches'] += 1
                team_records[h]['GF'] += h_g
                team_records[h]['GA'] += a_g
                team_records[h]['GD'] += (h_g - a_g)
                team_records[h]['xG'] += float(row.get('home_xG', row.get('home_xg', 0.0)))
                team_records[h]['xGA'] += float(row.get('away_xG', row.get('away_xg', 0.0)))
                team_records[h]['xPts'] += float(row.get('home_expected_points', row.get('home_xpts', 0.0)))
                
                team_records[a]['GF'] += a_g
                team_records[a]['GA'] += h_g
                team_records[a]['GD'] += (a_g - h_g)
                team_records[a]['xG'] += float(row.get('away_xG', row.get('away_xg', 0.0)))
                team_records[a]['xGA'] += float(row.get('home_xG', row.get('home_xg', 0.0)))
                team_records[a]['xPts'] += float(row.get('away_expected_points', row.get('away_xpts', 0.0)))
                
                if h_g > a_g:
                    team_records[h]['Pts'] += 3; team_records[h]['W'] += 1; team_records[a]['L'] += 1
                elif a_g > h_g:
                    team_records[a]['Pts'] += 3; team_records[a]['W'] += 1; team_records[h]['L'] += 1
                else:
                    team_records[h]['Pts'] += 1; team_records[a]['Pts'] += 1; team_records[h]['D'] += 1; team_records[a]['D'] += 1
            
            table_df = pd.DataFrame([{'Club': k, 'MP': v['Matches'], 'Pts': v['Pts'], 'xPts': v['xPts'], 'GD': v['GD'], 'GF': v['GF'], 'xG': v['xG'], 'GA': v['GA'], 'xGA': v['xGA']} for k, v in team_records.items()])
            table_df = table_df.sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
            table_df.index += 1
            
            st.dataframe(
                table_df, width="stretch",
                column_config={
                    "Pts": st.column_config.ProgressColumn("Pts", format="%d", min_value=0, max_value=int(table_df['Pts'].max())),
                    "xPts": st.column_config.NumberColumn("xPts", format="%.1f"),
                    "xG": st.column_config.NumberColumn("xG", format="%.1f"),
                    "xGA": st.column_config.NumberColumn("xGA", format="%.1f")
                }
            )

elif app_mode == "📈 Team Trends (xG vs Actual)":
    st.title("📈 Team Trends: Expected vs Actual")
    if understat_shooting_df is not None and not understat_shooting_df.empty:
        available_seasons = sorted(understat_shooting_df['season'].unique().tolist(), reverse=True)
        selected_season_raw = st.selectbox("Select Season to Analyze:", available_seasons, format_func=format_season)
        szn_df = understat_shooting_df[understat_shooting_df['season'] == selected_season_raw].sort_values('date')
        
        if not szn_df.empty:
            col1, col2 = st.columns(2)
            selected_team = col1.selectbox("Select Team:", sorted(list(set(szn_df['home_team'].tolist() + szn_df['away_team'].tolist()))))
            metric_choice = col2.selectbox("Select Metric:", ["Goals For", "Goals Against", "Points"])
            
            team_matches = szn_df[(szn_df['home_team'] == selected_team) | (szn_df['away_team'] == selected_team)].copy()
            
            if not team_matches.empty:
                actual_vals, expected_vals = [], []
                for _, row in team_matches.iterrows():
                    is_home = (row['home_team'] == selected_team)
                    h_score, a_score = row['home_goals'], row['away_goals']
                    h_xg, a_xg = float(row.get('home_xG', row.get('home_xg', 0.0))), float(row.get('away_xG', row.get('away_xg', 0.0)))
                    h_xpts, a_xpts = float(row.get('home_expected_points', row.get('home_xpts', 0.0))), float(row.get('away_expected_points', row.get('away_xpts', 0.0)))
                    
                    if metric_choice == "Goals For":
                        actual_vals.append(h_score if is_home else a_score); expected_vals.append(h_xg if is_home else a_xg)
                    elif metric_choice == "Goals Against":
                        actual_vals.append(a_score if is_home else h_score); expected_vals.append(a_xg if is_home else h_xg)
                    elif metric_choice == "Points":
                        gf, ga = (h_score, a_score) if is_home else (a_score, h_score)
                        actual_vals.append(3 if gf > ga else (1 if gf == ga else 0))
                        expected_vals.append(h_xpts if is_home else a_xpts)
                        
                trend_df = pd.DataFrame({'Gameweek': range(1, len(actual_vals) + 1), 'Actual': np.cumsum(actual_vals), 'Expected': np.cumsum(expected_vals)})
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Actual'], mode='lines+markers', name=f'Actual {metric_choice}', line=dict(color='#0088cc', width=3)))
                fig.add_trace(go.Scatter(x=trend_df['Gameweek'], y=trend_df['Expected'], mode='lines', name=f'Expected {metric_choice}', line=dict(color='#cc0066', width=3, dash='dot')))
                fig.update_layout(title=f"{selected_team} - Cumulative {metric_choice} ({format_season(selected_season_raw)})", xaxis_title="Gameweek", template=chart_theme, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)

elif app_mode == "🌐 Understat Team Stats":
    st.title("🌐 Understat Team Match Stats")
    if understat_shooting_df is not None: st.dataframe(understat_shooting_df, width="stretch")

# ==========================================
# MODULE 6: BETTING ADVISOR
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
            fact_matches['HT_Status'] = np.where(fact_matches['Scored_HT'] > fact_matches['Conceded_HT'], 'Winning', np.where(fact_matches['Scored_HT'] < fact_matches['Conceded_HT'], 'Losing', 'Drawing'))
            fact_matches['FT_Status'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 'Win', np.where(fact_matches['Scored_FT'] < fact_matches['Conceded_FT'], 'Loss', 'Draw'))
            
            tab1, tab2, tab3, tab4 = st.tabs(["🔄 Losing at HT", "🛡️ Winning at HT", "🏠 Home vs Away", "🎯 Chaos Quadrant"])
            
            with tab1:
                fig1 = px.histogram(fact_matches[fact_matches['HT_Status'] == 'Losing'], y="Team", color="FT_Status", title="Match Outcomes When Trailing at HT", color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig1, width="stretch")
            with tab2:
                fig2 = px.histogram(fact_matches[fact_matches['HT_Status'] == 'Winning'], y="Team", color="FT_Status", title="Match Outcomes When Leading at HT", color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig2, width="stretch")
            with tab3:
                ha_stats = fact_matches.groupby(['Team', 'Venue']).size().reset_index(name='Matches')
                ha_wins = fact_matches[fact_matches['FT_Status'] == 'Win'].groupby(['Team', 'Venue']).size().reset_index(name='Wins')
                ha_merged = pd.merge(ha_stats, ha_wins, on=['Team', 'Venue'], how='left').fillna(0)
                ha_merged['Win_Rate'] = (ha_merged['Wins'] / ha_merged['Matches']) * 100
                fig3 = px.bar(ha_merged, x="Team", y="Win_Rate", color="Venue", barmode="group", title="Win Rate %: Home vs Away", color_discrete_map={'Home': '#0088cc', 'Away': '#cc0066'})
                st.plotly_chart(fig3, width="stretch")
            with tab4:
                fact_matches['Pts'] = fact_matches['FT_Status'].map({'Win': 3, 'Draw': 1, 'Loss': 0})
                team_stats = fact_matches.groupby('Team').agg(Avg_Scored=('Scored_FT', 'mean'), Avg_Conceded=('Conceded_FT', 'mean'), Total_Pts=('Pts', 'sum')).reset_index()
                
                fig4 = px.scatter(team_stats, x='Avg_Conceded', y='Avg_Scored', text='Team', size='Total_Pts', size_max=25, color_discrete_sequence=['#0088cc'])
                fig4.update_traces(textposition='top center')
                
                x_mean, y_mean = team_stats['Avg_Conceded'].mean(), team_stats['Avg_Scored'].mean()
                x_min, x_max = max(0, team_stats['Avg_Conceded'].min() - 0.5), team_stats['Avg_Conceded'].max() + 0.5
                y_min, y_max = max(0, team_stats['Avg_Scored'].min() - 0.5), team_stats['Avg_Scored'].max() + 0.5
                
                fig4.add_hline(y=y_mean, line_dash="dash", line_color="#cc0066"); fig4.add_vline(x=x_mean, line_dash="dash", line_color="#cc0066")
                fig4.add_shape(type="rect", x0=x_min, x1=x_mean, y0=y_mean, y1=y_max, fillcolor="rgba(0, 136, 204, 0.1)", line_width=0, layer="below")
                fig4.add_shape(type="rect", x0=x_mean, x1=x_max, y0=y_min, y1=y_mean, fillcolor="rgba(204, 0, 102, 0.1)", line_width=0, layer="below")
                
                fig4.add_annotation(x=x_min + (x_mean-x_min)/2, y=y_max-0.1, text="🔥 Elite", showarrow=False, font=dict(color="#0088cc", size=16))
                fig4.add_annotation(x=x_max - (x_max-x_mean)/2, y=y_max-0.1, text="🎭 Entertainers", showarrow=False, font=dict(color="#8f9bba", size=14))
                fig4.add_annotation(x=x_min + (x_mean-x_min)/2, y=y_min+0.1, text="🛡️ Park the Bus", showarrow=False, font=dict(color="#8f9bba", size=14))
                fig4.add_annotation(x=x_max - (x_max-x_mean)/2, y=y_min+0.1, text="📉 Strugglers", showarrow=False, font=dict(color="#cc0066", size=14))
                
                fig4.update_layout(title="The Chaos Quadrant", xaxis_title="Avg Goals Conceded (Fewer = Better)", yaxis_title="Avg Goals Scored (More = Better)", xaxis=dict(range=[x_min, x_max]), yaxis=dict(range=[y_min, y_max]))
                st.plotly_chart(fig4, width="stretch")
