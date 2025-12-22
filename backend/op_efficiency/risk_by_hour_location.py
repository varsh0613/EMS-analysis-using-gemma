#!/usr/bin/env python3
"""
risk_by_hour_location.py

Analyzes when and where high-risk cases emerge.
Combines risk labels with temporal and geographic data.

Outputs:
- risk_by_hour.json: Risk distribution by hour
- risk_by_location.json: Risk distribution by city/location
- peak_risk_hours.json: Top high-risk hours with details
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Any

# Config - Use relative paths from op_efficiency folder
EDA_CSV = Path(__file__).parent.parent / "eda" / "eda.csv"
RISK_OUTPUTS = Path(__file__).parent.parent / "risk_score" / "outputs"
OP_OUTPUT_DIR = Path(__file__).parent / "outputs"
OP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def safe_round(x, nd=2):
    try:
        if pd.isna(x):
            return None
        return round(float(x), nd)
    except Exception:
        return None

def load_data_with_risk() -> pd.DataFrame:
    """Load final_risk_scored.csv with all data and risk labels"""
    final_risk_path = RISK_OUTPUTS / "final_risk_scored.csv"
    
    if final_risk_path.exists():
        print(f"Loading from final_risk_scored.csv...")
        df = pd.read_csv(final_risk_path)
    else:
        print(f"final_risk_scored.csv not found, loading from EDA...")
        df = pd.read_csv(EDA_CSV)
    
    # Convert datetime columns
    date_cols = [
        "Time_Call_Was_Received",
        "Time_Vehicle_was_Dispatched",
        "Time_Arrived_on_Scene",
        "Time_Departed_from_the_Scene",
    ]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    
    # Compute times if not already in df
    if "response_time_min" not in df.columns and "Time_Arrived_on_Scene" in df.columns and "Time_Vehicle_was_Dispatched" in df.columns:
        df["response_time_min"] = (df["Time_Arrived_on_Scene"] - df["Time_Vehicle_was_Dispatched"]).dt.total_seconds() / 60
    if "turnout_time_min" not in df.columns and "Time_Vehicle_was_Dispatched" in df.columns and "Time_Call_Was_Received" in df.columns:
        df["turnout_time_min"] = (df["Time_Vehicle_was_Dispatched"] - df["Time_Call_Was_Received"]).dt.total_seconds() / 60
    if "call_cycle_time_min" not in df.columns and "Time_Departed_from_the_Scene" in df.columns and "Time_Call_Was_Received" in df.columns:
        df["call_cycle_time_min"] = (df["Time_Departed_from_the_Scene"] - df["Time_Call_Was_Received"]).dt.total_seconds() / 60
    if "on_scene_time_min" not in df.columns and "Time_Departed_from_the_Scene" in df.columns and "Time_Arrived_on_Scene" in df.columns:
        df["on_scene_time_min"] = (df["Time_Departed_from_the_Scene"] - df["Time_Arrived_on_Scene"]).dt.total_seconds() / 60
    
    # Ensure risk_label exists and is not null
    if "risk_label" not in df.columns:
        df["risk_label"] = "MEDIUM"
    else:
        df["risk_label"] = df["risk_label"].fillna("MEDIUM")
    
    # Extract hour
    if "Time_Call_Was_Received" in df.columns:
        df["hour"] = df["Time_Call_Was_Received"].dt.hour
    
    return df

def compute_risk_by_hour(df: pd.DataFrame, sla: float = 8) -> List[Dict[str, Any]]:
    """Risk distribution by hour with delay percentage"""
    if df.empty or "hour" not in df.columns or "risk_label" not in df.columns:
        return []
    
    # Group by hour and risk level
    df = df.copy()
    df = df.dropna(subset=["hour", "risk_label"])
    
    result = []
    for hour in range(24):
        hour_data = df[df["hour"] == hour]
        if hour_data.empty:
            continue
        
        total = len(hour_data)
        high_count = int((hour_data["risk_label"] == "HIGH").sum())
        medium_count = int((hour_data["risk_label"] == "MEDIUM").sum())
        low_count = int((hour_data["risk_label"] == "LOW").sum())
        
        avg_response = safe_round(hour_data["response_time_min"].mean())
        high_pct = safe_round((high_count / total * 100) if total > 0 else 0)
        
        # Calculate delayed percentage (response_time > SLA)
        delayed_count = int((hour_data["response_time_min"] > sla).sum()) if "response_time_min" in hour_data.columns else 0
        delayed_pct = safe_round((delayed_count / total * 100) if total > 0 else 0)
        
        result.append({
            "hour": f"{hour:02d}:00",
            "total_incidents": total,
            "high_risk_count": high_count,
            "high_risk_pct": high_pct,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "avg_response_time": avg_response,
            "delayed_count": delayed_count,
            "delayed_pct": delayed_pct
        })
    
    # Sort by hour (chronologically 0-23)
    result.sort(key=lambda x: int(x["hour"].split(":")[0]))
    return result

def compute_risk_by_location(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Risk distribution by city/location"""
    if df.empty or "Incident_City" not in df.columns or "risk_label" not in df.columns:
        return []
    
    df = df.copy()
    df = df[(df["Incident_City"] != "") & (df["risk_label"].notna())]
    
    result = []
    for city, city_data in df.groupby("Incident_City"):
        total = len(city_data)
        high_count = int((city_data["risk_label"] == "HIGH").sum())
        medium_count = int((city_data["risk_label"] == "MEDIUM").sum())
        low_count = int((city_data["risk_label"] == "LOW").sum())
        
        avg_response = safe_round(city_data["response_time_min"].mean())
        high_pct = safe_round((high_count / total * 100) if total > 0 else 0)
        
        result.append({
            "city": str(city),
            "total_incidents": total,
            "high_risk_count": high_count,
            "high_risk_pct": high_pct,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "avg_response_time": avg_response
        })
    
    # Sort by high risk count descending
    result.sort(key=lambda x: x["high_risk_count"], reverse=True)
    return result

