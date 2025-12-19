# EMS Analysis Using Gemma

A comprehensive Emergency Medical Services (EMS) incident analysis system combining geospatial hotspot detection, operational efficiency metrics, and machine learning-based risk classification.

<video controls src="https://github.com/varsh0613/EMS-analysis-using-gemma/assets/YOUR_ASSET_ID/Screen%20Recording%202025-12-16%20160202%20(1).mp4" title="Dashboard demo"></video>

---

## Project Overview

This project implements an intelligent EMS analytics platform that identifies high-risk geographic locations, analyzes operational efficiency bottlenecks, and classifies incidents by risk severity using machine learning and LLM-powered insights.

---

# Analysis 1: Geospatial Hotspot Analysis

## 1. Problem

Geographic clustering of EMS incidents can indicate areas with higher emergency densities, demographic factors, or infrastructure challenges. Understanding where high-volume incidents occur is essential for strategic EMS resource positioning, coverage planning, and response time optimization.

**Key Challenge:** Identifying incident hotspots at city and sub-city (hexagon) levels to enable targeted station placement and dispatch strategies.

## 2. Data

**Dataset:** 32,562+ EMS incidents with geographic coordinates
- **Location Fields:** Incident_Latitude, Incident_Longitude, Incident_City, Incident_County
- **Time Fields:** Time_Call_Was_Received, Time_Arrived_on_Scene, Time_Departed_from_the_Scene
- **Clinical Fields:** Primary_Impression, Protocol_Used_by_EMS_Personnel, Patient_Age, Patient_Gender

**Geospatial Structure:**
- H3 hierarchical hexagon grid (resolution 8) for uniform spatial binning
- Polygon-based geographic representation for mapping and analysis

## 3. Methods

**Geospatial Processing Pipeline:**

1. **H3 Hexagon Grid Mapping:** Assigned each incident to a Hexagon at resolution 8 (~1.2 km cells)
2. **Aggregation by Hex Cell:** Grouped incidents and computed per-cell statistics
3. **On-Scene Time Calculation:** Computed duration from arrival to departure with validation (0-200 min bounds)
4. **Geometry Extraction:** Generated polygon boundaries for each H3 cell for map visualization
5. **Output Formats:** Generated both CSV (tabular) and GeoJSON (geographic) outputs

**Technologies:**
- H3 hierarchical spatial indexing (Python h3 library)
- GeoPandas for geographic data handling
- Shapely for polygon geometry

## 4. Output

**Hotspot Data Files:**
- `incidents_with_h3.csv` - 32,562+ rows with H3 hexagon assignment per incident
- `h3_hex_summary.csv` - Aggregated metrics by hexagon cell
- `h3_hex_summary.geojson` - Geographic visualization ready format

**Hex-Level Metrics:**
- Incident count per hexagon
- Average on-scene time (mean, min, max)
- Spatial clustering identification
- Geographic boundaries for each hotspot area

**Key Findings:**
- High-incident density clusters identified in San Rafael, Novato, and Mill Valley areas
- On-scene times vary by geography (2-4 min average)
- Hexagon-level granularity enables precise resource allocation

## 5. Impact

- **Station Placement:** Data-driven location selection for new EMS stations
- **Coverage Analysis:** Identify underserved geographic areas with long response distances
- **Demand Forecasting:** Predict high-demand periods by location for staffing optimization
- **Dashboard Integration:** Interactive maps showing incident hotspots for operational decision-making

## 6. Tech Stack

- **Data Processing:** Python, Pandas, NumPy
- **Geospatial:** H3 hexagon library, GeoPandas, Shapely
- **Visualization:** GeoJSON export for Leaflet/Mapbox mapping
- **Output Formats:** CSV, GeoJSON

---

# Analysis 2: Operational Efficiency Analysis

## 1. Problem

EMS operational delays stem from multiple sources: dispatch time, turnout time, response time, and on-scene duration. Understanding these time components reveals bottlenecks and enables targeted improvements in dispatch protocols, staffing, and scene management. Different hours, cities, and incident types experience varying efficiency levels.

**Key Challenge:** Identify which operational components and time periods drive delays, enabling targeted optimization.

## 2. Data

