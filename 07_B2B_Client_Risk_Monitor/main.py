import os
import requests
import pandas as pd
from datetime import datetime
from google.cloud import bigquery

# Securely load credentials from GitHub Actions environment variables
API_KEY = os.environ.get("CH_API_KEY")
PROJECT_ID = "olumayowa"  # Your GCP Project ID
DATASET_ID = "client_risk_portfolio"
TABLE_ID = "daily_risk_scores"

PORTFOLIO = [
    "02050399",  
    "00002065",  
    "11371436",  
    "08209948",  
    "04362159"   
]

def get_company_metrics(company_number, api_key):
    url = f"https://api.company-information.service.gov.uk/company/{company_number}"
    response = requests.get(url, auth=(api_key, ""))
    
    if response.status_code != 200:
        return None
        
    data = response.json()
    
    creation_date_str = data.get("date_of_creation")
    age = 0.0
    if creation_date_str:
        creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
        age = round((datetime.now() - creation_date).days / 365.25, 1)
        
    accounts = data.get("accounts", {})
    is_overdue = accounts.get("next_accounts", {}).get("overdue", False)
    
    return {
        "company_number": company_number,
        "company_name": data.get("company_name"),
        "company_age_years": age,
        "accounts_overdue": is_overdue,
        "has_insolvency_history": data.get("has_insolvency_history", False),
        "extraction_date": datetime.utcnow().isoformat()
    }

def calculate_risk(row):
    score = 5
    if row["accounts_overdue"]:
        score += 45
    if row["has_insolvency_history"]:
        score += 35
    if row["company_age_years"] < 3.0:
        score += 20
    return min(score, 100)

def assign_tier(score):
    if score >= 60:
        return "High Risk"
    elif score >= 25:
        return "Medium Risk"
    return "Low Risk"

def main():
    print(f"Processing {len(PORTFOLIO)} companies...")
    
    records = [get_company_metrics(num, API_KEY) for num in PORTFOLIO]
    df = pd.DataFrame([r for r in records if r is not None])
    
    if df.empty:
        print("No valid data extracted.")
        return
        
    df["default_risk_score"] = df.apply(calculate_risk, axis=1)
    df["risk_tier"] = df["default_risk_score"].apply(assign_tier)
    
    # BigQuery Client automatically uses the credentials setup by GitHub Actions
    client = bigquery.Client(project=PROJECT_ID)
    
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    
    print(f"Success! Loaded {len(df)} rows into BigQuery table: {TABLE_ID}")

if __name__ == "__main__":
    main()
