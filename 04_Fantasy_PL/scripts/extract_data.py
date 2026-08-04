import requests
import pandas as pd
import os
from datetime import datetime

def fetch_and_save_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        players = data.get("elements", [])
        df = pd.DataFrame(players)
        
        columns_to_keep = [
            'id', 'first_name', 'second_name', 'team', 'element_type',
            'now_cost', 'selected_by_percent', 'form', 'total_points',
            'minutes', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'own_goals', 'penalties_saved',
            'penalties_missed', 'yellow_cards', 'red_cards', 'saves',
            'bonus', 'bps', 'influence', 'creativity', 'threat', 'ict_index'
        ]
        
        available_columns = [col for col in columns_to_keep if col in df.columns]
        df_filtered = df[available_columns]
        
        os.makedirs("data", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/fpl_players_{timestamp}.csv"
        
        df_filtered.to_csv(filename, index=False)
        print(f"Successfully saved player stats to {filename}")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

if __name__ == "__main__":
    fetch_and_save_fpl_data()
