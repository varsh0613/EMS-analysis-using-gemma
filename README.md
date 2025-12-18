# EMS Analysis Using Gemma - High-Risk Location Analysis

## 1. Problem

Emergency Medical Services (EMS) response times are critical in determining patient outcomes. Geographic variations in high-risk case distribution and response delays can lead to unequal care quality across regions. This analysis identifies which locations have the highest concentrations of high-risk incidents and experience the longest response delays, enabling targeted resource allocation and operational improvements.

**Key Challenge:** 65.2% of all EMS cases are classified as high-risk, with significant geographic clustering in specific cities and uneven response times across locations.

---

## 2. Data

**Dataset:** Emergency Medical Services incident records from Marin County

**Data Scope:**
- **Total Cases Analyzed:** 32,562 test cases
- **High-Risk Cases:** 21,232 (65.2%)
- **Geographic Coverage:** Marin County with focus on individual cities
- **Key Attributes:** Case location (city/county), incident type, response times (turnout, on-scene, call cycle), risk classification

**Data Sources Generated:**
- `high_risk_by_city.csv` - High-risk case counts and percentages by city
- `high_risk_by_county.csv` - High-risk case counts and percentages by county
- `high_risk_delays_by_city.csv` - Response time metrics for top cities

---

## 3. Methods

**Analysis Approach:**

1. **Geographic Aggregation:** Grouped EMS incidents by city and county to identify high-risk concentrations
2. **Response Time Analysis:** Calculated average response metrics including turnout time, on-scene time, and call cycle time
3. **Incident Type Classification:** Categorized incidents by type to understand case composition in high-risk areas
4. **Ranking & Prioritization:** Ranked cities by high-risk case volume and response delays to identify priority areas

**Metrics Calculated:**
- High-risk case count and percentage by location
- Average response time, turnout time, on-scene time, and call cycle time
- Incident type distribution in high-risk cases

---

## 4. Output

**High-Risk Distribution (Top 5 Cities):**
1. San Rafael - 6,694 cases (65.2%)
2. Novato - 4,763 cases (63.3%)
3. Mill Valley - 2,083 cases (65.8%)
4. Larkspur - 1,135 cases (67.6%)
5. Sausalito - 963 cases (67.7%)

**Response Time Concerns (Top 5):**
1. Fairfax - 10.5 min average response time ⚠️
2. San Anselmo - 8.1 min average response time
3. Larkspur - 7.2 min average response time
4. Tiburon - 7.1 min average response time
5. San Rafael - 6.8 min average response time

**County Snapshot:**
- Marin County: 20,917 high-risk cases (65.1% of 32,141 total)

**Incident Types in High-Risk Cases:**
- Traumatic injuries (13-19% across cities)
- Altered Level of Consciousness (6-7%)
- Abdominal Pain/Problems (6-7%)
- Generalized Weakness (5-8%)

---

## 5. Impact

**Operational Improvements:**
- Identifies resource-constrained areas requiring additional EMS coverage
- Highlights response time inefficiencies in specific locations (Fairfax, San Anselmo)
- Enables targeted deployment strategies for peak-hour demand in high-volume cities (San Rafael, Novato)

**Patient Care Outcomes:**
- Reducing response delays in Fairfax (currently 10.5 min) can significantly improve survival rates for time-critical incidents
- Optimizing dispatch in high-risk areas addresses 65.2% of all emergency calls
- Incident type insights enable specialized training and equipment pre-positioning

**Strategic Value:**
- Data-driven basis for budget allocation across EMS stations
- Performance benchmarking across locations
- Foundation for predictive resource planning and response optimization

---

## 6. Tech Stack

**Data Processing & Analysis:**
- **Python 3.x** - Primary analysis language
- **Pandas** - Data manipulation and aggregation
- **NumPy** - Numerical computations

**Visualization & Dashboard:**
- **React** - Frontend framework for interactive dashboard
- **JavaScript** - Dashboard scripting
- **Chart libraries** - Interactive visualizations (bar charts, tables)

**Backend & Infrastructure:**
- **Python Flask/FastAPI** - RESTful API backend
- **CSV Export** - Data output format for analysis results

**Development Tools:**
- **Git** - Version control
- **Jupyter Notebook** - Exploratory data analysis and documentation

---

## Dashboard Integration

Results are visualized in the **Risk Analysis Dashboard** with three interactive components:
1. Top 10 Cities by High-Risk Cases (bar chart with percentages)
2. High-Risk Cases by County (bar chart with percentages)
3. Response Delays in High-Risk Cases by City (detailed table with timing metrics)
<video controls src="Screen Recording 2025-12-16 160202.mp4" title="dashboard demo"></video>
