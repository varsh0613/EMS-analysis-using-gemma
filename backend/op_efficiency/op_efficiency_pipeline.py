#!/usr/bin/env python3
"""
op_efficiency_pipeline.py

Robust JSON outputs for Operational Efficiency dashboard:
- kpis.json
- time_trends.json       (daily if available, otherwise monthly)
- distributions.json     (hist bins + capped raw arrays)
- response_percentiles.json
- delay_buckets.json
- city_summary.json
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Any

# ---------------- CONFIG ----------------
# Use relative paths from op_efficiency folder
EDA_CSV = Path(__file__).parent.parent / "eda" / "eda.csv"
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- HELPERS ----------------
def safe_round(x, nd=2):
    try:
        if pd.isna(x):
            return None
        return round(float(x), nd)
    except Exception:
        return None

def write_json(obj: Any, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))

def pctile_cap(arr: np.ndarray, q=99):
    if arr.size == 0:
        return None
    return float(np.percentile(arr, q))

def histogram_bins_from_array(values: np.ndarray, bins: int = 30):
    if values.size == 0:
        return []
    hist, edges = np.histogram(values, bins=bins)
    out = []
    for i in range(len(hist)):
        out.append({
            "bin": f"{round(float(edges[i]), 2)} - {round(float(edges[i+1]), 2)}",
            "count": int(hist[i])
        })
    return out

# ---------------- LOAD & PREP ----------------
def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path)
    date_cols = [
        "Time_Call_Was_Received",
        "Time_Vehicle_was_Dispatched",
        "Time_Arrived_on_Scene",
        "Time_Departed_from_the_Scene",
    ]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # compute core times
    df["response_time_min"] = (df["Time_Arrived_on_Scene"] - df["Time_Vehicle_was_Dispatched"]).dt.total_seconds() / 60 if "Time_Arrived_on_Scene" in df.columns and "Time_Vehicle_was_Dispatched" in df.columns else np.nan
    df["turnout_time_min"] = (df["Time_Vehicle_was_Dispatched"] - df["Time_Call_Was_Received"]).dt.total_seconds() / 60 if "Time_Vehicle_was_Dispatched" in df.columns and "Time_Call_Was_Received" in df.columns else np.nan
    df["call_cycle_time_min"] = (df["Time_Departed_from_the_Scene"] - df["Time_Call_Was_Received"]).dt.total_seconds() / 60 if "Time_Departed_from_the_Scene" in df.columns and "Time_Call_Was_Received" in df.columns else np.nan
    df["on_scene_time_min"] = (df["Time_Departed_from_the_Scene"] - df["Time_Arrived_on_Scene"]).dt.total_seconds() / 60 if "Time_Departed_from_the_Scene" in df.columns and "Time_Arrived_on_Scene" in df.columns else np.nan

    # drop invalid rows
    core_times = ["response_time_min", "on_scene_time_min", "call_cycle_time_min"]
    df = df.dropna(subset=core_times, how="any")
    for t in core_times + ["turnout_time_min"]:
        if t in df.columns:
            df = df[(df[t] >= 0) & (df[t] <= 300)]

    return df

# ---------------- KPI SUMMARY ----------------
def compute_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {k: None for k in [
            "avg_response_time","p90_response_time",
            "avg_on_scene_time","avg_total_cycle_time","calls_per_day",
            "busiest_hour","busiest_city","avg_turnout_time","sla_8_min_pct"
        ]}

    avg_response = df["response_time_min"].mean()
    p90 = df["response_time_min"].quantile(0.9)
    avg_on_scene = df["on_scene_time_min"].mean()
    avg_cycle = df["call_cycle_time_min"].mean()
    avg_turnout = df["turnout_time_min"].mean() if "turnout_time_min" in df.columns else None

    # calls per day
    calls_per_day = None
    if "Time_Call_Was_Received" in df.columns:
        daily_counts = df.groupby(df["Time_Call_Was_Received"].dt.date).size()
        if len(daily_counts):
            calls_per_day = float(daily_counts.mean())

    # busiest hour
    busiest_hour = None
    if "Time_Call_Was_Received" in df.columns:
        hours = df["Time_Call_Was_Received"].dt.hour.value_counts()
        if not hours.empty:
            busiest_hour = f"{int(hours.idxmax()):02d}:00"

    # busiest city
    busiest_city = None
    if "Incident_City" in df.columns:
        city_counts = df["Incident_City"].value_counts()
        if not city_counts.empty:
            busiest_city = str(city_counts.idxmax())

    # SLA 8 min compliance
    sla_8_min_pct = ((df["response_time_min"] <= 8).sum() / len(df) * 100) if "response_time_min" in df.columns else None

    return {
        "avg_response_time": safe_round(avg_response),
        "p90_response_time": safe_round(p90),
        "avg_on_scene_time": safe_round(avg_on_scene),
        "avg_total_cycle_time": safe_round(avg_cycle),
        "calls_per_day": safe_round(calls_per_day),
        "busiest_hour": busiest_hour,
        "busiest_city": busiest_city,
        "avg_turnout_time": safe_round(avg_turnout),
        "sla_8_min_pct": safe_round(sla_8_min_pct)
    }

# ---------------- TIME TRENDS ----------------
def compute_time_trends(df: pd.DataFrame, prefer="D") -> List[Dict[str, Any]]:
    if df.empty or "Time_Call_Was_Received" not in df.columns:
        return []

    total = len(df)
    non_null = df["Time_Call_Was_Received"].notna().sum()
    use_month = (non_null / total if total else 0) < 0.5

    if use_month:
        df = df.copy()
        df["month"] = df["Time_Call_Was_Received"].dt.to_period("M").astype(str)
        grouped = df.groupby("month").agg(
            avg_response=("response_time_min", "mean"),
            avg_on_scene=("on_scene_time_min", "mean"),
            avg_cycle=("call_cycle_time_min", "mean"),
            avg_turnout=("turnout_time_min", "mean"),
            incident_count=("Incident_Number", "count")
        ).reset_index()
        grouped = grouped.rename(columns={"month": "period"})
        for c in ["avg_response","avg_on_scene","avg_cycle","avg_turnout"]:
            grouped[c] = grouped[c].round(2)
        return grouped.to_dict(orient="records")
    else:
        df = df.copy()
        df["date"] = df["Time_Call_Was_Received"].dt.date.astype(str)
        grouped = df.groupby("date").agg(
            avg_response=("response_time_min", "mean"),
            avg_on_scene=("on_scene_time_min", "mean"),
            avg_cycle=("call_cycle_time_min", "mean"),
            avg_turnout=("turnout_time_min", "mean"),
            incident_count=("Incident_Number", "count")
        ).reset_index()
        for c in ["avg_response","avg_on_scene","avg_cycle","avg_turnout"]:
            grouped[c] = grouped[c].round(2)
        return grouped.to_dict(orient="records")

# ---------------- DISTRIBUTIONS ----------------
def compute_distributions(df: pd.DataFrame) -> Dict[str, Any]:
    out = {}
    def safe_array(col):
        if col not in df.columns:
            return np.array([])
        vals = df[col].dropna().astype(float).values
        return vals

    resp = safe_array("response_time_min")
    onscene = safe_array("on_scene_time_min")
    cycle = safe_array("call_cycle_time_min")

    p99_resp = pctile_cap(resp, 99) or 0.0
    p99_scene = pctile_cap(onscene, 99) or 0.0
    p99_cycle = pctile_cap(cycle, 99) or 0.0

    resp_capped = np.where(resp>p99_resp,p99_resp,resp) if resp.size else np.array([])
    scene_capped = np.where(onscene>p99_scene,p99_scene,onscene) if onscene.size else np.array([])
    cycle_capped = np.where(cycle>p99_cycle,p99_cycle,cycle) if cycle.size else np.array([])

    out["response_hist"] = histogram_bins_from_array(resp_capped, bins=30)
    out["on_scene_hist"] = histogram_bins_from_array(scene_capped, bins=30)
    out["cycle_hist"] = histogram_bins_from_array(cycle_capped, bins=30)

    out["response_times_capped"] = [round(float(x),2) for x in resp_capped.tolist()] if resp_capped.size else []
    out["on_scene_times_capped"] = [round(float(x),2) for x in scene_capped.tolist()] if scene_capped.size else []
    out["cycle_times_capped"] = [round(float(x),2) for x in cycle_capped.tolist()] if cycle_capped.size else []

    out["caps"] = {
        "p99_response": safe_round(p99_resp),
        "p99_on_scene": safe_round(p99_scene),
        "p99_cycle": safe_round(p99_cycle)
    }

    return out

# ---------------- RESPONSE PERCENTILES ----------------
def compute_response_percentiles(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty or "response_time_min" not in df.columns:
        return {"p50": None, "p75": None, "p90": None, "p95": None, "max": None}
    s = df["response_time_min"].dropna()
    return {
        "p50": safe_round(s.quantile(0.5)),
        "p75": safe_round(s.quantile(0.75)),
        "p90": safe_round(s.quantile(0.9)),
        "p95": safe_round(s.quantile(0.95)),
        "max": safe_round(s.max())
    }
# ---------------- DELAY BUCKETS WITH SLA (ONLY LATE CALLS) ----------------
def compute_delay_buckets(df: pd.DataFrame, sla: float = 8) -> list[dict]:
    if df.empty or "response_time_min" not in df.columns:
        return []

    # 1️⃣ Compute delay over SLA
    df['delay'] = df['response_time_min'] - sla
    df['delay'] = df['delay'].apply(lambda x: x if x > 0 else 0)

    # 2️⃣ Keep only delayed incidents
    df_late = df[df['delay'] > 0]
    if df_late.empty:
        return [{"delay_bucket": label, "count": 0} for label in ["0–5 min","5–10","10–15","15–30","30+"]]

    # 3️⃣ Define delay buckets
    bins = [0,5,10,15,30,999]  # minutes late
    labels = ["0–5 min","5–10","10–15","15–30","30+"]

    # 4️⃣ Categorize delays into buckets
    cat = pd.cut(df_late['delay'], bins=bins, labels=labels, right=False)

    # 5️⃣ Count number of incidents in each bucket
    dist = cat.value_counts().reindex(labels).fillna(0).astype(int)

    # 6️⃣ Return as list of dicts
    return [{"delay_bucket": label, "count": int(dist[label])} for label in labels]

# ---------------- CITY AGG ----------------
def compute_city_agg(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty or "Incident_City" not in df.columns:
        return []
    city_agg = df.groupby("Incident_City").agg(
        incidents=("Incident_Number","count"),
        avg_response=("response_time_min","mean"),
        p90_response=("response_time_min", lambda x: x.quantile(0.9)),
        avg_turnout=("turnout_time_min","mean")
    ).reset_index()
    city_agg["avg_response"] = city_agg["avg_response"].round(2)
    city_agg["p90_response"] = city_agg["p90_response"].round(2)
    city_agg["avg_turnout"] = city_agg["avg_turnout"].round(2)
    return city_agg.rename(columns={"Incident_City":"city"}).to_dict(orient="records")
# ---------------- HOURLY RESPONSE ----------------
def compute_hourly_response(df: pd.DataFrame) -> list[dict]:
    """
    Groups calls by hour of Time_Call_Was_Received.
    Returns list of dicts with:
      - hour: "00:00", "01:00", ...
      - avg_response: float (average response time)
      - count: int (number of calls)
      - is_peak_delay: bool (True if this hour has above-average delays)
    """
    if df.empty or "Time_Call_Was_Received" not in df.columns:
        return []

    df = df.copy()
    df["hour"] = df["Time_Call_Was_Received"].dt.hour

    grouped = df.groupby("hour").agg(
        avg_response=("response_time_min", "mean"),
        count=("Incident_Number", "count")
    ).reset_index()

    # Identify peak delay hours (above overall mean)
    overall_mean_response = grouped["avg_response"].mean()
    grouped["is_peak_delay"] = grouped["avg_response"] > overall_mean_response

    # format hour as string "HH:00"
    grouped["hour"] = grouped["hour"].apply(lambda h: f"{h:02d}:00")
    grouped["avg_response"] = grouped["avg_response"].round(2)

    return grouped.to_dict(orient="records")

# ---------------- PEAK DELAY HOURS SUMMARY ----------------
def compute_peak_delay_hours(df: pd.DataFrame, sla: float = 8) -> Dict[str, Any]:
    """
    Identifies which HOURS had the most DELAYED incidents (response_time > SLA).
    Returns hours ranked by count of delayed incidents.
    """
    if df.empty or "Time_Call_Was_Received" not in df.columns or "response_time_min" not in df.columns:
        return {
            "peak_hours": [],
            "worst_hour": None,
            "best_hour": None,
            "total_delayed_incidents": 0
        }

    df = df.copy()
    
    # Filter to only delayed incidents (response time > SLA)
    df_delayed = df[df["response_time_min"] > sla].copy()
    
    if df_delayed.empty:
        return {
            "peak_hours": [],
            "worst_hour": None,
            "best_hour": None,
            "total_delayed_incidents": 0
        }
    
    # Extract hour from Time_Call_Was_Received
    df_delayed["hour"] = df_delayed["Time_Call_Was_Received"].dt.hour
    
    # Count delayed incidents per hour
    hour_counts = df_delayed["hour"].value_counts().sort_values(ascending=False)
    
    # Get worst and best hours by count of delayed incidents
    worst_hour = f"{int(hour_counts.index[0]):02d}:00" if len(hour_counts) > 0 else None
    best_hour = f"{int(hour_counts.index[-1]):02d}:00" if len(hour_counts) > 0 else None
    
    # Build list of peak hours (all hours with delayed incidents, sorted by count)
    peak_hours_list = []
    for hour, count in hour_counts.items():
        peak_hours_list.append({
            "hour": f"{int(hour):02d}:00",
            "delayed_incident_count": int(count),
            "pct_of_total_delays": safe_round((count / len(df_delayed)) * 100)
        })

    return {
        "peak_hours": peak_hours_list,
        "worst_hour": worst_hour,
        "best_hour": best_hour,
        "total_delayed_incidents": int(len(df_delayed))
    }


# ---------------- MAIN ----------------
def main():
    df = load_data(EDA_CSV)
    write_json(compute_kpis(df), OUTPUT_DIR / "kpis.json")
    write_json(compute_time_trends(df), OUTPUT_DIR / "time_trends.json")
    write_json(compute_distributions(df), OUTPUT_DIR / "distributions.json")
    write_json(compute_response_percentiles(df), OUTPUT_DIR / "response_percentiles.json")
    write_json(compute_delay_buckets(df), OUTPUT_DIR / "delay_buckets.json")
    write_json(compute_city_agg(df), OUTPUT_DIR / "city_summary.json")
    write_json(compute_hourly_response(df), OUTPUT_DIR / "hourly_response.json")
    write_json(compute_peak_delay_hours(df), OUTPUT_DIR / "peak_delay_hours.json")
    print("[DONE] Wrote JSON outputs to:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
