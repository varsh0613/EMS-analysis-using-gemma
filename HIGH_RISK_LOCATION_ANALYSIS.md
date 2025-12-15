# High-Risk Cases by Location Analysis

## Overview
Analysis of emergency medical services (EMS) incidents by geographic location to identify high-risk areas and response delays.

---

## Key Findings

### High-Risk Distribution by City (Top 5)
1. **San Rafael** - 6,694 high-risk cases (65.2% of city's total)
2. **Novato** - 4,763 high-risk cases (63.3% of city's total)
3. **Mill Valley** - 2,083 high-risk cases (65.8% of city's total)
4. **Larkspur** - 1,135 high-risk cases (67.6% of city's total)
5. **Sausalito** - 963 high-risk cases (67.7% of city's total)

**Total High-Risk Cases:** 21,232 out of 32,562 test cases (65.2%)

---

### County Distribution
- **Marin County** dominates with 20,917 high-risk cases (65.1% of Marin's 32,141 total)
- **MARIN** (separate entry) - 287 cases (74.2% high-risk rate)
- Other counties have minimal case volumes

---

## Response Time Delays in High-Risk Cases

### Cities with Most Concerning Delays (Avg Response Time)
1. **Fairfax** - 10.5 min average response time ⚠️
2. **San Anselmo** - 8.1 min average response time
3. **Larkspur** - 7.2 min average response time
4. **Tiburon** - 7.1 min average response time
5. **San Rafael** - 6.8 min average response time

### Other Delay Metrics (Top 10 Cities)
- **Turnout Time:** 0.7-1.0 minutes (generally acceptable)
- **On-Scene Time:** 1.6-2.5 minutes (generally acceptable)
- **Call Cycle Time:** 6.7-11.5 minutes

---

## Incident Type Breakdown

### San Rafael (Largest Volume)
1. Traumatic injury (15%)
2. Generalized Weakness (8%)
3. Abdominal Pain/Problems (7%)
4. Altered Level of Consciousness (7%)
5. Other (7%)

### Novato (Second Largest)
1. Traumatic injury (13%)
2. Other (12%)
3. Altered Level of Consciousness (7%)
4. Abdominal Pain/Problems (6%)
5. Syncope / Fainting (6%)

### Mill Valley
1. Traumatic injury (19%)
2. Altered Level of Consciousness (7%)
3. Other (6%)
4. Abdominal Pain/Problems (6%)
5. Generalized Weakness (5%)

---

## Actionable Insights

### Priority Areas
1. **Fairfax** - Highest response time delays (10.5 min avg) in high-risk cases
2. **San Anselmo** - High response times (8.1 min) with significant case volume
3. **San Rafael & Novato** - High volume areas requiring resource allocation

### Recommendations
1. **Increase Coverage in Fairfax** - Address response time delays
2. **Optimize Dispatch in High-Risk Cities** - San Rafael and Novato handle majority of cases
3. **Incident Type Focus** - Traumatic injuries dominate in high-risk cases
4. **Resource Allocation** - Deploy more units to San Rafael and Novato during peak hours

---

## Data Files Generated
- `high_risk_by_city.csv` - High-risk case counts and percentages by city
- `high_risk_by_county.csv` - High-risk case counts and percentages by county
- `high_risk_delays_by_city.csv` - Response time metrics for top 10 cities

---

## Dashboard Integration
These metrics are now visualized in the **Risk Analysis Dashboard** under:
- **High-Risk Cases by Location** section
- Three interactive charts showing:
  1. Top 10 Cities by High-Risk Cases (bar chart with percentages)
  2. High-Risk Cases by County (bar chart with percentages)
  3. Response Delays in High-Risk Cases by City (detailed table with all timing metrics)
