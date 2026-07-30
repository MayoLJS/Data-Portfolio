# ⚽ Automated Football Analytics Pipeline

## 📌 Business Problem
Tracking weekly team performance, match statistics, and form streaks typically requires manual data entry and spreadsheet updates. For sports analysts and management teams, this manual overhead causes reporting delays. This project solves that by building a fully automated ETL pipeline that extracts live weekend match data, processes performance metrics, and updates a reporting dashboard without human intervention.

## 🛠️ Tools & Architecture
* **Orchestration:** GitHub Actions (Automates the weekly execution schedule).
* **Ingestion:** Python & `requests` (Connects to a sports API to fetch live match JSON data).
* **Transformation (ETL):** Python & `pandas` (Cleans missing data, calculates win/loss streaks, and structures the output).
* **Storage & BI:** CSV data storage feeding directly into a Power BI dashboard for visualization.

## 💡 Pipeline Logic & Engineering
1. **Automated Trigger:** A GitHub Actions cron job fires every Monday morning.
2. **Defensive Extraction:** The Python script authenticates with the API, fetches the latest Premier League match results, and handles rate-limiting.
3. **Transformation Layer:** The raw JSON is flattened. The script calculates aggregated metrics like goals scored, goals conceded, and current form (last 5 matches).
4. **Data Product Delivery:** The clean dataset is saved and committed to the repository, ready to be ingested by Power BI.

## 📂 Project Structure
* `scripts/extract_match_data.py`: The Python engine handling API extraction and data transformation.
* `.github/workflows/weekly_update.yml`: The YAML configuration file controlling the GitHub Actions schedule.
* `data/`: Directory storing the historical and latest clean CSV files.
* `Football_Form_Dashboard.pbix`: The final interactive data product.

## 🚀 The Bottom Line
By leveraging Python and cloud orchestration, this pipeline eliminates manual data entry. It demonstrates the ability to handle live API endpoints, schedule cloud workflows, and engineer raw sports data into clean, automated business intelligence.
