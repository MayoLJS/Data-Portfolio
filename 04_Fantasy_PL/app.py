import streamlit as st
import pandas as pd
import requests
import pulp

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (Dark Theme)
# ==========================================
st.set_page_config(page_title="FPL Squad Architect", page_icon="⚽", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #e0e6ed; }
    section[data-testid="stSidebar"] { background-color: #121621; border-right: 1px solid #1e2638; }
    .metric-card { background-color: #161b26; border: 1px solid #232b3e; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .badge-cyan { background-color: rgba(0, 242, 254, 0.15); color: #00f2fe; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA EXTRACTION (Cached for Speed)
# ==========================================
@st.cache_data(ttl=3600)
def load_fpl_data():
    """Fetches live FPL player metrics from the official API."""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            st.error(f"FPL API is currently unavailable (Status Code: {response.status_code}).")
            return None
    except requests.exceptions.RequestException:
        st.error("Failed to connect to FPL API. Please check your internet connection.")
        return None
    
    data = response.json()
    players = pd.DataFrame(data['elements'])
    teams = pd.DataFrame(data['teams'])
    
    # Map team names
    team_dict = dict(zip(teams['id'], teams['name']))
    players['team_name'] = players['team'].map(team_dict)
    
    # Safely cast numerical columns (crucial for Linear Programming math)
    num_cols = ['now_cost', 'selected_by_percent', 'form', 'total_points', 'influence', 'creativity', 'threat', 'ict_index']
    for col in num_cols:
        players[col] = pd.to_numeric(players[col], errors='coerce').fillna(0.0)
            
    # FPL stores prices multiplied by 10 (e.g., 100 = £10.0M)
    players['cost_m'] = players['now_cost'] / 10.0
    
    # Map Positions
    pos_map = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    players['position'] = players['element_type'].map(pos_map)
    
    return players

# ==========================================
# 3. SIDEBAR NAVIGATION & SETTINGS
# ==========================================
st.sidebar.title("⚽ FPL SQUAD ARCHITECT")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio("Select Module:", ["⚡ Squad Optimizer", "👤 Player Database"])

# Load the data
players_df = load_fpl_data()

# ==========================================
# MODULE 1: FPL SQUAD OPTIMIZER (Linear Programming)
# ==========================================
if app_mode == "⚡ Squad Optimizer":
    st.title("⚡ Prescriptive FPL Squad Optimizer")
    st.write("Uses Integer Linear Programming (PuLP) to select the mathematical absolute best 15-player squad based on your custom strategy.")
    
    # User Inputs
    st.sidebar.header("1. Budget Constraints")
    budget = st.sidebar.number_input("Available Budget (£M)", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
    
    st.sidebar.header("2. Custom Strategy Weights")
    advanced_mode = st.sidebar.toggle("Advanced Metric Breakdown", value=False)
    
    if not advanced_mode:
        st.sidebar.info("💡 **Base Mode:** Uses bundled ICT Index alongside Form & Ownership.")
        w_form = st.sidebar.slider("Form (Short-Term Momentum)", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership % (Consensus)", 0, 100, 40, 5)
        w_ict = st.sidebar.slider("ICT Index (Overall Quality)", 0, 100, 40, 5)
        weights = {'form': w_form, 'selected_by_percent': w_own, 'ict_index': w_ict}
    else:
        st.sidebar.info("⚙️ **Advanced Mode:** Unbundles ICT into Influence, Creativity, and Threat.")
        w_form = st.sidebar.slider("Form", 0, 100, 20, 5)
        w_own = st.sidebar.slider("Ownership %", 0, 100, 20, 5)
        w_inf = st.sidebar.slider("Influence (Impact)", 0, 100, 20, 5)
        w_cre = st.sidebar.slider("Creativity (Assists)", 0, 100, 20, 5)
        w_thr = st.sidebar.slider("Threat (Goals)", 0, 100, 20, 5)
        weights = {'form': w_form, 'selected_by_percent': w_own, 'influence': w_inf, 'creativity': w_cre, 'threat': w_thr}

    # Normalize weights so they sum to 1.0 internally
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    # Trigger Optimization
    if st.button("🚀 Generate Optimal Squad", type="primary", use_container_width=True):
        if players_df is not None and not players_df.empty:
            df = players_df.copy()
            
            # Step 1: Normalize selected metrics (0 to 1 scale) to prevent large numbers from dominating
            for metric in weights.keys():
                min_v, max_v = df[metric].min(), df[metric].max()
                # Safety check: avoid division by zero if all players have the exact same stat
                if max_v > min_v:
                    df[f'{metric}_norm'] = (df[metric] - min_v) / (max_v - min_v)
                else:
                    df[f'{metric}_norm'] = 0.0
            
            # Step 2: Calculate composite score based on user weights
            df['custom_score'] = sum(df[f'{metric}_norm'] * w for metric, w in weights.items())
                
            # Step 3: PuLP Linear Optimization Engine
            prob = pulp.LpProblem("Optimal_FPL_Squad", pulp.LpMaximize)
            player_vars = pulp.LpVariable.dicts("player", df.index, cat='Binary')
            
            # Objective Function: Maximize total custom score
            prob += pulp.lpSum([df.loc[i, 'custom_score'] * player_vars[i] for i in df.index])
            
            # Constraint 1: Budget (Multiply user budget by 10 to match API format)
            prob += pulp.lpSum([df.loc[i, 'now_cost'] * player_vars[i] for i in df.index]) <= (budget * 10) 
            
            # Constraint 2: Total 15 Players
            prob += pulp.lpSum([player_vars[i] for i in df.index]) == 15 
            
            # Constraint 3: Strict Position Limits (Fully closed brackets)
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 1]) == 2 # Exactly 2 GK
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 2]) == 5 # Exactly 5 DEF
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 3]) == 5 # Exactly 5 MID
            prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'element_type'] == 4]) == 3 # Exactly 3 FWD
            
            # Constraint 4: Max 3 players per Premier League club
            for t_id in df['team'].unique():
                prob += pulp.lpSum([player_vars[i] for i in df.index if df.loc[i, 'team'] == t_id]) <= 3
                
            # Solve the mathematical model
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            # Step 4: Extract and Format Results
            selected_indices = [i for i in df.index if player_vars[i].varValue == 1]
            squad = df.loc[selected_indices].copy()
            squad = squad.sort_values(by=['element_type', 'cost_m'], ascending=[True, False])
            
            if len(squad) == 15:
                st.success("✅ Optimization Complete! Here is your mathematically perfect squad based on your parameters.")
                
                # Top Summary Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Spent", f"£{squad['cost_m'].sum():.1f}M")
                c2.metric("Remaining Bank", f"£{budget - squad['cost_m'].sum():.1f}M")
                c3.metric("Avg Squad Form", f"{squad['form'].mean():.2f}")
                c4.metric("Avg
