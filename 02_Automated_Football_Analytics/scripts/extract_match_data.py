import requests
import pandas as pd
import os
import time
from datetime import datetime

def fetch_rolling_3_year_matches():
    """Fetches up to 3 years of rolling Premier League match results."""
    api_key = os.environ.get("FOOTBALL_API_KEY")
    
    if not api_key:
        raise ValueError("Missing API Key. Check your environment variables.")

    url = "https://api.football-data.org/v4/competitions/PL/matches"
    headers = {
        "X-Auth-Token": api_key
    }
    
    match_records = []
    
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    latest_season = current_year - 1 if current_month < 8 else current_year
    seasons = [str(latest_season - i) for i in range(3)]
    print(f"Fetching data for seasons: {seasons}")
    
    for season in seasons:
        params = {
            "status": "FINISHED",
            "season": season
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            for match in matches:
                score_data = match.get('score', {})
                ht_data = score_data.get('halfTime', {})
                ft_data = score_data.get('fullTime', {})

                match_records.append({
                    'Match_ID': match.get('id'),
                    'Date': match.get('utcDate'),
                    'Season': season,
                    'Home_Team': match.get('homeTeam', {}).get('name'),
                    'Away_Team': match.get('awayTeam', {}).get('name'),
                    'Home_Score_HT': ht_data.get('home'),
                    'Away_Score_HT': ht_data.get('away'),
                    'Home_Score_FT': ft_data.get('home'), 
                    'Away_Score_FT': ft_data.get('away'),
                    'Winner': score_data.get('winner')
                })
            print(f"Successfully fetched {len(matches)} matches for season {season}")
        else:
            print(f"Failed/Skipped season {season} (Status: {response.status_code}): {response.text}")
        
        time.sleep(6)
        
    return pd.DataFrame(match_records)

def transform_and_save_data(df):
    """Cleans the dataframe and saves it to BOTH analytics and FPL data folders."""
    if df.empty:
        raise RuntimeError("No match data fetched from API. Check API key permissions and response logs.")

    df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_localize(None)
    df = df.drop_duplicates(subset=['Match_ID'])
    df = df.sort_values(by='Date', ascending=False)
    
    # Save destinations
    output_targets = [
        "02_Automated_Football_Analytics/data",
        "04_Fantasy_PL/data"
    ]
    
    filename = "pl_rolling_3_years_latest.csv"
    
    for target_dir in output_targets:
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)
        df.to_csv(target_path, index=False)
        print(f"Saved {len(df)} matches to {target_path}")

if __name__ == "__main__":
    print("Starting rolling 3-year football data pipeline...")
    raw_df = fetch_rolling_3_year_matches()
    transform_and_save_data(raw_df)
