import requests
import pandas as pd
import os
import time
from datetime import datetime

def fetch_rolling_3_year_matches():
    """Fetches up to 3 years of rolling Premier League match results."""
    api_key = os.environ.get("FOOTBALL_API_KEY")
    
    if not api_key:
        raise ValueError("Missing API Key")

    url = "https://api.football-data.org/v4/competitions/PL/matches"
    headers = {
        "X-Auth-Token": api_key
    }
    
    match_records = []
    
    # Dynamically determine the current season year (starts in August)
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    if current_month < 8:
        latest_season = current_year - 1
    else:
        latest_season = current_year
        
    # Create a list of the last 3 seasons dynamically
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
            for match in data.get('matches', []):
                match_records.append({
                    'Match_ID': match.get('id'),
                    'Date': match.get('utcDate'),
                    'Season': season,
                    'Home_Team': match.get('homeTeam', {}).get('name'),
                    'Away_Team': match.get('awayTeam', {}).get('name'),
                    'Home_Score': match.get('score', {}).get('fullTime', {}).get('home'),
                    'Away_Score': match.get('score', {}).get('fullTime', {}).get('away'),
                    'Winner': match.get('score', {}).get('winner')
                })
            print(f"Successfully fetched season {season}")
        else:
            print(f"Skipped season {season} (API Status: {response.status_code}). Free tier may restrict older data.")
        
        # Sleep for 6 seconds to respect the free API rate limit (10 requests/minute)
        time.sleep(6)
        
    return pd.DataFrame(match_records)

def transform_and_save_data(df):
    """Cleans the dataframe and saves it to the designated data folder."""
    if df.empty:
        print("No data fetched. Exiting.")
        return

    # Convert UTC date string to actual datetime objects
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_convert(None)
    
    # Drop duplicates and sort newest to oldest
    df = df.drop_duplicates(subset=['Match_ID'])
    df = df.sort_values(by='Date', ascending=False)
    
    # Ensure the data directory exists specifically for GitHub Actions root execution
    output_dir = "02_Automated_Football_Analytics/data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to a timestamped CSV file
    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = f"{output_dir}/pl_rolling_3_years_{timestamp}.csv"
    
    df.to_csv(output_path, index=False)
    print(f"Extraction complete. {len(df)} matches saved to {output_path}")

if __name__ == "__main__":
    print("Starting rolling 3-year football data pipeline...")
    raw_df = fetch_rolling_3_year_matches()
    transform_and_save_data(raw_df)
