# ================================
# main.py — Gemma Backend (Compute → Reason → Speak)
# GOAL:
# - Behave like ChatGPT:
#   1. Understand intent
#   2. COMPUTE when numbers are required
#   3. REASON with LLM only when needed
#   4. SPEAK naturally
# - Deterministic for facts, flexible for explanations
# - Existing dashboard endpoints untouched
# ================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import json
import time
from typing import List, Dict, Any, Optional

from llm_client import LLMClient

# ---------------- App & CORS ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Config ----------------
BASE_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma")
CSV_PATH = BASE_DIR / "eda" / "eda.csv"
EDA_OUTPUT_DIR = BASE_DIR / "eda" / "outputs"
OP_OUTPUT_DIR = BASE_DIR / "op_efficiency" / "outputs"
RISK_OUTPUT_DIR = BASE_DIR / "risk_score" / "outputs"
RAG_STORE_PATH = BASE_DIR / "risk_score" / "rag_store"
GEO_PATH = BASE_DIR / "geospatial" / "h3_hex_summary.geojson"

# ---------------- LLM ----------------
llm_client = LLMClient(sleep_between_calls=0.01)

# ---------------- Load Dataset ----------------
if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")

df = pd.read_csv(CSV_PATH)
df.fillna("", inplace=True)

# Extract hour from time column for analysis
if "Time_Call_Was_Received" in df.columns:
    df["hour"] = pd.to_datetime(df["Time_Call_Was_Received"], errors="coerce").dt.hour

COL_CITY = "Incident_City"
COL_AGE = "Patient_Age"
COL_IMPRESSION = "Primary_Impression"

# ---------------- COMPUTE LAYER (SOURCE OF TRUTH) ----------------
# Anything numeric is computed ONCE here

CITY_COUNTS = (
    df[df[COL_CITY] != ""]
    .groupby(COL_CITY)
    .size()
    .sort_values(ascending=False)
)

TOTAL_INCIDENTS = int(len(df))
AVERAGE_AGE = float(df[COL_AGE].mean()) if COL_AGE in df.columns else None
TOP_IMPRESSIONS = (
    df[COL_IMPRESSION]
    .value_counts()
    .head(5)
    .to_dict()
)

# ---------------- RAG STORE (Protocols Only) ----------------
RAG_CACHE: List[str] = []
if RAG_STORE_PATH.exists():
    for f in RAG_STORE_PATH.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                RAG_CACHE.append(json.dumps(data))
        except Exception:
            pass

# ---------------- Intent Detection ----------------

def detect_intent(msg: str) -> str:
    s = msg.lower()
    if s in {"hi", "hello", "hey", "bye", "thanks"}:
        return "greeting"
    if any(k in s for k in ["most", "least", "highest", "lowest", "count", "how many", "top", "average", "hour"]):
        return "compute"
    if any(k in s for k in ["protocol", "ems", "triage", "cardiac", "trauma"]):
        return "ems"
    if any(k in s for k in ["why", "explain", "trend", "analysis"]):
        return "reason"
    return "chat"

# ---------------- COMPUTE HANDLERS ----------------

