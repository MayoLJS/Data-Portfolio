# 🌍 Global Sovereign Debt & Creditor Concentration Monitor

**Prepared by:** Olumayowa Osimosu
**Domain Expertise:** Financial Data Analysis | Risk Operations | Regulatory Compliance
**Dataset:** Bank of England / Bank of Canada (BoC-BoE) Sovereign Default Database (2024 Edition)

## 📌 The Business Problem

The primary objective of this project was to engineer a high-performance analytical tool to monitor 60+ years of sovereign debt trend. While traditional reporting often focuses on total debt-to-GDP, this framework specifically isolates Creditor Concentration Risk to identify over-reliance on single lending blocks. 

In the context of emerging markets, understanding the identity of the creditor is as vital as the amount of the debt. "Hidden" debt concentration poses a significant threat to audit transparency and sovereign creditworthiness. Think of a country like a person with several credit cards. While most banks only look at the total amount that person owes, this project looks at who they owe it to. This tool acts as an early warning system that flags when a country is becoming too dependent on one source, helping experts catch financial problems before they turn into a global crisis.


---

## 🛠️ Technical Architecture (The Process)

To ensure the monitor is scalable and "audit-ready," a Three-Tier Data Architecture was implemented:

* **Tier 1: Data Engineering (Power Query ETL)**
    * **Ingestion:** Automated the connection to the BoE/BoC 2024 CSV, JSON, and XML data, managing complex multi-line metadata headers.
    * **Normalization:** Transformed static historical records into a dynamic time-series format for 167 country profiles.
* **Tier 2: Analytical Modelling (Power Pivot & DAX)** 
    * Custom DAX (Data Analysis Expressions) were authored to calculate core engine metrics.
    * Calculated metrics include Total Debt Volume, Targeted Creditor Exposure, and a Concentration Risk Index.
* **Tier 3: Executive Visualization (Presentation Layer)** 
    * **Trend Analysis:** A Multi-Series Line Chart displays the Concentration Risk Index across various regions and the global average.
    * **Interactivity:** Synchronized Slicers allow for instant toggling between regions and specific nations, such as Nigeria or Mali.

---

## 💡 Key Findings & Strategic Insights

The tool identified several critical shifts documented in the 2024 database update:

* **The "China Shift":** Identified defaults to China rose by 28% (nearly $50 billion) in 2023, while defaults to the Paris Club remained steady at approximately $78 billion.
* **Concentrated Value:** Just three sovereigns—Venezuela, Russia, and Iraq—accounted for 35% of the overall amount in default in 2023.
* **The 2021 HIPC Peak:** China's concentration risk in Heavily Indebted Poor Countries (HIPC) peaked at 34.2% in 2021.
* **Nigeria Deep-Dive:** Analysis reveals localized spikes in concentration following major infrastructure financing cycles, particularly around 2013-2014.

---

## 🛡️ Data Governance & Internal Controls

Reflecting a background in Operational Risk, the tool includes two specific internal controls to ensure data integrity:

* **Reporting Coverage Monitor:** A validation table ensures historical trends are not skewed by reporting lags (stabilized at ~167 countries).
* **Risk Threshold Alerts:** Conditional formatting visually flags any region exceeding a 20% concentration threshold for mandatory regulatory review.

---

## 📂 Repository Contents

* 📄 **`Project_Report.pdf`**: The comprehensive project documentation detailing the ETL methodology, DAX formulas, historical accuracy revisions, and full executive dashboard views.
