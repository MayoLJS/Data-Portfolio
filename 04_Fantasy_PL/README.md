# ⚽ Premier League Hub & Prescriptive FPL Optimizer

🚀 **[Click here to view the live interactive web app!](https://respectthel.streamlit.app/)**

## 📖 Project Overview
This project is a Full-Stack Data Application designed to solve complex constraint-based resource allocation problems (Operations Research) while providing historical, rolling analytics for the English Premier League. 

Moving beyond descriptive analytics ("what happened"), this tool leverages **Prescriptive Analytics** ("what should we do?"). It uses Integer Linear Programming to mathematically deduce the absolute best 15-player Fantasy Premier League (FPL) squad based on dynamic user constraints, while simultaneously tracking 3-year rolling match data to identify betting edges and team form.

## 🛠️ Architecture & Directory Structure
This repository contains two parallel data workflows:
1. **The Cloud Application (`app.py`):** A live Streamlit web application hosted on Streamlit Community Cloud. It bypasses static files to pull live player data directly from the official FPL API, caching it hourly.
2. **The ETL Pipeline (`scripts/` & `data/`):** Python scripts triggered by GitHub Actions that automatically extract, transform, and load historical PL match data into static CSVs. *Note: These files are staged as the backend semantic model for a future Power BI dashboard integration.*

## 🌟 Core Modules

### 1. ⚡ FPL Squad Optimizer (The Math Engine)
Instead of relying on gut feeling, this module treats team selection as a **Knapsack Optimization Problem**.
* **The Engine:** Powered by the `PuLP` linear programming library.
* **The Logic:** Maximizes a custom composite score (built from user-weighted sliders for Form, Ownership, and ICT index) subject to strict FPL constraints:
  * Total budget $\leq$ £100M (or user-defined).
  * Exactly 15 players (2 GK, 5 DEF, 5 MID, 3 FWD).
  * Maximum of 3 players per Premier League club.
* **Feature:** Allows users to set "Hard Constraints" by locking in up to 5 premium "must-have" players, forcing the algorithm to mathematically solve for the remaining budget.

### 2. 📈 Predictive Match Analytics (Betting Edge)
Ingests a rolling 3-year match database to identify tactical trends and betting anomalies using `Plotly`.
* **The Chaos Quadrant:** An inverted scatter plot comparing Average Goals Scored vs. Conceded. Isolates the league's elite (Top-Left) from the tactically vulnerable.
* **Halftime Turnarounds:** Visualizes team resilience, identifying which clubs successfully rescue points when trailing at halftime, and which clubs are notorious "bottle jobs" when leading.

### 3. 👤 Player Scout Card
A dynamic player database that translates raw API metrics into visual percentile rankings, allowing users to instantly compare a player's Influence, Creativity, Threat (ICT), and Bonus Points System (BPS) output against the rest of the league.

### 4. 📊 Live League Table & Form Tracker
An iterative chronological engine that replays historical matches gameweek-by-gameweek. It calculates points, goal difference, and goals scored from scratch to generate a dynamic, multiline trend chart of team positions over the course of a season.

## 💻 Tech Stack
* **Language:** Python 3
* **Frontend/Hosting:** Streamlit, Streamlit Community Cloud
* **Operations Research:** PuLP (Integer Linear Programming)
* **Data Manipulation:** Pandas, NumPy
* **Data Visualization:** Plotly Express, Plotly Graph Objects
* **APIs Consumed:** Official Fantasy Premier League API, Football-Data.org API

## 🏃‍♂️ How to Run Locally
If you wish to run the prescriptive optimizer on your local machine:

1. Clone the repository:
   ```bash
   git clone [https://github.com/MayoLJS/Data-Portfolio.git](https://github.com/MayoLJS/Data-Portfolio.git)
