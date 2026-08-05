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
        if selected_pos != "All": filtered_df = filtered_df[filtered_df['position'] == selected_pos]
        
        # Step 3: Player Search
        player_list = sorted((filtered_df['first_name'] + " " + filtered_df['second_name']).tolist())
        
        if len(player_list) > 0:
            selected_player = st.selectbox("Select Player:", player_list)
            p_data = filtered_df[(filtered_df['first_name'] + " " + filtered_df['second_name']) == selected_player].iloc[0]
            
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
            
            # Percentile Progress Bars
            metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat (Goal Danger)': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
            col1, col2 = st.columns(2)
            for i, (label, col_name) in enumerate(metrics.items()):
                val = p_data[col_name]
                percentile = int((players_df[col_name] < val).mean() * 100)
                target_col = col1 if i < 3 else col2
                with target_col:
                    st.write(f"**{label}**: `{val}` *(Top {100-percentile}%)*")
                    st.progress(percentile / 100.0)
        else:
            st.warning("No players found with these filters.")

# ==========================================
# MODULE 2: FPL SQUAD OPTIMIZER (With Pitch)
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
            
            if len(squad) == 15:
                # --- STARTING XI vs BENCH LOGIC ---
                squad = squad.sort_values(by='custom_score', ascending=False)
                
                gkps = squad[squad['element_type'] == 1]
                defs = squad[squad['element_type'] == 2]
                mids = squad[squad['element_type'] == 3]
                fwds = squad[squad['element_type'] == 4]

                start_gkp = gkps.head(1)
                bench_gkp = gkps.tail(1)
                
                start_def = defs.head(3)
                start_mid = mids.head(2)
                start_fwd = fwds.head(1)
                
                remaining_outfield = pd.concat([defs.iloc[3:], mids.iloc[2:], fwds.iloc[1:]]).sort_values(by='custom_score', ascending=False)
                start_rest = remaining_outfield.head(4)
                bench_rest = remaining_outfield.tail(3)
                
                starters = pd.concat([start_gkp, start_def, start_mid, start_fwd, start_rest])
                bench = pd.concat([bench_gkp, bench_rest]).sort_values(by='element_type')

                # --- UI RENDERING ---
                st.success("✅ Optimization Complete!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Spent", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget - squad['cost_m'].sum():.1f}M")
                c2.metric("Starting XI Proj. Score", f"{starters['custom_score'].sum():.2f}")
                c3.metric("Bench Proj. Score", f"{bench['custom_score'].sum():.2f}")

                st.markdown("### 🏟️ The Starting XI")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                def render_row(players_in_row):
                    if not players_in_row.empty:
                        cols = st.columns(len(players_in_row))
                        for col, (_, p) in zip(cols, players_in_row.iterrows()):
                            col.markdown(f"<div class='pitch-card'><b>{p['second_name']}</b><br><span style='font-size:12px; color:#8f9bba;'>{p['team_name']}</span><br><span style='color:#00f2fe;'>£{p['cost_m']}m</span></div>", unsafe_allow_html=True)
                    st.write("") # Spacing

                render_row(starters[starters['element_type'] == 1]) # GK
                render_row(starters[starters['element_type'] == 2]) # DEF
                render_row(starters[starters['element_type'] == 3]) # MID
                render_row(starters[starters['element_type'] == 4]) # FWD
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("### 🪑 The Bench")
                b_cols = st.columns(4)
                for col, (_, p) in zip(b_cols, bench.iterrows()):
                    col.markdown(f"<div class='bench-card'><b>{p['second_name']}</b> ({p['position']})<br>£{p['cost_m']}m</div>", unsafe_allow_html=True)

            else:
                st.error("⚠️ Budget too tight to field 15 players. Adjust constraints.")

