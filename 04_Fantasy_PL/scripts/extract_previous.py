import pandas as pd
import os

def download_historical_fpl_data():
    seasons = ["2023-24", "2024-25", "2025-26"]
    base_url = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{}/cleaned_players.csv"
    
    columns_to_keep = [
        'id', 'first_name', 'second_name', 'team', 'element_type',
        'now_cost', 'selected_by_percent', 'form', 'total_points',
        'minutes', 'goals_scored', 'assists', 'clean_sheets',
        'goals_conceded', 'own_goals', 'penalties_saved',
        'penalties_missed', 'yellow_cards', 'red_cards', 'saves',
        'bonus', 'bps', 'influence', 'creativity', 'threat', 'ict_index'
    ]
    
    os.makedirs("data", exist_ok=True)
    all_seasons_df = []
    
    for season in seasons:
        print(f"Downloading data for the {season} season...")
        url = base_url.format(season)
        
        try:
            df = pd.read_csv(url)
            df['season'] = season
            
            available_columns = [col for col in columns_to_keep if col in df.columns]
            df_filtered = df[available_columns + ['season']]
            
            all_seasons_df.append(df_filtered)
            
        except Exception as e:
            print(f"Failed to download data for {season}. Error: {e}")

    if all_seasons_df:
        final_df = pd.concat(all_seasons_df, ignore_index=True)
        filename = "data/fpl_players_previous.csv"
        final_df.to_csv(filename, index=False)
        print(f"Successfully combined and saved all historical stats to {filename}")

if __name__ == "__main__":
    download_historical_fpl_data()