def compute_peak_risk_hours(df: pd.DataFrame, sla: float = 8) -> Dict[str, Any]:
    """
    Identifies hours with most high-risk cases AND delays.
    Critical: where high-risk meets response time breach.
    """
    if df.empty or "hour" not in df.columns or "risk_label" not in df.columns:
        return {
            "critical_windows": [],
            "worst_hour_for_high_risk": None,
            "total_high_risk_incidents": 0,
            "total_delayed_high_risk": 0
        }
    
    df = df.copy()
    df = df.dropna(subset=["hour", "risk_label"])
    
    # High-risk incidents
    df_high = df[df["risk_label"] == "HIGH"].copy()
    
    if df_high.empty:
        return {
            "critical_windows": [],
            "worst_hour_for_high_risk": None,
            "total_high_risk_incidents": 0,
            "total_delayed_high_risk": 0
        }
    
    # Group by hour
    hour_stats = []
    for hour in range(24):
        hour_high = df_high[df_high["hour"] == hour]
        if hour_high.empty:
            continue
        
        total_high = len(hour_high)
        delayed_high = int((hour_high["response_time_min"] > sla).sum()) if "response_time_min" in hour_high.columns else 0
        avg_response = safe_round(hour_high["response_time_min"].mean())
        delayed_pct = safe_round((delayed_high / total_high * 100) if total_high > 0 else 0)
        
        hour_stats.append({
            "hour": f"{hour:02d}:00",
            "high_risk_incidents": total_high,
            "delayed_high_risk_incidents": delayed_high,
            "delayed_pct": delayed_pct,
            "avg_response": avg_response
        })
    
    # Sort by hour (chronologically 0-23)
    hour_stats.sort(key=lambda x: int(x["hour"].split(":")[0]))
    
    worst_hour = hour_stats[0]["hour"] if hour_stats else None
    total_high = len(df_high)
    total_delayed_high = int((df_high["response_time_min"] > sla).sum()) if "response_time_min" in df_high.columns else 0
    
    return {
        "critical_windows": hour_stats,
        "worst_hour_for_high_risk": worst_hour,
        "total_high_risk_incidents": total_high,
        "total_delayed_high_risk": total_delayed_high,
        "delayed_high_risk_pct": safe_round((total_delayed_high / total_high * 100) if total_high > 0 else 0)
    }

def write_json(obj: Any, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))

def main():
    print("Loading data with risk labels...")
    df = load_data_with_risk()
    print(f"Loaded {len(df):,} rows")
    
    print("\nComputing risk by hour...")
    risk_by_hour = compute_risk_by_hour(df)
    write_json(risk_by_hour, OP_OUTPUT_DIR / "risk_by_hour.json")
    print(f"Wrote {len(risk_by_hour)} hours to risk_by_hour.json")
    
    print("\nComputing risk by location...")
    risk_by_location = compute_risk_by_location(df)
    write_json(risk_by_location, OP_OUTPUT_DIR / "risk_by_location.json")
    print(f"Wrote {len(risk_by_location)} cities to risk_by_location.json")
    
    print("\nComputing peak risk hours (critical windows)...")
    peak_risk = compute_peak_risk_hours(df)
    write_json(peak_risk, OP_OUTPUT_DIR / "peak_risk_hours.json")
    print(f"Critical windows: {len(peak_risk['critical_windows'])} hours")
    if peak_risk["worst_hour_for_high_risk"]:
        print(f"Worst hour for high-risk: {peak_risk['worst_hour_for_high_risk']}")
    
    print(f"\n[DONE] Risk analysis written to {OP_OUTPUT_DIR}")

if __name__ == "__main__":
    main()