# ==========================================
# MODULE 3: TEAM BETTING EDGE (Expanded)
# ==========================================
elif app_mode == "📈 Team Betting Edge":
    st.title("📈 Predictive Match Analytics")
    
    if match_df is not None and not match_df.empty:
        # Restructure Data
        home_m = match_df[['Match_ID', 'Home_Team', 'Home_Score_HT', 'Away_Score_HT', 'Home_Score_FT', 'Away_Score_FT']].copy()
        home_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
        home_m['Venue'] = 'Home'
        
        # CORRECTED LINE BELOW (This is what caused the NameError crash!)
        away_m = match_df[['Match_ID', 'Away_Team', 'Away_Score_HT', 'Home_Score_HT', 'Away_Score_FT', 'Home_Score_FT']].copy()
        away_m.columns = ['Match_ID', 'Team', 'Scored_HT', 'Conceded_HT', 'Scored_FT', 'Conceded_FT']
        away_m['Venue'] = 'Away'
        
        fact_matches = pd.concat([home_m, away_m], ignore_index=True)
        fact_matches['HT_Status'] = np.where(fact_matches['Scored_HT'] > fact_matches['Conceded_HT'], 'Winning',
                                     np.where(fact_matches['Scored_HT'] < fact_matches['Conceded_HT'], 'Losing', 'Drawing'))
        fact_matches['FT_Status'] = np.where(fact_matches['Scored_FT'] > fact_matches['Conceded_FT'], 'Win',
                                     np.where(fact_matches['Scored_FT'] < fact_matches['Conceded_FT'], 'Loss', 'Draw'))
        
        tab1, tab2, tab3, tab4 = st.tabs(["🔄 Losing at HT", "🛡️ Winning at HT", "🏠 Home vs Away", "🎯 Chaos Quadrant"])
        
        # TAB 1: LOSING
        with tab1:
            losing_ht = fact_matches[fact_matches['HT_Status'] == 'Losing']
            fig1 = px.histogram(losing_ht, y="Team", color="FT_Status", title="Match Outcomes When Trailing at HT",
                                color_discrete_map={'Win': '#00f2fe', 'Draw': '#8f9bba', 'Loss': '#ff007f'}, orientation='h')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed')
            st.plotly_chart(fig1, use_container_width=True)
            
        # TAB 2: WINNING
        with tab2:
            winning_ht = fact_matches[fact_matches['HT_Status'] == 'Winning']
            fig2 = px.histogram(winning_ht, y="Team", color="FT_Status", title="Match Outcomes When Leading at HT (Bottle Jobs?)",
                                color_discrete_map={'Win': '#00f2fe', 'Draw': '#8f9bba', 'Loss': '#ff007f'}, orientation='h')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed')
            st.plotly_chart(fig2, use_container_width=True)
            
        # TAB 3: HOME VS AWAY
        with tab3:
            ha_stats = fact_matches.groupby(['Team', 'Venue']).size().reset_index(name='Matches')
            ha_wins = fact_matches[fact_matches['FT_Status'] == 'Win'].groupby(['Team', 'Venue']).size().reset_index(name='Wins')
            ha_merged = pd.merge(ha_stats, ha_wins, on=['Team', 'Venue'], how='left').fillna(0)
            ha_merged['Win_Rate'] = (ha_merged['Wins'] / ha_merged['Matches']) * 100
            
            fig3 = px.bar(ha_merged, x="Team", y="Win_Rate", color="Venue", barmode="group", title="Win Rate %: Home vs Away Fortress",
                          color_discrete_map={'Home': '#00f2fe', 'Away': '#ff007f'})
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed')
            st.plotly_chart(fig3, use_container_width=True)

        # TAB 4: CHAOS QUADRANT
        with tab4:
            team_stats = fact_matches.groupby('Team').agg(Avg_Scored=('Scored_FT', 'mean'), Avg_Conceded=('Conceded_FT', 'mean')).reset_index()
            fig4 = px.scatter(team_stats, x='Avg_Scored', y='Avg_Conceded', text='Team', color_discrete_sequence=['#00f2fe'])
            fig4.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=2, color='DarkSlateGrey')))
            fig4.add_hline(y=team_stats['Avg_Conceded'].mean(), line_dash="dash", line_color="#ff007f", annotation_text="Avg Conceded")
            fig4.add_vline(x=team_stats['Avg_Scored'].mean(), line_dash="dash", line_color="#ff007f", annotation_text="Avg Scored")
            fig4.update_layout(title="The Chaos Quadrant (Offense vs Defense)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e6ed')
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.warning("Match dataset is currently loading or unavailable. Check the raw GitHub CSV link.")

# ==========================================
# MODULE 4: LIVE LEAGUE TABLE (New)
# ==========================================
elif app_mode == "📊 Live League Table":
    st.title("📊 League Table & Performance Form")
    
    if match_df is not None and not match_df.empty:
        latest_season = match_df['Season'].max()
        st.write(f"Displaying aggregated data for the **{latest_season}** season.")
        
        szn_df = match_df[match_df['Season'] == latest_season]
        
        records = []
        teams = pd.concat([szn_df['Home_Team'], szn_df['Away_Team']]).unique()
        
        for team in teams:
            h_matches = szn_df[szn_df['Home_Team'] == team]
            a_matches = szn_df[szn_df['Away_Team'] == team]
            
            w = len(h_matches[h_matches['Home_Score_FT'] > h_matches['Away_Score_FT']]) + len(a_matches[a_matches['Away_Score_FT'] > a_matches['Home_Score_FT']])
            d = len(h_matches[h_matches['Home_Score_FT'] == h_matches['Away_Score_FT']]) + len(a_matches[a_matches['Away_Score_FT'] == a_matches['Home_Score_FT']])
            l = len(h_matches[h_matches['Home_Score_FT'] < h_matches['Away_Score_FT']]) + len(a_matches[a_matches['Away_Score_FT'] < a_matches['Home_Score_FT']])
            
            gf = h_matches['Home_Score_FT'].sum() + a_matches['Away_Score_FT'].sum()
            ga = h_matches['Away_Score_FT'].sum() + a_matches['Home_Score_FT'].sum()
            gd = gf - ga
            pts = (w * 3) + (d * 1)
            
            records.append({'Club': team, 'MP': w+d+l, 'W': w, 'D': d, 'L': l, 'GF': gf, 'GA': ga, 'GD': gd, 'Pts': pts})
            
        table = pd.DataFrame(records).sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
        table.index += 1
        
        st.dataframe(table, use_container_width=True)
    else:
        st.warning("Match dataset is currently loading or unavailable.")
