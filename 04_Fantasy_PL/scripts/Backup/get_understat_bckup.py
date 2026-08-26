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
    
    # Extract team stats
    df = understat.read_team_match_stats()
    
    # Reset multi-index dataframe structure for easy CSV export
    df = df.reset_index()
    
    # Flatten multi-level column names if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip('_') for col in df.columns.values]
    
    # Ensure data output folder exists
    os.makedirs('data', exist_ok=True)
    
    # Save output to CSV
    output_path = 'data/team_shooting.csv'
    df.to_csv(output_path, index=False)
    print(f"Data successfully saved to {output_path}")

if __name__ == '__main__':
    extract_and_save()
