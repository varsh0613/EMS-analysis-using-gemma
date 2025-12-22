import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

async function apiGet(endpoint, fallback = null) {
  try {
    const res = await axios.get(`${API_BASE}${endpoint}`);
    return res.data;
  } catch (err) {
    console.error(`API ERROR → ${endpoint}:`, err);
    return fallback;
  }
}

// Dataset pagination
export const fetchDatasetPage = async (page = 1, limit = 25) =>
  apiGet(`/dataset?page=${page}&limit=${limit}`, { rows: [], total_rows: 0, page: 1, total_pages: 1 });

// Fetch EDA JSON outputs
export const fetchEdaJson = (filename) => apiGet(`/eda/${filename}`, []);

// Analytics endpoints
export const fetchPrimaryImpressionCounts = () => fetchEdaJson("primary_impression_top10.json");
export const fetchMonthlyTrends = () => fetchEdaJson("incident_trend_month.json");
export const fetchYearDistribution = () => fetchEdaJson("incident_trend_year.json");
export const fetchIncidentPlaces = () => fetchEdaJson("top_injury_places.json");
export const fetchAgeDistribution = () => fetchEdaJson("age_distribution.json");
export const fetchTransportDestinations = () => fetchEdaJson("top_destinations.json");
export const fetchKpis = () => fetchEdaJson("kpis.json");
export const fetchIncidentsPerDay = () => fetchEdaJson("incident_trend_day.json");
export const fetchCallsPerHour = () => fetchEdaJson("calls_per_hour.json");
export const fetchGenderDistribution = () => fetchEdaJson("gender_counts.json");
// ===============================
// OPERATIONAL EFFICIENCY API
// ===============================

export const fetchOpKpis = () => apiGet(`/op_efficiency/kpis.json`, {});
export const fetchOpTimeTrends = () => apiGet(`/op_efficiency/time_trends.json`, []);
export const fetchOpDistributions = () => apiGet(`/op_efficiency/distributions.json`, {});
export const fetchOpPercentiles = () => apiGet(`/op_efficiency/response_percentiles.json`, {});
export const fetchOpDelayBuckets = () => apiGet(`/op_efficiency/delay_buckets.json`, {});
export const fetchOpCitySummary = () => apiGet(`/op_efficiency/city_summary.json`, []);
export const fetchOpHourlyResponse = () => apiGet(`/op_efficiency/hourly_response.json`, []);
export const fetchOpPeakDelayHours = () => apiGet(`/op_efficiency/peak_delay_hours.json`, {});
export const fetchOpRiskByHour = () => apiGet(`/op_efficiency/risk_by_hour.json`, []);
export const fetchOpRiskByLocation = () => apiGet(`/op_efficiency/risk_by_location.json`, []);
export const fetchOpPeakRiskHours = () => apiGet(`/op_efficiency/peak_risk_hours.json`, {});

// ===============================
// GEO HOTSPOT API
// ===============================
export const fetchGeoHotspotTable = (top_n = 10) => apiGet(`/geo/hotspot_table?top_n=${top_n}`, { data: [] });

// ===============================
// RISK DASHBOARD API
// ===============================
// RISK dashboard endpoints
export const fetchRiskClusters = () => apiGet("/risk/cluster_embeddings.json", []);
export const fetchRiskTopProtocols = () => apiGet("/risk/top_protocols.json", []);
export const fetchRiskTopPrimaryImpressions = () => apiGet("/risk/top_primary_impressions.json", []);
export const fetchRiskLabelDistribution = () => apiGet("/risk/label_distribution.json", { HIGH: 0, MEDIUM: 0, LOW: 0 });

// optional
export const fetchRiskClusterSummaries = () => apiGet("/risk/cluster_summaries.json", {});
export const fetchRiskClusteredCSV = () => apiGet("/risk/clustered_data.csv", "");

// Model diagnostics
// - confusion matrix CSV (we will parse it on the client)
export const fetchConfusionMatrixCSV = async () => {
  try {
    const res = await axios.get(`${API_BASE}/risk/confusion_matrix.csv`);
    return res.data; // plain CSV text
  } catch (err) {
    console.error("API ERROR → /risk/confusion_matrix.csv:", err?.message);
    return null;
  }
};

export const fetchClassifierReportText = async () => {
  try {
    const res = await axios.get(`${API_BASE}/risk/classifier_report.txt`);
    return res.data; // plain text
  } catch (err) {
    console.error("API ERROR → /risk/classifier_report.txt:", err?.message);
    return null;
  }
};

export const fetchMisclassifiedCSV = async () => {
  try {
    const res = await axios.get(`${API_BASE}/risk/misclassified_samples.csv`);
    return res.data; // plain CSV text
  } catch (err) {
    console.error("API ERROR → /risk/misclassified_samples.csv:", err?.message);
    return null;
  }
};

// High-risk by location
export const fetchRiskHighRiskByCity = () => apiGet("/risk/high_risk_by_city.json", []);
export const fetchRiskHighRiskDelaysByCity = () => apiGet("/risk/high_risk_delays_by_city.json", []);