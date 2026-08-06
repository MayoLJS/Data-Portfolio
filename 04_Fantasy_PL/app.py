import streamlit as st
import pandas as pd
import numpy as np
import requests
import pulp
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (LIGHT/DARK COMPATIBLE)
# ==========================================
st.set_page_config(page_title="EPL Hub", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

# We use CSS variables here so it dynamically adapts to Streamlit's native Light/Dark toggle
st.markdown("""
<style>
    /* Custom Card Containers */
    .scout-card { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    .pitch-card { background-color: var(--secondary-background-color); border: 1px solid #00f2fe; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; }
    .bench-card { background-color: var(--background-color); border: 1px solid #ff007f; border-radius: 8px; padding: 10px; text-align: center; opacity: 0.9; position: relative;}
    .fixture-card { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    
    /* Pitch Background */
    .pitch-container { background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%); border-radius: 15px; padding: 20px; border: 2px solid #4caf50; color: white; margin-bottom: 20px;}
    
    /* Badges */
    .badge-cyan { background-color: rgba(0, 242, 254, 0.15); color: #0088cc; border: 1px solid #00f2fe; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .badge-pink { background-color: rgba(255, 0, 127, 0.15); color: #cc0066; border: 1px solid #ff007f; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .score-box { background-color: var(--background-color); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px 14px; font-size: 18px; font-weight: bold; letter-spacing: 2px; }
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
                        <h3 style="color: #0088cc; margin:0;">Expected Goals (xG): {p_data.get('expected_goals', 0.0):.2f}</h3>
                        <h3 style="color: #0088cc; margin:0;">Expected Assists (xA): {p_data.get('expected_assists', 0.0):.2f}</h3>
                        <p style="margin:0;">Form: {p_data['form']} | ICT: {p_data['ict_index']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            metrics = {'Form': 'form', 'ICT Index': 'ict_index', 'Threat (Goal Danger)': 'threat', 'Creativity': 'creativity', 'Influence': 'influence', 'Bonus Points (BPS)': 'bps'}
            col1, col2 = st.columns(2)
            for i, (label, col_name) in enumerate(metrics.items()):
                if col_name in players_df.columns:
                    val = p_data[col_name]
                    percentile = int((players_df[col_name] < val).mean() * 100)
                    target_col = col1 if i < 3 else col2
                    with target_col:
                        st.write(f"**{label}**: `{val}` *(Top {100-percentile}%)*")
                        st.progress(percentile / 100.0)
            
            st.markdown("---")
            st.markdown("### 🏆 Top Performers by Metric")
            st.write(f"Showing the best **{selected_pos if selected_pos != 'All' else 'Players'}** from **{selected_team if selected_team != 'All' else 'All Teams'}**.")
            
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            
            def display_top_5(df, metric_col, title, col):
                top_5 = df.sort_values(by=metric_col, ascending=False).head(5)
                with col:
                    st.markdown(f"**{title}**")
                    for _, row in top_5.iterrows():
                        st.markdown(f"<div style='font-size:14px; padding: 4px 0; border-bottom: 1px solid var(--border-color);'><b>{row['first_name']} {row['second_name']}</b><br><span style='color:#0088cc; font-weight:bold;'>{row[metric_col]}</span> <span style='font-size:11px;'>({row['team_name']} - {row['position']})</span></div>", unsafe_allow_html=True)
                        
            display_top_5(filtered_df, 'threat', '🔥 Highest Threat', m_c1)
            display_top_5(filtered_df, 'creativity', '✨ Most Creative', m_c2)
            display_top_5(filtered_df, 'influence', '💪 Most Influential', m_c3)
            display_top_5(filtered_df, 'ict_index', '⭐ Overall ICT', m_c4)
            
            st.markdown("---")
            st.markdown("### 🔍 Interactive Player Database")
            grid_cols = ['first_name', 'second_name', 'team_name', 'position', 'cost_m', 'total_points', 'expected_goals', 'expected_assists', 'ict_index']
            available_cols = [c for c in grid_cols if c in filtered_df.columns]
            
            # THE FIX: Removed width=None entirely, restoring use_container_width=True to fix the invalid width crash
            st.dataframe(filtered_df[available_cols], use_container_width=True, hide_index=True)

        else:
            st.warning("No players found with these filters.")

# ==========================================
# MODULE 2: FPL SQUAD OPTIMIZER (WITH FORMATIONS)
# ==========================================
elif app_mode == "⚡ FPL Squad Optimizer":
    st.title("⚡ Prescriptive FPL Squad Optimizer")
    
    st.sidebar.header("1. Budget Constraints")
    budget = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.header("2. Bench Strategy")
    bench_weight = st.sidebar.slider("Bench Investment Weight", 0.0, 1.0, 0.1, 0.1, help="0.1 = Dump cheapest fodder on bench to maximize Starting XI. 1.0 = Spread budget equally (Bench Boost).")
    
    # NEW FEATURE: Preferred Formation
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

    # Using width="stretch" to comply with future Streamlit updates for buttons
    if st.button("🚀 Generate Optimal Squad", type="primary", use_container_width=True):
        if players_df is not None:
            df = players_df.copy()
            df['full_name'] = df['first_name'] + " " + df['second_name']
            
            for metric in weights.keys():
                min_v, max_v = df[metric].min(), df[metric].max()
                df[f'{metric}_norm'] = (df[metric] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
            
            df['custom_score'] = sum(df[f'{metric}_norm'] * w for metric, w in weights.items())
                
            # Advanced LP Formulation: Starters vs Bench
            prob = pulp.LpProblem("Optimal_FPL_Squad", pulp.LpMaximize)
            squad_vars = pulp.LpVariable.dicts("squad", df.index, cat='Binary')
            starter_vars = pulp.LpVariable.dicts("starter", df.index, cat='Binary')
            bench_vars = pulp.LpVariable.dicts("bench", df.index, cat='Binary')
            
            # Objective: Maximize Starters + (Bench * Weight)
            prob += pulp.lpSum([df.loc[i, 'custom_score'] * starter_vars[i] + bench_weight * df.loc[i, 'custom_score'] * bench_vars[i] for i in df.index])
            
            for i in df.index:
                prob += squad_vars[i] == starter_vars[i] + bench_vars[i]
            
            prob += pulp.lpSum([df.loc[i, 'now_cost'] * squad_vars[i] for i in df.index]) <= (budget * 10) 
            prob += pulp.lpSum([squad_vars[i] for i in df.index]) == 15 
            prob += pulp.lpSum([starter_vars[i] for i in df.index]) == 11 
            prob += pulp.lpSum([bench_vars[i] for i in df.index]) == 4 
            
            # Global Squad Position constraints
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5
            prob += pulp.lpSum([squad_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3
            
            # Starting XI Formation Logic
            prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 1
            
            if target_formation == "Auto (Best Points)":
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) >= 3
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) >= 2
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) >= 1
            else:
                # Parse exact positions requested (e.g. 3-4-3)
                def_req, mid_req, fwd_req = map(int, target_formation.split('-'))
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == def_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == mid_req
                prob += pulp.lpSum([starter_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == fwd_req
            
            # Team Limitations
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
                
                # Sort bench: GK first, then outfield by highest score to lowest
                bench_gkp = bench_raw[bench_raw['element_type'] == 1]
                bench_outfield = bench_raw[bench_raw['element_type'] > 1].sort_values(by='custom_score', ascending=False)
                bench = pd.concat([bench_gkp, bench_outfield])

                st.success("✅ Optimization Complete!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Spent", f"£{squad['cost_m'].sum():.1f}M", f"Bank: £{budget - squad['cost_m'].sum():.1f}M")
                c2.metric("Starting XI Proj. Score", f"{starters['custom_score'].sum():.2f}")
                c3.metric("Bench Proj. Score", f"{bench['custom_score'].sum():.2f}")

                st.markdown("### 🏟️ The Starting XI (with FDR)")
                st.caption("Dots indicate overall team strength: Green = Easy, Grey = Avg, Red = Hard")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                # Inline HTML styling for FDR Badges ensures they render correctly regardless of cloud CSS stripping
                def get_fdr_style(val):
                    bg = {2: "#01fc7a", 3: "#e7e7e7", 4: "#ff005a", 5: "#80002d"}.get(val, "#e7e7e7")
                    txt = "black" if val in [2, 3] else "white"
                    return f"background-color: {bg}; color: {txt};"

                def render_row(players_in_row, card_class='pitch-card'):
                    if not players_in_row.empty:
                        cols = st.columns(len(players_in_row))
                        for col, row_data in zip(cols, players_in_row.itertuples()):
                            strength_val = int(row_data.team_strength) if pd.notna(row_data.team_strength) else 3
                            inline_fdr = get_fdr_style(strength_val)
                            
                            col.markdown(f"""
                            <div class='{card_class}'>
                                <div style='position: absolute; top: -8px; right: -8px; padding: 4px 8px; border-radius: 50%; font-size: 11px; font-weight: bold; border: 1px solid var(--border-color); z-index: 10; {inline_fdr}'>
                                    {strength_val}
                                </div>
                                <b>{row_data.second_name}</b><br>
                                <span style='font-size:12px;'>{row_data.team_name}</span><br>
                                <span style='color:#0088cc; font-weight:bold;'>£{row_data.cost_m}m</span>
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
# MODULE 3: TEAM BETTING EDGE
# ==========================================
elif app_mode == "📈 Team Betting Edge":
    st.title("📈 Predictive Match Analytics")
    
    if match_df is not None and not match_df.empty:
        available_seasons = sorted(match_df['Season'].unique().tolist(), reverse=True)
        selected_season = st.selectbox("Select Season to Analyze:", available_seasons)
        
        szn_match_df = match_df[match_df['Season'] == selected_season]
        
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
                fig1 = px.histogram(losing_ht, y="Team", color="FT_Status", title=f"Match Outcomes When Trailing at HT ({selected_season})",
                                    color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig1, use_container_width=True)
                
            with tab2:
                winning_ht = fact_matches[fact_matches['HT_Status'] == 'Winning']
                fig2 = px.histogram(winning_ht, y="Team", color="FT_Status", title=f"Match Outcomes When Leading at HT ({selected_season})",
                                    color_discrete_map={'Win': '#0088cc', 'Draw': '#8f9bba', 'Loss': '#cc0066'}, orientation='h')
                fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig2, use_container_width=True)
                
            with tab3:
                ha_stats = fact_matches.groupby(['Team', 'Venue']).size().reset_index(name='Matches')
                ha_wins = fact_matches[fact_matches['FT_Status'] == 'Win'].groupby(['Team', 'Venue']).size().reset_index(name='Wins')
                ha_merged = pd.merge(ha_stats, ha_wins, on=['Team', 'Venue'], how='left').fillna(0)
                ha_merged['Win_Rate'] = (ha_merged['Wins'] / ha_merged['Matches']) * 100
                
                fig3 = px.bar(ha_merged, x="Team", y="Win_Rate", color="Venue", barmode="group", title=f"Win Rate %: Home vs Away ({selected_season})",
                              color_discrete_map={'Home': '#0088cc', 'Away': '#cc0066'})
                fig3.update_layout(template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig3, use_container_width=True)

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
                
                fig4.update_layout(title=f"The Chaos Quadrant ({selected_season}) - Bubble Size = Total Points", 
                                   xaxis_title="Average Goals Conceded (Fewer is Better)",
                                   yaxis_title="Average Goals Scored (More is Better)",
                                   xaxis=dict(range=[x_min, x_max]),
                                   yaxis=dict(range=[y_min, y_max]),
                                   template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("No matches found for this season/filter.")
    else:
        st.warning("Match dataset is currently loading or unavailable.")

# ==========================================
# MODULE 4: MATCH RESULTS & FIXTURES
# ==========================================
elif app_mode == "📅 Match Results & Fixtures":
    st.title("📅 Match Results & Fixtures")
    st.write("Browse actual match scores and results across Premier League seasons, grouped by Gameweek.")
    
    if match_df is not None and not match_df.empty:
        available_seasons = sorted(match_df['Season'].unique().tolist(), reverse=True)
        selected_season = st.selectbox("Select Season:", available_seasons)
        
        szn_matches = match_df[match_df['Season'] == selected_season].copy()
        
        if not szn_matches.empty:
            max_gw = int(szn_matches['Gameweek'].max())
            gw_list = [f"Gameweek {i}" for i in range(1, max_gw + 1)]
            
            selected_gw_str = st.selectbox("Select Matchweek:", gw_list)
            selected_gw_num = int(selected_gw_str.split(" ")[1])
            
            gw_matches = szn_matches[szn_matches['Gameweek'] == selected_gw_num].sort_values('Date')
            
            st.markdown(f"### 🗓️ {selected_season} - {selected_gw_str}")
            st.markdown("---")
            
            if not gw_matches.empty:
                for _, row in gw_matches.iterrows():
                    match_date = row['Date'].strftime('%d %b %Y')
                    h_team = row['Home_Team']
                    a_team = row['Away_Team']
                    h_score = int(row['Home_Score_FT'])
                    a_score = int(row['Away_Score_FT'])
                    
                    st.markdown(f"""
                    <div class="fixture-card">
                        <div style="width: 35%; text-align: right; font-size: 16px; font-weight: bold;">{h_team}</div>
                        <div style="width: 30%; display: flex; flex-direction: column; align-items: center;">
                            <div class="score-box">{h_score} - {a_score}</div>
                            <span style="font-size: 11px; margin-top: 4px;">{match_date}</span>
                        </div>
                        <div style="width: 35%; text-align: left; font-size: 16px; font-weight: bold;">{a_team}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No fixtures found for this gameweek.")
        else:
            st.warning("No matches found for this season.")
    else:
        st.warning("Match dataset is currently loading or unavailable.")

# ==========================================
# MODULE 5: LIVE LEAGUE TABLE
# ==========================================
elif app_mode == "📊 Live League Table":
    st.title("📊 League Table & Gameweek Trends")
    
    if match_df is not None and not match_df.empty:
        available_seasons = ["All Seasons"] + sorted(match_df['Season'].unique().tolist(), reverse=True)
        selected_season = st.selectbox("Select Season to Analyze:", available_seasons)
        
        if selected_season == "All Seasons":
            szn_df = match_df.copy().sort_values('Date')
            st.info("Aggregating cumulative 3-year points and form data.")
        else:
            szn_df = match_df[match_df['Season'] == selected_season].sort_values('Date')
        
        if not szn_df.empty:
            teams = pd.concat([szn_df['Home_Team'], szn_df['Away_Team']]).unique()
            team_records = {team: {'W': 0, 'D': 0, 'L': 0, 'Pts': 0, 'GD': 0, 'GF': 0, 'GA': 0, 'Matches': 0} for team in teams}
            trend_data = []

            for _, row in szn_df.iterrows():
                home = row['Home_Team']
                away = row['Away_Team']
                h_score = row['Home_Score_FT']
                a_score = row['Away_Score_FT']
                
                team_records[home]['Matches'] += 1
                team_records[away]['Matches'] += 1
                
                team_records[home]['GF'] += h_score
                team_records[home]['GA'] += a_score
                team_records[home]['GD'] += (h_score - a_score)
                
                team_records[away]['GF'] += a_score
                team_records[away]['GA'] += h_score
                team_records[away]['GD'] += (a_score - h_score)
                
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
                    
                trend_data.append({'Team': home, 'Match_Num': team_records[home]['Matches'], 'Pts': team_records[home]['Pts'], 'GD': team_records[home]['GD'], 'GF': team_records[home]['GF']})
                trend_data.append({'Team': away, 'Match_Num': team_records[away]['Matches'], 'Pts': team_records[away]['Pts'], 'GD': team_records[away]['GD'], 'GF': team_records[away]['GF']})
            
            t1, t2 = st.tabs(["📋 League Table", "📈 Position Trend Line"])

            with t1:
                final_table = []
                for team, stats in team_records.items():
                    final_table.append({'Club': team, 'MP': stats['Matches'], 'W': stats['W'], 'D': stats['D'], 'L': stats['L'], 'GF': stats['GF'], 'GA': stats['GA'], 'GD': stats['GD'], 'Pts': stats['Pts']})
                
                table_df = pd.DataFrame(final_table).sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
                table_df.index += 1
                st.dataframe(table_df, use_container_width=True)
            
            with t2:
                trend_df = pd.DataFrame(trend_data)
                trend_df = trend_df.sort_values(by=['Match_Num', 'Pts', 'GD', 'GF'], ascending=[True, False, False, False])
                trend_df['Position'] = trend_df.groupby('Match_Num').cumcount() + 1
                
                all_teams = sorted(trend_df['Team'].unique().tolist())
                selected_teams = st.multiselect("Select Teams to Compare (Click 'X' to clear):", all_teams, default=all_teams)
                
                if selected_teams:
                    filtered_trend_df = trend_df[trend_df['Team'].isin(selected_teams)]
                    fig_trend = px.line(filtered_trend_df, x="Match_Num", y="Position", color="Team", 
                                        title=f"Gameweek by Gameweek League Position ({selected_season})",
                                        height=600)
                    
                    fig_trend.update_yaxes(autorange="reversed", title="League Position", tickmode='linear', tick0=1, dtick=1)
                    fig_trend.update_xaxes(title="Matches Played")
                    fig_trend.update_layout(template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("Please select at least one team to display the trend line.")

        else:
            st.warning("No matches found for this filter.")
    else:
        st.warning("Match dataset is currently loading or unavailable.")