**Dataset:** 32,562 EMS incidents with full timing pipeline
- **Timing Fields:** Time_Call_Was_Received, Time_Vehicle_was_Dispatched, Time_Arrived_on_Scene, Time_Departed_from_the_Scene
- **Location Fields:** Incident_City, Incident_County
- **Incident Fields:** Primary_Impression, Protocol_Used_by_EMS_Personnel, Patient_Age, Patient_Gender
- **Incident Number:** Unique incident identifier

**Time Metrics Derived:**
- Turnout time (dispatch to departure from station)
- Response time (dispatch to arrival on scene)
- On-scene time (arrival to departure from scene)
- Call cycle time (initial call to final departure)

## 3. Methods

**Operational Efficiency Pipeline:**

1. **Time Parsing:** Converted timestamp fields to datetime format with error handling
2. **Time Interval Calculation:** Computed four core timing metrics with validation (0-300 min bounds)
3. **Aggregation by Dimension:** Grouped by hour-of-day, city, and county
4. **KPI Computation:** Calculated averages, percentiles (P50, P75, P90, P95), and SLA compliance
5. **Delay Analysis:** Identified incidents exceeding 8-minute response SLA, categorized delay buckets
6. **Peak Hour Detection:** Ranked hours by delayed incident count
7. **Distribution Analysis:** Generated histograms and capped arrays for visualization

**Metrics Computed:**
- Average and percentile response times (P50, P75, P90, P95, max)
- Average turnout time, on-scene time, call cycle time
- SLA compliance (% calls ≤ 8 min response)
- Calls per day, busiest hour, busiest city
- Delay distribution (0-5, 5-10, 10-15, 15-30, 30+ min late)

## 4. Output

**Operational Metrics (JSON format):**
- `kpis.json` - High-level KPIs (avg response time, P90, compliance %, busiest locations)
- `time_trends.json` - Daily/monthly trends in response times
- `distributions.json` - Histograms of response, on-scene, and cycle times
- `response_percentiles.json` - P50, P75, P90, P95, max response times
- `delay_buckets.json` - Count of incidents in each delay category
- `city_summary.json` - Per-city metrics (incident count, avg response, P90 response, turnout)
- `hourly_response.json` - Hour-by-hour response times and peak delay identification
- `peak_delay_hours.json` - Ranked hours by delayed incident count

**Key Findings:**
- Average response time: 3-6 min across most cities
- Response delays in Fairfax average 10.5 min (concerning)
- Peak delays occur in afternoon/evening hours (14:00-18:00)
- San Rafael and Novato handle 65%+ of incident volume

## 5. Impact

- **Protocol Optimization:** Identify bottlenecks in turnout, dispatch, and scene management
- **Staffing Planning:** Peak hours show 2-3x delayed incidents vs. baseline
- **SLA Improvement:** Target cities below 8-min SLA compliance with additional resources
- **Performance Benchmarking:** Compare inter-city efficiency and identify best practices
- **Alert System:** Real-time peak delay hour detection for dynamic resource allocation

## 6. Tech Stack

- **Data Processing:** Python, Pandas, NumPy
- **Numerical Computation:** NumPy percentiles and histograms
- **Output Format:** JSON (structured metrics for dashboard)
- **Libraries:** Pathlib for cross-platform file handling

---

# Analysis 3: Risk Classification Analysis

## 1. Problem

EMS incidents vary widely in clinical severity, operational complexity, and resource requirements. Automated risk classification enables intelligent prioritization, dispatch routing, and scene preparation. Manual triage is subjective; machine learning provides consistent, evidence-based risk scoring across incident types.

**Key Challenge:** Classify 32,562 incidents into LOW/MEDIUM/HIGH risk categories using medical impression text, protocols, patient age, and operational features, achieving high accuracy on diverse incident types.

## 2. Data

**Dataset:** 32,562 EMS incidents with clinical and operational features
- **Clinical Fields:** Primary_Impression (text), Protocol_Used_by_EMS_Personnel (text), Patient_Age, Patient_Gender
- **Operational Fields:** response_time_min, turnout_time_min, call_cycle_time_min, on_scene_time_min
- **Location:** Incident_County
- **Demographics:** Patient age categorized as infant/child/teen/adult/elderly

**Medical Text Processing:**
- Merged Primary_Impression + Protocol_Used_by_EMS_Personnel + age_group into unified medical text field
- Vectorized using TF-IDF with 8000 features (unigrams + bigrams)

## 3. Methods

**Risk Classification Pipeline:**

