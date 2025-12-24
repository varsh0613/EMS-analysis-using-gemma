# main.py
# Render-free-tier–safe FastAPI backend

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import time
import threading
from pathlib import Path

# --------------------
# App setup
# --------------------
app = FastAPI(title="Gemma Dashboard Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "ems.csv"
OP_OUTPUT_DIR = DATA_DIR / "outputs"

# --------------------
# Lazy-loaded caches
# --------------------
_df_cache = None
_risk_by_hour_cache = None
_peak_risk_cache = None
_protocols_cache = None
_rag_cache = None

# --------------------
# Helpers (LAZY LOADERS)
# --------------------

def get_df():
    """Load EMS CSV only when needed and cache it."""
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(CSV_PATH)
        # safer fillna: avoid dtype issues
        for col in df.columns:
            if df[col].dtype == "float64":
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("")

        if "Time_Call_Was_Received" in df.columns:
            df["hour"] = pd.to_datetime(
                df["Time_Call_Was_Received"], errors="coerce"
            ).dt.hour

        _df_cache = df
    return _df_cache


def load_json_cached(path: Path, cache_name: str):
    """Generic JSON lazy loader."""
    global _risk_by_hour_cache, _peak_risk_cache, _protocols_cache, _rag_cache

    cache_map = {
        "risk": "_risk_by_hour_cache",
        "peak": "_peak_risk_cache",
        "protocols": "_protocols_cache",
        "rag": "_rag_cache",
    }

    cache_var = cache_map.get(cache_name)
    if cache_var is None:
        return []

    if globals()[cache_var] is None:
        if path.exists():
            with open(path, "r") as f:
                globals()[cache_var] = json.load(f)
        else:
            globals()[cache_var] = []

    return globals()[cache_var]

# --------------------
# Heartbeat (prevents Render free-tier thrash shutdown)
# --------------------

def heartbeat():
    while True:
        time.sleep(60)
        print("heartbeat")

threading.Thread(target=heartbeat, daemon=True).start()

# --------------------
# Routes
# --------------------

@app.get("/")
def root():
    return {"status": "Gemma backend alive"}


@app.get("/dataset")
def get_dataset():
    df = get_df()
    return df.head(200).to_dict(orient="records")


@app.get("/eda/kpis.json")
def get_kpis():
    df = get_df()

    total_incidents = int(len(df))
    avg_age = (
        float(df["Age"].mean())
        if "Age" in df.columns and not df.empty
        else None
    )

    return {
        "total_incidents": total_incidents,
        "average_age": avg_age,
    }


@app.get("/eda/calls_per_hour.json")
def calls_per_hour():
    df = get_df()
    if "hour" not in df.columns:
        return []

    out = (
        df.groupby("hour")
        .size()
        .reset_index(name="count")
        .sort_values("hour")
    )
    return out.to_dict(orient="records")


@app.get("/eda/incident_trend_year.json")
def incident_trend_year():
    df = get_df()
    if "Year" not in df.columns:
        return []

    out = (
        df.groupby("Year")
        .size()
        .reset_index(name="count")
        .sort_values("Year")
    )
    return out.to_dict(orient="records")


@app.get("/risk/by-hour.json")
def risk_by_hour():
    path = OP_OUTPUT_DIR / "risk_by_hour.json"
    return load_json_cached(path, "risk")


@app.get("/risk/peak-hours.json")
def peak_risk_hours():
    path = OP_OUTPUT_DIR / "peak_risk_hours.json"
    return load_json_cached(path, "peak")


@app.get("/protocols")
def protocols():
    path = OP_OUTPUT_DIR / "available_protocols.json"
    return load_json_cached(path, "protocols")


@app.get("/rag/cache")
def rag_cache():
    path = OP_OUTPUT_DIR / "rag_cache.json"
    return load_json_cached(path, "rag")
