import os
import pandas as pd
import soccerdata as sd

def extract_and_save():
    # Pivot to Understat: Great for xG, xA, and shooting stats without the CAPTCHAs
    understat = sd.Understat(leagues=['ENG-Premier League'], seasons=['2324'])
    
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