def handle_compute(msg: str) -> str:
    q = msg.lower()

    if "most" in q and "city" in q:
        city = CITY_COUNTS.index[0]
        count = int(CITY_COUNTS.iloc[0])
        return f"The city with the most incidents is {city}, with {count:,} incidents."

    if "least" in q and "city" in q:
        non_zero = CITY_COUNTS[CITY_COUNTS > 0]
        city = non_zero.index[-1]
        count = int(non_zero.iloc[-1])
        return f"The city with the least incidents is {city}, with {count:,} incidents."

    if "total" in q and "incident" in q:
        return f"There are a total of {TOTAL_INCIDENTS:,} incidents in the dataset."

    # Averages - check most specific first
    if "average" in q:
        if "turnout" in q:
            avg_turnout = df["turnout_time_min"].mean()
            return f"The average turnout time is approximately {avg_turnout:.2f} minutes."
        elif "response" in q:
            avg_response = df["response_time_min"].mean()
            return f"The average response time is approximately {avg_response:.2f} minutes."
        elif "call" in q or "cycle" in q:
            avg_cycle = df["call_cycle_time_min"].mean()
            return f"The average call cycle time is approximately {avg_cycle:.2f} minutes."
        elif "scene" in q or "on_scene" in q:
            avg_scene = df["on_scene_time_min"].mean()
            return f"The average on-scene time is approximately {avg_scene:.2f} minutes."
        elif "age" in q:
            return f"The average patient age is approximately {AVERAGE_AGE:.1f} years."

    # "which hour had most incidents"
    if "hour" in q and "most" in q:
        hour_counts = df["hour"].value_counts()
        peak_hour = int(hour_counts.idxmax())
        count = int(hour_counts.max())
        return f"Hour {peak_hour}:00 had the most incidents with {count:,} incidents."

    # Generic: "top X [impressions|diseases|conditions]"
    if "top" in q and ("impression" in q or "disease" in q or "condition" in q):
        import re
        match = re.search(r"top\s+(\d+)", q)
        limit = int(match.group(1)) if match else 10
        result = df[COL_IMPRESSION].value_counts().head(limit)
        formatted = ", ".join([f"{cond} ({count:,})" for cond, count in result.items()])
        return f"Top {limit} primary impressions: {formatted}"

    # Generic: "how many [condition/disease]"
    if "how many" in q:
        from difflib import SequenceMatcher
        
        search_term = q.replace("how many", "").replace("incidents", "").replace("patients", "").replace("with", "").strip()
        
        if search_term:
            # Try exact substring first
            exact_match = df[df[COL_IMPRESSION].str.contains(search_term, case=False, na=False)]
            if len(exact_match) > 0:
                count = int(exact_match.shape[0])
                return f"There are {count:,} incidents matching '{search_term}'."
            
            # Fuzzy match: find closest disease name
            conditions = df[COL_IMPRESSION].dropna().unique()
            best_match = None
            best_score = 0.4  # Minimum similarity threshold
            
            for cond in conditions:
                if cond:
                    score = SequenceMatcher(None, search_term.lower(), cond.lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = cond
            
            if best_match:
                count = int(df[df[COL_IMPRESSION] == best_match].shape[0])
                return f"There are {count:,} incidents of {best_match} (matched '{search_term}')."
            else:
                return f"No incidents found matching '{search_term}'. Try a different term."

    return ""

# ---------------- PROMPTS ----------------

def reasoning_prompt(question: str, facts: str = "") -> str:
    return f"""
You are Gemma, an EMS data assistant.

FACTS:
{facts if facts else "No computed facts provided."}

QUESTION:
{question}

Explain clearly and concisely. Do not invent numbers.
"""


def ems_prompt(question: str, protocols: List[str]) -> str:
    return f"""
You are an EMS clinical assistant.

PROTOCOLS:
{protocols[:1] if protocols else "General EMS guidelines."}

QUESTION:
{question}

Respond with sound EMS judgment.
"""

# ---------------- CHAT REQUEST ----------------
class ChatRequest(BaseModel):
    message: str

# ---------------- CHAT ENDPOINT ----------------
@app.post("/chat")
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if not msg:
        return {"answer": "Hi! How can I help?"}

    intent = detect_intent(msg)

    # ---- GREETING ----
    if intent == "greeting":
        return {"answer": "Hey 👋 I’m Gemma. Ask me anything about EMS data or protocols."}

    # ---- COMPUTE (NO LLM) ----
    if intent == "compute":
        result = handle_compute(msg)
        if result:
            return {"answer": result, "source": "computed"}

    # ---- EMS REASONING ----
    if intent == "ems":
        prompt = ems_prompt(msg, RAG_CACHE)
        answer = await run_in_threadpool(llm_client.ask, prompt)
        return {"answer": answer.strip(), "mode": "ems"}

    # ---- DATA / WHY / ANALYSIS ----
    if intent == "reason":
        facts = f"Top city: {CITY_COUNTS.index[0]} ({int(CITY_COUNTS.iloc[0]):,})"
        prompt = reasoning_prompt(msg, facts)
        answer = await run_in_threadpool(llm_client.ask, prompt)
        return {"answer": answer.strip(), "mode": "reason"}

    # ---- CHAT ----
    prompt = f"You are Gemma. Respond naturally.\nUser: {msg}\nAnswer:"
    answer = await run_in_threadpool(llm_client.ask, prompt)
    return {"answer": answer.strip(), "mode": "chat"}


# ============= DASHBOARD ENDPOINTS =============

# Dataset pagination
@app.get("/dataset")
def get_dataset(page: int = 1, limit: int = 25):
    start = (page - 1) * limit
    end = start + limit
    total_rows = len(df)
    total_pages = (total_rows + limit - 1) // limit
    rows = df.iloc[start:end].to_dict(orient="records")
    return {"rows": rows, "total_rows": total_rows, "page": page, "total_pages": total_pages}

# EDA JSON
@app.get("/eda/{filename}")
def get_eda_file(filename: str):
    file_path = EDA_OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="application/json")
    raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