1. **Medical Text Preparation:** Concatenated and normalized clinical impression, protocol, and patient age group
2. **Initial Clustering:** Applied K-Means (n_clusters=30) on TF-IDF vectors to discover natural incident groupings
3. **Cluster Sampling:** Sampled 30 incidents per cluster to reduce LLM processing
4. **LLM Summarization:** Used Gemma 7B to summarize cluster characteristics and identify patterns
5. **Automated Labeling:** Applied keyword-based extraction on LLM summaries to assign LOW/MEDIUM/HIGH labels
   - **HIGH:** cardiac arrest, life-threatening, severe, airway, unconscious, seizure, DOA, expired
   - **LOW:** low risk, minor, no injury, nosebleed, public assist, non-traumatic
   - **MEDIUM:** moderate, stable, requires transport, hospital care (default if ambiguous)
6. **Stratified Train-Test Split:** 70% train / 30% test (stratified to maintain class proportions)
7. **Classifier Training:** LightGBM multiclass classifier on combined features:
   - Numeric features: response time, turnout time, call cycle time, on-scene time
   - Medical text: TF-IDF vectors (500 features)
   - Categorical features: Patient_Gender, Incident_County, Primary_Impression (one-hot encoded)
8. **Evaluation:** Classification report, confusion matrix, and misclassified sample analysis

**Technologies:**
- K-Means clustering (scikit-learn)
- TF-IDF vectorization (scikit-learn)
- LightGBM gradient boosting classifier
- Gemma 7B LLM for semantic understanding
- One-hot encoding for categorical features

## 4. Output

**Risk Classification Artifacts:**
- `cluster_summaries.json` - LLM summaries of each cluster's characteristics
- `cluster_diagnostics.json` - Cluster-to-label mapping with example incidents
- `train_set.csv` - 70% of data with assigned risk labels (for model training)
- `test_set.csv` - 30% held-out test set with assigned risk labels
- `classifier_model.joblib` - Trained LightGBM model (3-class prediction)
- `tfidf_vectorizer.joblib` - Fitted TF-IDF for clustering
- `tfidf_classifier.joblib` - Fitted TF-IDF for classifier features
- `kmeans_model.joblib` - Fitted K-Means clustering model
- `classifier_report.txt` - Precision, recall, F1 by class + confusion matrix
- `confusion_matrix.csv` - Detailed misclassification breakdown
- `misclassified_samples.csv` - 500+ incidents with incorrect predictions (for analysis)

**Classification Metrics:**
- Precision, recall, F1-score per class (LOW/MEDIUM/HIGH)
- Overall accuracy on held-out test set
- Confusion matrix analysis
- Feature importance (LightGBM)

## 5. Impact

- **Intelligent Dispatch:** Route high-risk incidents to closest advanced life support (ALS) units
- **Scene Preparation:** Pre-position specialized equipment (cardiac monitors, airway supplies) based on predicted risk
- **Resource Optimization:** Allocate paramedic units to HIGH-risk areas during peak periods
- **Training Data:** Labeled dataset enables continuous model improvement
- **Risk Trending:** Track incident risk distribution over time to identify emerging patterns
- **Clinical Insights:** Understand which medical presentations are most challenging operationally

## 6. Tech Stack

- **Data Processing:** Python, Pandas, NumPy
- **Text Processing:** Scikit-learn TF-IDF, Sklearn preprocessing
- **Clustering:** K-Means (scikit-learn)
- **ML Model:** LightGBM (gradient boosting)
- **LLM:** Gemma 7B (Ollama API)
- **Model Persistence:** Joblib for serialization
- **Evaluation:** scikit-learn classification_report, confusion_matrix

---

# EMS Intelligence Chatbot (Gemma 7B)

## Overview

A multi-modal conversational assistant powered by Gemma 7B LLM that provides intelligent responses across three domains:
1. **Data Analysis Mode** - Query insights from EMS datasets and visualizations
2. **Operational Mode** - EMS protocols, severity assessment, dispatch recommendations
3. **General Chat** - Conversational assistance

## Features

- **Automatic Mode Detection:** Interprets user intent from keywords (dataset, protocol, patient, risk, etc.)
- **Data Analysis:** Discusses clusters, predictions, model performance, geospatial patterns
- **EMS Operational:** Provides severity classification (LOW/MEDIUM/HIGH), scene observations, dispatch priorities
- **Fast & Accurate:** <5-8 second response times with configurable temperature for hallucination control
- **Robust Error Handling:** Retry logic, graceful degradation, session management

