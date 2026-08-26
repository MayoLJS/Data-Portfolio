import os
import pandas as pd
import soccerdata as sd
from datetime import datetime

def get_rolling_seasons(window=3):
    now = datetime.now()
    # The European football season typically rolls over in July
    start_year = now.year if now.month >= 7 else now.year - 1
    
    seasons = []
    for i in range(window - 1, -1, -1):
        y1 = start_year - i
        y2 = y1 + 1
        season_str = f"{str(y1)[-2:]}{str(y2)[-2:]}"
        seasons.append(season_str)
        
    return seasons

def extract_and_save():
    rolling_seasons = get_rolling_seasons(3)
    print(f"Extracting data for seasons: {rolling_seasons}")
    
    # Pivot to Understat: Pulling dynamic 3-year rolling window
    understat = sd.Understat(leagues=['ENG-Premier League'], seasons=rolling_seasons)
    
    # Ensure data output folder exists
    os.makedirs('data', exist_ok=True)

    # ---------------------------------------------------------
    # 1. EXTRACT TEAM MATCH STATS (Existing functionality)
    # ---------------------------------------------------------
    print("Fetching team match stats...")
    df_teams = understat.read_team_match_stats()
    df_teams = df_teams.reset_index()
    
    # Flatten multi-level column names if present
    if isinstance(df_teams.columns, pd.MultiIndex):
        df_teams.columns = ['_'.join(col).strip('_') for col in df_teams.columns.values]
        
    output_path_teams = 'data/team_shooting.csv'
    df_teams.to_csv(output_path_teams, index=False)
    print(f"✅ Team stats successfully saved to {output_path_teams}")

    # ---------------------------------------------------------
    # 2. EXTRACT GRANULAR SHOT EVENTS (New functionality)
    # ---------------------------------------------------------
    print("Fetching granular shot events...")
    try:
        df_shots = understat.read_shot_events()
        df_shots = df_shots.reset_index()
        
        # Flatten multi-level column names if present
        if isinstance(df_shots.columns, pd.MultiIndex):
            df_shots.columns = ['_'.join(col).strip('_') for col in df_shots.columns.values]
            
        output_path_shots = 'data/understat_shots.csv'
        df_shots.to_csv(output_path_shots, index=False)
        print(f"✅ Shot events successfully saved to {output_path_shots}")
    except Exception as e:
        print(f"❌ Failed to extract shot events: {e}")

if __name__ == '__main__':
    extract_and_save()
