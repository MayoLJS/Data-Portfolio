# UK Household Financial Resilience Analysis (2024-2025)

## Project Overview
This project investigates the financial health and debt structures of UK households using the **Bank of England (BoE) NMG Survey data**. The study identifies a critical "Awareness Gap" in the 2025 economy, where objective debt levels are accelerating while subjective financial stress remains at record lows.

## Data Source
https://www.bankofengland.co.uk/statistics/research-datasets

---

## Technical Stack
* **Platform:** Databricks (Lakehouse Architecture)
* **Languages:** SQL (Data Transformation), Python (Visualization)
* **Libraries:** Pandas, Seaborn, Matplotlib
* **Data Pipeline:** Medallion Architecture (Bronze -> Silver -> Gold)

---

## Data Engineering Pipeline

### 1. Bronze to Silver (Cleaning)
Raw survey data was ingested from Excel volumes. Key transformations included:
* Standardizing 17-band Stata income codes into numerical midpoints for calculation.
* Mapping categorical variables for Housing Tenure and Age Brackets.
* Handling null values in savings (`be07`) and debt (`totaldebt`) columns to ensure analytical integrity.

### 2. Silver to Gold (Feature Engineering)
A Gold-level analytical view was created to calculate core resilience metrics:
* **Debt-to-Income (DTI) Ratio:** Total Household Debt / Gross Annual Income.
* **Financial Fragility %:** Identifying households with active debt but £0 in liquid savings.
* **Stress Gap:** Comparing calculated leverage against self-reported "High Stress" status.

---

## Analytical Insights

### The Liquidity Gap
Analysis of the **"Danger Zone"** (debt with zero buffer) shows that housing tenure is the primary predictor of fragility:
* **Social Renters:** Over **80%** are financially fragile.
* **Outright Owners:** Frequently "cash poor," with fragility levels exceeding **80%** despite property wealth.
* **Mortgage Holders:** Highly resilient, with less than **5%** lacking a savings buffer.

### The "Silent" Debt Drift
The data reveals a rapid acceleration of debt in specific sectors between 2024 and 2025:
* **Rental Spike:** The **25-34 Social Rental** group saw DTI ratios climb from ~0.5 to 2.33 in one year.
* **Mortgage Intensity:** Young mortgage holders (25-34) carry the highest overall intensity with a 2.63 DTI.
* **Stress Paradox:** Despite DTIs reaching 2.63, reported "High Financial Stress" consistently remained at 0% across the 2025 sample.

---

## Key Conclusions
The project demonstrates that UK financial risk is currently concentrated in the **25-34 age bracket**, regardless of housing type. The disconnect between objective leverage and subjective worry suggests a normalization of high debt that poses a structural risk to household resilience.
"""
