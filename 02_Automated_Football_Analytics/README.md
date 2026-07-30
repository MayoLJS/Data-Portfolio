# ⚽ Automated Sports Analytics ETL Pipeline

## 📌 Business Problem
For sports analytics firms, betting syndicates, and team performance analysts, manual match-day data collection is slow, resource-heavy, and prone to human error. To conduct accurate predictive modeling, analysts require a reliable, automated daily feed of match statistics. 

The objective of this project was to build a **Zero-Touch ETL (Extract, Transform, Load) Pipeline** that automatically fetches, normalizes, and stores live global football data without manual intervention.

## ⚙️ Architecture & Data Flow
`API-Football (v3)` ➡️ `Python (Requests)` ➡️ `Pandas (JSON Normalization)` ➡️ `GitHub Actions (Cron)` ➡️ `Automated CSV Artifact`

## 🛠️ Tech Stack & Engineering Skills
* **Python (`requests`, `pandas`, `json`):** API authentication, pagination handling, and nested JSON parsing.
* **Data Wrangling:** Flattening complex, non-relational dictionary payloads into structured tabular formats via `pd.json_normalize`.
* **CI/CD & Automation:** Scheduled pipeline execution using **GitHub Actions**.

## 💡 Key Engineering Outcomes
1. **Automated Live Ingestion:** Replaced manual CSV downloads with a live API connection, pulling real-time match data (scores, halftime stats, full-time stats, and venue info) directly from API-Football.
2. **Defensive Parsing:** Engineered the `extract_match_data.py` script to handle missing keys and deeply nested arrays, ensuring the pipeline does not break when specific match statistics are unavailable.
3. **Cloud Scheduling:** Deployed a cron job via GitHub actions to run the extraction script daily, creating a hands-off, consistently updating repository of match data.

## 📂 Project Structure
* `extract_match_data.py`: The core Python ETL script. Handles the API GET requests, normalizes the JSON payloads, and stages the final dataframe.
* `.github/workflows/`: (If applicable) Contains the YAML file dictating the automated scheduling of the script.

## 🚀 Future Scalability & Next Steps
* **Database Migration:** Phase 2 of this project will replace the flat `football_data.csv` output with an automated load mechanism into a cloud data warehouse (e.g., PostgreSQL or Google BigQuery) for persistent storage.
* **BI Integration:** Connect the future cloud database to Power BI for a live-updating dashboard tracking team performance metrics.
