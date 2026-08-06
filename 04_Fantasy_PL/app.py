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

st.markdown("""
<style>
    .scout-card { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    .pitch-card { background-color: var(--secondary-background-color); border: 1px solid #00f2fe; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; }
    .bench-card { background-color: var(--background-color); border: 1px solid #ff007f; border-radius: 8px; padding: 10px; text-align: center; opacity: 0.8;}
    .pitch-container { background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%); border-radius: 15px; padding: 20px; border: 2px solid #4caf50; color: white; }
    .badge-cyan { background-color: rgba(0, 242, 254, 0.15); color: #0088cc; border: 1px solid #00f2fe; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .badge-pink { background-color: rgba(255, 0, 127, 0.15); color: #cc0066; border: 1px solid #ff007f; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    
    /* FDR Badges */
    .fdr-badge { position: absolute; top: -5px; right: -5px; padding: 4px 6px; border-radius: 50%; font-size: 10px; font-weight: bold; color: white; border: 1px solid white;}
    .fdr-2 { background-color: #01fc7a; color: black; } /* Easy */
    .fdr-3 { background-color: #e7e7e7; color: black; } /* Medium */
    .fdr-4 { background-color: #ff005a; } /* Hard */
    .fdr-5 { background-color: #80002d; } /* Very Hard */
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
    players['team_strength'] = players['team'].map(dict(zip(teams['id'], teams['strength'])))
    
    # Adding xG and xA from official FPL Data
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index', 'expected_goals', 'expected_assists', 'expected_goal_involvements']
    
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
                        <h3 style="margin:0;">Expected Goals (xG): {p_data.get('expected_goals', 0.0):.2f}</h3>
                        <h3 style="margin:0;">Expected Assists (xA): {p_data.get('expected_assists', 0.0):.2f}</h3>
                        <p style="margin:0;">Form: {p_data['form']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🔍 Interactive Player Database")
            grid_cols = ['first_name', 'second_name', 'team_name', 'position', 'cost_m', 'total_points', 'expected_goals', 'expected_assists']
            
            available_cols = [c for c in grid_cols if c in filtered_df.columns]
            gb = GridOptionsBuilder.from_dataframe(filtered_df[available_cols])
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_default_column(editable=True, groupable=True, value=True, enableRowGroup=True)
            gridOptions = gb.build()
            
            AgGrid(filtered_df[available_cols], gridOptions=gridOptions, enable_enterprise_modules=False, height=400, fit_columns_on_grid_load=True)

        else:
            st.warning("No players found with these filters.")

# ==========================================
# MODULE 2: FPL SQUAD OPTIMIZER (WITH VISUAL FDR)
# ==========================================
elif app_mode == "⚡ FPL Squad Optimizer":
    st.title("⚡ Prescriptive FPL Squad Optimizer")
    
    st.sidebar.header("1. Budget Constraints")
    budget = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.info("💡 Optimizer uses a blend of Form, Ownership, and ICT Index.")
    weights = {'form': 0.3, 'selected_by_percent': 0.3, 'ict_index': 0.4}

    if st.button("🚀 Generate Optimal Squad", type="primary", use_container_width=True):
        if players_df is not None:
            df = players_df.copy()
            df['full_name'] = df['first_name'] + " " + df['second_name']
            
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
            
            for t_id in df['team'].unique(): 
                prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            squad = df.loc[[i for i in df.index if player_vars[i].varValue == 1]].copy()
            
            if len(squad) == 15:
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

                st.success("✅ Optimization Complete!")

                st.markdown("### 🏟️ The Starting XI (with FDR)")
                st.caption("Dots indicate overall team strength: Green = Easy, Grey = Avg, Red = Hard")
                st.markdown("<div class='pitch-container'>", unsafe_allow_html=True)
                
                def render_row(players_in_row):
                    if not players_in_row.empty:
                        cols = st.columns(len(players_in_row))
                        for col, row_data in zip(cols, players_in_row.itertuples()):
                            strength_val = int(row_data.team_strength)
                            fdr_class = f"fdr-{strength_val}" if strength_val in [2, 3, 4, 5] else "fdr-3"
                            
                            col.markdown(f"""
                            <div class='pitch-card'>
                                <div class='fdr-badge {fdr_class}'>{strength_val}</div>
                                <b>{row_data.second_name}</b><br>
                                <span style='font-size:12px; color:#8f9bba;'>{row_data.team_name}</span><br>
                                <span style='color:#00f2fe;'>£{row_data.cost_m}m</span>
                            </div>
                            """, unsafe_allow_html=True)
                    st.write("") 

                render_row(starters[starters['element_type'] == 1]) 
                render_row(starters[starters['element_type'] == 2]) 
                render_row(starters[starters['element_type'] == 3]) 
                render_row(starters[starters['element_type'] == 4]) 
                st.markdown("</div>", unsafe_allow_html=True)

            else:
                st.error("⚠️ Optimizer failed to find a valid squad.")

# ==========================================
# MODULE 3 & 4: PLOTLY MATRIX & TABLE
# ==========================================
elif app_mode == "📈 Team Betting Edge":
    st.title("📈 Predictive Match Analytics")
    if match_df is not None and not match_df.empty:
        selected_season = st.selectbox("Select Season:", sorted(match_df['Season'].unique().tolist(), reverse=True))
        szn_match_df = match_df[match_df['Season'] == selected_season]
        
        if not szn_match_df.empty:
            home_m = szn_match_df[['Home_Team', 'Home_Score_FT', 'Away_Score_FT']].copy()
            home_m.columns = ['Team', 'Scored_FT', 'Conceded_FT']
            team_stats = home_m.groupby('Team').mean().reset_index()
            
            fig = px.scatter(team_stats, x='Conceded_FT', y='Scored_FT', text='Team', size='Scored_FT', color_discrete_sequence=['#00f2fe'])
            fig.update_traces(textposition='top center')
            fig.update_layout(title="Home Performance Matrix", template=chart_theme, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

elif app_mode == "📊 Live League Table":
    st.title("📊 League Table & Trends")
    st.info("Ag-Grid interactive league table placeholder. Data loader handles primary focus.")
