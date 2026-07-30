# ScotRail Performance Audit: The Cost of External Accountability

## 🏢 The Firm Position
ScotRail must immediately cease absorbing the primary financial and reputational penalties for network delays. The data definitively proves that infrastructure failures, managed entirely by Network Rail, are the overwhelming driver of system delays, not ScotRail's internal operations. 

## 📊 The Data Defense
By reshaping and analyzing the ORR 2025 periodic statistics, the delay attribution data removes operational ambiguity:

* **The Accountability Imbalance:** Network Rail (Infrastructure) accounted for **886,906 delay minutes** in 2025, severely overshadowing ScotRail's operational contribution of 636,614 minutes. 
* **External Primary Drivers:** The absolute largest bottlenecks on the grid are outside of train operator control. *Network Management Other* (244,642 mins) and *Non-Track Assets* (218,478 mins) dictate the failure rate of the network.
* **The Period 08 Crisis:** Total delay minutes spiked past 100,000 in a single period. Public-facing metrics currently force the operator to take the hit for severe infrastructure degradation.

## 🎯 Strategic Recommendation: What to Stop Doing
1. **Stop Absorbing Compensation Costs:** Delay Repay schemes and passenger compensation should be automatically cross-charged to Network Rail via Service Level Agreement (SLA) penalty clauses whenever the root cause is flagged as *Non-Track Assets* or *Network Management*.
2. **Stop Blanket Apologies:** Transition corporate communications and station dashboards to clearly delineate between operator errors (Traincrew, Fleet) and infrastructure failures. Protect the operator's brand equity by redirecting accountability to the infrastructure provider.

## 🛠️ Technical Implementation
* **Language:** Python (Pandas, Seaborn, Matplotlib)
* **Techniques Used:** Regex feature extraction, data unpivoting (Melt), categorical mapping, temporal trend analysis.

### Core Data Transformation
To enable time-series and categorical analysis, the raw 'wide' data was unpivoted into a 'long' format, and regex was used to extract sortable chronological periods.

```python
# 1. Feature Engineering: Extract numeric periods and years using Regex
df_2025['period'] = df_2025['time period'].str.extract(r'\(Period (\d+)\)').astype(int)
df_2025['year'] = df_2025['time period'].str.split(r' \(').str[0]

# 2. Data Reshaping: Unpivot columns into a single delay_cause feature
id_vars = ['train operating company name', 'period', 'year']
value_vars = [col for col in df_2025.columns if col not in id_vars]

df_unpivot = df_2025.melt(
    id_vars=id_vars,
    value_vars=value_vars,
    var_name='delay_cause',
    value_name='minutes'
)
