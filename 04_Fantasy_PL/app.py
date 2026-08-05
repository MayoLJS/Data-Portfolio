import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px

# ==========================================
# 1. PAGE CONFIG & CUSTOM SCOUT LAB CSS
# ==========================================
st.set_page_config(page_title="FPL Squad Architect & Scout", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp { background-color: #0b0e14; color: #e0e6ed; }
    section[data-testid="stSidebar"] { background-color: #121621; border-right: 1px solid #1e2638; }
    
    /* Custom Card Containers */
    .scout-card { background-color: #161b26; border: 1px solid #232b3e; border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    
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
    """Fetches live FPL player metrics from the official API."""
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
    """Reads rolling 3-year match results dataset from GitHub."""
    # Ensure this URL matches your actual raw GitHub link to the CSV
    raw_url = "https://raw.githubusercontent.com/MayoLJS/Data-Portfolio/refs/heads/main/02_Automated_Football_Analytics/data/pl_rolling_3_years_latest.csv"
    try:
        df = pd.read_csv(raw_url)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("⚽ SCOUT LAB PRO")
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("Select Module:", ["👤 Player Scout Card", "⚡ FPL Squad Optimizer", "📈 Team Betting Edge"])

players_df = load_fpl_data()
match_df = load_match_data()

# ==========================================
# MODULE 1: PLAYER SCOUT CARD
# ==========================================
if app_mode == "👤 Player Scout Card":
    st.title("👤 Player Performance Profile")
    
    if players_df is not None and not players_df.empty:
        player_list = (players_df['first_name'] + " " + players_df['second_name']).tolist()
        selected_player = st.selectbox("Search Player:", sorted(player_list), index=player_list.index("Erling Haaland") if "Erling Haaland" in player_list else 0)
        
        p_data = players_df[(players_df['first_name'] + " " + players_df['second_name']) == selected_player].iloc[0]
        
        # Scout Banner
        st.markdown(f"""
        <div class="scout-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span class="badge-cyan">{p_data['position'].upper()}</span>
                    <span class="badge-pink">{p_data['team_name']}</span>
                    <h1 style="color: white; margin: 10px 0 0 0;">{p_data['first_name']} {p_data['second_name']}</h1>
                    <p style="color: #8f9bba; margin: 0;">Price: £{p_data['cost_m']}M | Ownership: {p_data['selected_by_percent']}% | Points: {int(p_data['total_points'])}</p>
                </div>
                <div style="text-align: right;">
                    <h2 style="color: #00f2fe; margin:0;">ICT: {p_data['ict_index']}</h2>
                    <p style="color: #8f9bba; margin:0;">Form: {p_data['form']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat (Goal Danger)': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
        
        col1, col2 = st.columns(2)
        for i, (label, col_name) in enumerate(metrics.items()):
            val = p_data[col_name]
            percentile = int((players_df[col_name] < val).mean() * 100)
            
            target_col = col1 if i < 3 else col2
            with target_col:
                st.write(f"**{label}**: `{val}` *(Top {100-percentile}%)*")
                st.progress(percentile / 100.0)

# ==========================================
# MODULE 2: FPL SQUAD OPTIMIZER
# ==========================================
elif app_mode == "⚡ FPL Squad Optimizer":
    st.title("⚡ Prescriptive FPL Squad Optimizer")
    
    st.sidebar.header("1. Budget Constraints")
    budget = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.header("2. Custom Strategy Weights")
    w_form = st.sidebar.slider("Form (Short-Term)", 0, 100, 20, 5)
    w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
    w_ict = st.sidebar.slider("ICT Index (Quality)", 0, 100, 40, 5)
    
    weights = {'form': w_form, 'selected_by_percent': w_own, 'ict_index': w_ict}
    total_w = sum(weights.values())
    if total_w > 0: weights = {k: v / total_w for k, v in weights.items()}

    if st.button("🚀 Generate Optimal Squad", type="primary", use_container_width=True):
        if players_df is not None:
            df = players_df.copy()
            for metric in weights.keys():
                min_v, max_v = df[metric].min(), df[metric].max()
                df[f'{metric}_norm'] = (df[metric] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
            
            df['custom_score'] = sum(df[f'{metric}_norm'] * w for metric, w in weights.items())
                
            prob = pulp.LpProblem("Optimal_FPL_Squad", pulp.LpMaximize)
            player_vars = pulp.LpVariable.dicts("player", df.index, cat='Binary')
            
            prob += pulp.lpSum([df.loc[i, 'custom_score'] * player_vars[i] for i in df.index])
            prob += pulp.lpSum([df.loc[i, 'now_cost'] * player_vars[i] for i in df.index]) <= (budget * 10) 
            prob += pulp.lpSum([player_vars[i] for i in df.index]) == 15 
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3
            
            for t_id in df['team'].unique(): prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            squad = df.loc[[i for i in df.index if player_vars[i].varValue == 1]].copy()
            squad = squad.sort_values(by=['element_type', 'cost_m'], ascending=[True, False])
            
            if len(squad) == 15:
                st.success("✅ Optimization Complete!")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Spent", f"£{squad['cost_m'].sum():.1f}M")
                c2.metric("Remaining Bank", f"£{budget - squad['cost_m'].sum():.1f}M")
                c3.metric("Avg Squad Form", f"{squad['form'].mean():.2f}")
                c4.metric("Avg Ownership", f"{squad['selected_by_percent'].mean():.1f}%")
                
                display_df = squad[['position', 'first_name', 'second_name', 'team_name', 'cost_m', 'form', 'selected_by_percent', 'custom_score']].copy()
                display_df['custom_score'] = display_df['custom_score'].round(4)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.error("⚠️ Budget too tight to field 15 players.")

# ==========================================
# MODULE 3: TEAM BETTING EDGE (Plotly)
# ==========================================
elif app_mode == "📈 Team Betting Edge":
    st.title("📈 Predictive Match Analytics")
    st.write("Analyzing 3-year rolling match data for betting patterns and tactical setups.")
    
    if match_df is not None and not match_df.empty:
        # Transform data to Team level (Home + Away perspectives)
        home_m = match_df[['Match_ID', 'Home_Team', 'Home_Score_HT', 'Away_Score_HT', 'Home_Score_FT', 'Away_Score_FT']].copy()
        home_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
        
        away_m = match_df[['Match_ID', 'Away_Team', 'Away_Score_HT', 'Home_Score_HT', 'Away_Score_FT', 'Home_Score_FT']].copy()
        away_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
        
        fact_matches = pd.concat([home_m, away_m], ignore_index=True)
        
        fact_matches['HT_Status'] = np.where(fact_matches['Scored_HT'] > fact_matches['Conceded_HT'], 'Winning',
                                     np.where(fact_matches['Scored_HT'] < fact_matches['Conceded_HT'], 'Losing', 'Drawing'))
        fact_matches['FT_Status'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 'Win',
                                     np.where(fact_matches['Scored_FT'] < fact_matches['Conceded_FT'], 'Loss', 'Draw'))
        
        tab1, tab2 = st.tabs(["🔄 HT/FT Turnaround Kings", "🎯 The Chaos Quadrant"])
        
        with tab1:
            st.subheader("Match Outcomes When Trailing at Halftime")
            losing_ht = fact_matches[fact_matches['HT_Status'] == 'Losing']
            
            # Plotly styling to match your dark/cyan/magenta screenshot
            fig1 = px.histogram(losing_ht, y="Team", color="FT_Status", 
                                color_discrete_map={'Win': '#00f2fe', 'Draw': '#8f9bba', 'Loss': '#ff007f'},
                                orientation='h', height=600)
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, 
                               paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed')
            st.plotly_chart(fig1, use_container_width=True)
            
        with tab2:
            st.subheader("Offensive vs Defensive Style (Avg Goals Per Match)")
            team_stats = fact_matches.groupby('Team').agg(Avg_Scored=('Scored_FT', 'mean'), Avg_Conceded=('Conceded_FT', 'mean')).reset_index()
            
            fig2 = px.scatter(team_stats, x='Avg_Scored', y='Avg_Conceded', text='Team', color_discrete_sequence=['#00f2fe'], height=600)
            fig2.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=2, color='DarkSlateGrey')))
            fig2.add_hline(y=team_stats['Avg_Conceded'].mean(), line_dash="dash", line_color="#ff007f", annotation_text="League Avg Conceded")
            fig2.add_vline(x=team_stats['Avg_Scored'].mean(), line_dash="dash", line_color="#ff007f", annotation_text="League Avg Scored")
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed',
                               xaxis_title="Average Goals Scored", yaxis_title="Average Goals Conceded")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Match dataset is currently loading or unavailable. Check the raw GitHub CSV link.")
