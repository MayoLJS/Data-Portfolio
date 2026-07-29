# 🏥 NHS Scotland Elective Care & Breach Trend Analysis

## 📌 Business Problem
Following systemic disruptions to healthcare services, NHS Scotland faced a massive backlog in elective care[cite: 1]. The raw clinical data provided by Public Health Scotland was difficult to analyze due to legacy identifiers, inconsistent schemas, and administrative latency[cite: 1]. The objective of this project was to move beyond simply counting total waitlists and instead engineer a data model that identifies the specific regions and medical specialties suffering the most severe bottlenecks[cite: 1].

## 🛠️ Tools Used
* **SQL Server (T-SQL):** Data staging, schema hardening, and view creation[cite: 1].
* **Advanced SQL:** Window functions (`LAG`), conditional aggregation, CTEs, and dynamic data casting[cite: 1, 2].
* **SSIS & Excel:** Data ingestion and secondary processing[cite: 1].

## 💡 Key Analytical Outcomes
By building a defensive engineering pipeline and a robust normalization layer (`vw_Clean_Treatment_Waits`), this analysis extracted actionable diagnostic intelligence[cite: 1]:

1. **Identified Hidden Regional Risk:** Modeled "Breach Density" to show that while urban boards have the largest total lists, **NHS Grampian (18.2%)** and **NHS Lothian (17.85%)** have the highest proportion of patients waiting over 52 weeks[cite: 1].
2. **Quantified Clinical Inequality:** Calculated disparity metrics showing that complex cases are being left behind. Patients requiring Plastic Surgery or Haematology wait over 3 times longer (3.3x and 3.2x respectively) than the median patient on those lists[cite: 1].
3. **Tracked Recovery Velocity:** Utilized MoM velocity calculations to prove that the national recovery effort is accelerating, dropping **9.87%** from its May 2025 peak[cite: 1].

## 📂 Project Structure
* `NHS_Elective_Care_Analysis.sql`: The complete T-SQL script containing the environment setup, data normalization views, QA checks, and advanced KPI calculations.
* `Ongoing_and_Completed_Waits_Monthly.csv`: The core dataset containing 41,000+ records from Public Health Scotland[cite: 1].

## 🚀 The Bottom Line
This project proves that healthcare recovery is not just about clearing easy cases to reduce raw numbers[cite: 1]. By engineering clean, structured data, we can pinpoint the exact specialties (like Plastic Surgery) and regions (like Grampian) that require targeted operational intervention to resolve extreme long-tail wait times[cite: 1].