## Technical Stack

- **Model:** Gemma 7B-instruct (Ollama)
- **API Communication:** HTTP POST to Ollama chat endpoint
- **Request Framework:** Python requests library
- **Parameters:** Configurable temperature (0.2), top_p (0.85), context window (4096 tokens), max output (2048 tokens)
- **Features:** Automatic system prompt switching, retry with exponential backoff

## How It Answers

**Data/Analysis Questions:**
```
User: "What are the top 3 cities by high-risk cases?"
Chatbot: Retrieves cluster_summaries.json, references geospatial output, provides statistics
```

**EMS Operational Questions:**
```
User: "Unresponsive patient, no vital signs"
Chatbot: Operational severity → HIGH, recommends ALS protocols, dispatch priority instructions
```

**General Questions:**
```
User: "What's the weather today?"
Chatbot: General conversational response
```

---

# Dashboard Integration

All three analyses feed into an interactive **React-based Risk Analysis Dashboard**:

1. **Geospatial Hotspot Map** - Interactive map showing incident density by hexagon
2. **Operational Efficiency Charts** - KPIs, time trends, peak hours, delay distribution
3. **Risk Distribution** - LOW/MEDIUM/HIGH incident breakdown by location and time
4. **City Comparison** - Bench-marking across geographic regions
5. **Chatbot Interface** - Ask questions about data, operations, and predictions

---

# File Structure

```
gemma/
├── backend/
│   ├── llm_client.py          # Gemma 7B chatbot client
│   └── ...
├── geospatial/
│   ├── geospatial_engine.py   # H3 hotspot analysis
│   ├── incidents_with_h3.csv
│   └── h3_hex_summary.geojson
├── op_efficiency/
│   ├── op_efficiency_pipeline.py  # Operational metrics
│   └── outputs/
│       ├── kpis.json
│       ├── time_trends.json
│       ├── delay_buckets.json
│       └── ...
├── risk_score/
│   ├── risk_score_pipeline.py     # Risk classification
│   ├── llm_client.py
│   └── outputs/
│       ├── classifier_model.joblib
│       ├── train_set.csv
│       ├── test_set.csv
│       ├── confusion_matrix.csv
│       └── ...
├── dashboard-react/           # Interactive dashboard UI
├── eda/                       # Exploratory data analysis
└── README.md                  # This file
```

---

# Tech Stack Summary

**Languages & Frameworks:**
- Python 3.x (data processing, ML, LLM)
- React (dashboard frontend)
- JavaScript (dashboard scripting)

**Data Processing:**
- Pandas, NumPy (data manipulation)
- Scikit-learn (TF-IDF, preprocessing, metrics)
- Joblib (model persistence)

**Machine Learning:**
- K-Means (clustering)
- LightGBM (classification)
- TF-IDF vectorization

**Geospatial:**
- H3 library (hexagon indexing)
- GeoPandas (geographic data)
- Shapely (polygon geometry)

**LLM:**
- Gemma 7B-instruct (Ollama API)
- Requests (HTTP communication)

**Visualization:**
- GeoJSON (geographic data format)
- React interactive charts
- Leaflet/Mapbox (mapping)

**Output Formats:**
- CSV (tabular data)
- JSON (structured metrics)
- GeoJSON (geographic features)

---

# Quick Start

1. **Data Preparation:**
   ```bash
   python eda/explore.py  # Generate eda.csv
   ```

2. **Run Analyses:**
   ```bash
   python geospatial/geospatial_engine.py     # Hotspot analysis
   python op_efficiency/op_efficiency_pipeline.py  # Operational metrics
   python risk_score/risk_score_pipeline.py   # Risk classification
   ```

3. **Start Chatbot:**
   ```bash
   # Ensure Ollama is running with Gemma 7B
   python backend/llm_client.py
   ```

4. **Launch Dashboard:**
   ```bash
   cd dashboard-react
   npm install && npm start
   ```

---

# Key Insights

- **65.2%** of EMS incidents classified as high-risk
- **San Rafael & Novato** account for 50%+ of incident volume
- **Fairfax** experiences longest response delays (10.5 min avg)
- **Afternoon hours (14-18:00)** show 2-3x delayed incidents
- **LightGBM classifier** achieves 80%+ accuracy on stratified test set
- **30 incident clusters** identified with distinct operational characteristics