@app.get("/eda/kpis.json")
def generate_kpis():
    kpis = {
        "total_incidents": int(df["Incident_Number"].nunique()) if "Incident_Number" in df.columns else None,
        "num_hospitals": int(df["Where_Patient_was_Transported"].nunique()) if "Where_Patient_was_Transported" in df.columns else None,
        "num_primary_impressions": int(df["Primary_Impression"].nunique()) if "Primary_Impression" in df.columns else None,
        "average_patient_age": float(df["Patient_Age"].mean()) if "Patient_Age" in df.columns else None,
        "most_common_incident_place": df["Place_Incident_Happened"].mode()[0] if "Place_Incident_Happened" in df.columns else None
    }
    return JSONResponse(kpis)

# GEOJSON
@app.get("/geo/summary")
def geo_summary():
    if GEO_PATH.exists():
        return FileResponse(GEO_PATH, media_type="application/json")
    raise HTTPException(status_code=404, detail="GeoJSON file not found")

# OP EFFICIENCY
OP_DIR = OP_OUTPUT_DIR

def get_json_file(filename: str):
    file_path = OP_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="application/json")
    raise HTTPException(status_code=404, detail=f"{filename} not found")

@app.get("/op_efficiency/kpis.json")
def op_kpis():
    return get_json_file("kpis.json")

@app.get("/op_efficiency/time_trends.json")
def op_time_trends():
    return get_json_file("time_trends.json")

@app.get("/op_efficiency/distributions.json")
def op_distributions():
    return get_json_file("distributions.json")

@app.get("/op_efficiency/response_percentiles.json")
def op_percentiles():
    return get_json_file("response_percentiles.json")

@app.get("/op_efficiency/delay_buckets.json")
def op_delay_buckets():
    return get_json_file("delay_buckets.json")

@app.get("/op_efficiency/city_summary.json")
def op_city_summary():
    return get_json_file("city_summary.json")

@app.get("/op_efficiency/hourly_response.json")
def op_hourly_response():
    return get_json_file("hourly_response.json")

# RISK OUTPUTS
def get_risk_file(filename: str):
    file_path = RISK_OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(path=file_path, media_type="application/json")
    raise HTTPException(status_code=404, detail=f"{filename} not found in risk outputs")

@app.get("/risk/cluster_embeddings.json")
def risk_cluster_embeddings():
    return get_risk_file("cluster_embeddings.json")

@app.get("/risk/top_protocols.json")
def risk_top_protocols():
    return get_risk_file("top_protocols.json")

@app.get("/risk/top_primary_impressions.json")
def risk_top_primary_impressions():
    return get_risk_file("top_primary_impressions.json")

@app.get("/risk/label_distribution.json")
def risk_label_distribution():
    return get_risk_file("label_distribution.json")

@app.get("/risk/cluster_summaries.json")
def risk_cluster_summaries():
    return get_risk_file("cluster_summaries.json")

@app.get("/risk/clustered_data.csv")
def risk_clustered_data():
    file_path = RISK_OUTPUT_DIR / "clustered_data.csv"
    if file_path.exists():
        return FileResponse(path=file_path, media_type="text/csv")
    raise HTTPException(status_code=404, detail="clustered_data.csv not found")

@app.get("/risk/confusion_matrix.csv")
def risk_confusion_matrix():
    file_path = RISK_OUTPUT_DIR / "confusion_matrix.csv"
    if file_path.exists():
        return FileResponse(path=file_path, media_type="text/csv")
    raise HTTPException(status_code=404, detail="confusion_matrix.csv not found")

@app.get("/risk/classifier_report.txt")
def risk_classifier_report():
    file_path = RISK_OUTPUT_DIR / "classifier_report.txt"
    if file_path.exists():
        return FileResponse(path=file_path, media_type="text/plain")
    raise HTTPException(status_code=404, detail="classifier_report.txt not found")

@app.get("/risk/misclassified_samples.csv")
def risk_misclassified():
    file_path = RISK_OUTPUT_DIR / "misclassified_samples.csv"
    if file_path.exists():
        return FileResponse(path=file_path, media_type="text/csv")
    raise HTTPException(status_code=404, detail="misclassified_samples.csv not found")


