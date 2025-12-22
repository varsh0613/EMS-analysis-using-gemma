import pandas as pd
import os
import json

# ----------------------------
# Helper: Clean categories (remove ALL unknownish values)
# ----------------------------
def clean_top_categories(series, top_n=10):
    # Convert everything to string
    s = series.astype(str).fillna("unknown")

    # Normalize formatting
    s = s.str.strip().str.lower()

    # Comprehensive invalid patterns
    invalid_vals = {
        "unknown", "unk", "un", "not known", "n/a", "na",
        "nan", "none", "", " ", "-", "--", "null"
    }

    # Filter out invalids
    s = s[~s.isin(invalid_vals)]

    # Return top categories
    return s.value_counts().head(top_n).to_dict()


# ----------------------------
# Paths
# ----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "../eda/eda.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# Load dataset
# ----------------------------
df = pd.read_csv(DATA_PATH)
print(f"[INFO] Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")

# ----------------------------
# 1️⃣ KPI Cards
# ----------------------------
kpis = {
    "total_incidents": df["Incident_Number"].nunique() if "Incident_Number" in df.columns else None,
    "num_hospitals": df["Where_Patient_was_Transported"].nunique() if "Where_Patient_was_Transported" in df.columns else None,
    "num_primary_impressions": df["Primary_Impression"].nunique() if "Primary_Impression" in df.columns else None,
    "average_patient_age": float(df["Patient_Age"].mean()) if "Patient_Age" in df.columns else None,
    "most_common_injury_place": (
        clean_top_categories(df["Injury_Place"], top_n=1)
    )
}

with open(os.path.join(OUTPUT_DIR, "kpis.json"), "w") as f:
    json.dump(kpis, f, indent=4)
print("[INFO] KPI summary saved")

# ----------------------------
# 2️⃣ Patient Demographics
# ----------------------------

# Age distribution (dynamic bins)
if "Patient_Age" in df.columns:
    max_age = int(df["Patient_Age"].max())
    age_bins = list(range(0, max_age + 10, 10))
    age_dist = pd.cut(df["Patient_Age"], bins=age_bins).value_counts().sort_index()
    age_distribution = [{"bin": str(interval), "count": int(count)} for interval, count in age_dist.items()]

    with open(os.path.join(OUTPUT_DIR, "age_distribution.json"), "w") as f:
        json.dump(age_distribution, f, indent=4)

    print("[INFO] Age distribution saved")

# Gender counts
if "Patient_Gender" in df.columns:
    gender_counts = clean_top_categories(df["Patient_Gender"], top_n=50)
    gender_counts_json = [{"feature": k, "value": int(v)} for k, v in gender_counts.items()]

    with open(os.path.join(OUTPUT_DIR, "gender_counts.json"), "w") as f:
        json.dump(gender_counts_json, f, indent=4)

    print("[INFO] Gender counts saved")

# Primary Impression counts (top 10)
if "Primary_Impression" in df.columns:
    top_impressions = clean_top_categories(df["Primary_Impression"], top_n=10)
    top_impressions_json = [{"feature": k, "value": int(v)} for k, v in top_impressions.items()]

    with open(os.path.join(OUTPUT_DIR, "primary_impression_top10.json"), "w") as f:
        json.dump(top_impressions_json, f, indent=4)

    print("[INFO] Primary Impression top 10 saved")

# Transport Destinations (top 10)
if "Where_Patient_was_Transported" in df.columns:
    top_destinations = clean_top_categories(df["Where_Patient_was_Transported"], top_n=10)
    top_destinations_json = [{"feature": k, "value": int(v)} for k, v in top_destinations.items()]

    with open(os.path.join(OUTPUT_DIR, "top_destinations.json"), "w") as f:
        json.dump(top_destinations_json, f, indent=4)

    print("[INFO] Top transport destinations saved")

# ----------------------------
# 3️⃣ Incident / Call Trends
# ----------------------------

# Per year
if "Year_Call_Received" in df.columns:
    incident_trend_year = df.groupby("Year_Call_Received").size().reset_index(name="count")
    incident_trend_year_json = [
        {"year": int(row["Year_Call_Received"]), "count": int(row["count"])}
        for _, row in incident_trend_year.iterrows()
    ]

    with open(os.path.join(OUTPUT_DIR, "incident_trend_year.json"), "w") as f:
        json.dump(incident_trend_year_json, f, indent=4)

    print("[INFO] Incident trend per year saved")

# Per month
if "Month_Call_Received" in df.columns:
    month_mapping = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    df["Month_Num"] = df["Month_Call_Received"]
    if df["Month_Call_Received"].dtype == object:
        df["Month_Num"] = df["Month_Call_Received"].map(month_mapping)

    incident_trend_month = df.groupby("Month_Num").size().reset_index(name="count")
    incident_trend_month_json = [
        {"month": int(row["Month_Num"]), "count": int(row["count"])}
        for _, row in incident_trend_month.iterrows()
    ]

    with open(os.path.join(OUTPUT_DIR, "incident_trend_month.json"), "w") as f:
        json.dump(incident_trend_month_json, f, indent=4)

    print("[INFO] Incident trend per month saved")

# Per weekday
if "Time_Call_Was_Received" in df.columns:
    df["Time_Call_Was_Received"] = pd.to_datetime(df["Time_Call_Was_Received"], errors="coerce")
    df["day_of_week"] = df["Time_Call_Was_Received"].dt.day_name()

    incident_trend_dow = df.groupby("day_of_week").size().reset_index(name="count")
    incident_trend_dow_json = [
        {"day": row["day_of_week"], "count": int(row["count"])}
        for _, row in incident_trend_dow.iterrows()
    ]

    with open(os.path.join(OUTPUT_DIR, "incident_trend_day.json"), "w") as f:
        json.dump(incident_trend_dow_json, f, indent=4)

    print("[INFO] Incident trend per day of week saved")

# Per hour
if "Time_Call_Was_Received" in df.columns:
    df["hour"] = df["Time_Call_Was_Received"].dt.hour
    calls_per_hour = df.groupby("hour").size().reset_index(name="count")
    calls_per_hour_json = [
        {"hour": int(row["hour"]), "count": int(row["count"])}
        for _, row in calls_per_hour.iterrows()
    ]

    with open(os.path.join(OUTPUT_DIR, "calls_per_hour.json"), "w") as f:
        json.dump(calls_per_hour_json, f, indent=4)

    print("[INFO] Calls per hour saved")

# ----------------------------
# 4️⃣ Incident Locations
# ----------------------------
if "Injury_Place" in df.columns:
    top_places = clean_top_categories(df["Injury_Place"], top_n=10)
    top_places_json = [{"feature": k, "value": int(v)} for k, v in top_places.items()]

    with open(os.path.join(OUTPUT_DIR, "top_injury_places.json"), "w") as f:
        json.dump(top_places_json, f, indent=4)

    print("[INFO] Top injury places saved")

# ----------------------------
# 5️⃣ Numeric Summary
# ----------------------------
numeric_cols = df.select_dtypes(include="number").columns
numeric_summary = df[numeric_cols].describe().to_dict()
numeric_summary_clean = {
    col: {stat: float(val) for stat, val in stats.items()}
    for col, stats in numeric_summary.items()
}

with open(os.path.join(OUTPUT_DIR, "numeric_summary.json"), "w") as f:
    json.dump(numeric_summary_clean, f, indent=4)

print("[INFO] Numeric summary saved")
print("[INFO] EDA outputs completed!")






