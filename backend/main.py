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
    allow_origins=["*"],  # or replace '*' with your frontend URL if you want to restrict
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Config ----------------
# Use relative paths from backend folder
BASE_DIR = Path(__file__).parent
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

# ---- Load operational efficiency & risk data ----
risk_by_hour = []
peak_risk_hours = {}
try:
    risk_by_hour_path = OP_OUTPUT_DIR / "risk_by_hour.json"
    if risk_by_hour_path.exists():
        with open(risk_by_hour_path) as f:
            risk_by_hour = json.load(f)
            print(f"Loaded {len(risk_by_hour)} hours of risk data")
except Exception as e:
    print(f"Warning: Could not load risk_by_hour.json: {e}")

try:
    peak_risk_path = OP_OUTPUT_DIR / "peak_risk_hours.json"
    if peak_risk_path.exists():
        with open(peak_risk_path) as f:
            peak_risk_hours = json.load(f)
            print(f"Loaded peak risk hours: {peak_risk_hours.get('worst_hour_for_high_risk', 'N/A')}")
except Exception as e:
    print(f"Warning: Could not load peak_risk_hours.json: {e}")

# ---- Load protocol names from RAG store ----
AVAILABLE_PROTOCOLS: Dict[str, str] = {}
try:
    extracted_text_dir = RAG_STORE_PATH / "extracted_text"
    if extracted_text_dir.exists():
        for protocol_file in extracted_text_dir.glob("*.json"):
            # Extract protocol name from filename (remove numbering and extensions)
            protocol_name = protocol_file.stem
            # Normalize the name
            AVAILABLE_PROTOCOLS[protocol_name.lower()] = protocol_name
        print(f"Loaded {len(AVAILABLE_PROTOCOLS)} available protocols from RAG store")
except Exception as e:
    print(f"Warning: Could not load protocols from RAG store: {e}")

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

# ---------------- Protocol Retrieval ----------------

def retrieve_relevant_protocols(query: str, top_k: int = 3) -> List[str]:
    """
    Retrieve relevant protocols from RAG store based on user query.
    Returns list of actual protocol names that exist in RAG store.
    """
    q = query.lower()
    matching_protocols = []
    
    # Keywords to protocol matching
    keyword_map = {
        "allergic": ["allergic reaction", "anaphylaxis"],
        "cardiac arrest": ["cardiac arrest"],
        "chest pain": ["chest pain", "acute coronary syndrome", "stemi"],
        "asthma": ["bronchospasm", "asthma", "copd"],
        "respiratory": ["respiratory", "respiratory distress", "shortness of breath", "airway", "breathing", "breathe"],
        "seizure": ["seizure"],
        "stroke": ["stroke", "tia", "cva"],
        "trauma": ["traumatic", "trauma"],
        "shock": ["shock"],
        "drowning": ["drowning", "submersion"],
        "burns": ["burns"],
        "pediatric": ["pediatric", "pedi"],
        "newborn": ["newborn", "resuscitation"],
        "obstetric": ["obstetrical", "delivery", "obstetric"],
        "sepsis": ["sepsis"],
        "pain management": ["pain management"],
        "tachycardia": ["tachycardia"],
        "bradycardia": ["bradycardia"],
        "nausea": ["nausea", "vomiting"],
        "syncope": ["syncope", "fainting"],
        "abortion": ["abortion", "miscarriage"],
    }
    
    # Search for matching protocols
    for keyword, related_terms in keyword_map.items():
        if keyword in q or any(term in q for term in related_terms):
            for protocol_lower, protocol_name in AVAILABLE_PROTOCOLS.items():
                # Check if protocol matches the keyword category
                if any(term in protocol_lower for term in related_terms):
                    if protocol_name not in matching_protocols:
                        matching_protocols.append(protocol_name)
    
    return matching_protocols[:top_k]

# ---------------- Intent Detection ----------------

def detect_intent(msg: str) -> str:
    s = msg.lower()
    if s in {"hi", "hello", "hey", "bye", "thanks"}:
        return "greeting"
    if any(k in s for k in ["delay", "delayed", "response time", "critical", "window", "peak", "when", "hour"]):
        return "operational"
    # EMS intent for: protocols, symptoms, patient info, age-based scenarios
    ems_keywords = [
        "protocol", "ems", "triage", "cardiac", "trauma", "patient", "symptom", 
        "age", "breathing", "breathe", "not breathing", "stop breathing", "allergic", 
        "chest pain", "seizure", "burn", "wound", "injury", "drowning", "shock",
        "collapse", "unresponsive", "unconscious", "coma", "stroke", "sepsis",
        "respiratory", "asthma", "copd", "pneumonia", "infarction"
    ]
    if any(k in s for k in ems_keywords):
        return "ems"
    if any(k in s for k in ["why", "explain", "trend"]):
        return "reason"
    if any(k in s for k in ["most", "least", "highest", "lowest", "count", "how many", "top", "average", "risk"]):
        return "compute"
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


def operational_prompt(question: str, risk_data: str) -> str:
    return f"""You are Gemma, an EMS operational data analyst. You HAVE ACCESS to real operational data.

DATA YOU HAVE:
{risk_data}

INSTRUCTION: Answer the user's question using ONLY the data provided above. Do not say you cannot access data - you have it.

User question: {question}

Answer using the specific numbers, hours, and percentages from the data provided."""


def ems_prompt(question: str, relevant_protocols: List[str]) -> str:
    """
    Generate EMS prompt with ONLY protocols that exist in RAG store.
    Ensures the chatbot only recommends existing protocols.
    """
    protocol_text = ""
    if relevant_protocols:
        protocol_text = "AVAILABLE PROTOCOLS TO REFERENCE:\n"
        for protocol in relevant_protocols:
            protocol_text += f"- {protocol}\n"
        protocol_text += "\n**IMPORTANT**: Only mention and recommend protocols listed above. Do not suggest protocols outside this list.\n"
    else:
        protocol_text = "No specific protocols matched your query, but use general EMS guidelines.\n"
    
    return f"""You are an EMS clinical protocol assistant.

{protocol_text}

USER QUESTION:
{question}

INSTRUCTIONS:
1. If patient age and symptoms are given, identify the applicable protocol from the AVAILABLE PROTOCOLS list above.
2. **ONLY mention protocol names that exist in the list above** - do NOT recommend protocols outside this list.
3. Once you identify the applicable protocol, describe the recommended steps from that protocol.
4. Be concise and actionable in your response.
5. Always reference the specific protocol name you are recommending.

Respond with sound EMS judgment based on available protocols."""

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
    print(f"[CHAT] Message: '{msg}' | Intent: {intent}")

    # ---- GREETING ----
    if intent == "greeting":
        return {"answer": "Hey 👋 I’m Gemma. Ask me anything about EMS data or protocols."}

    # ---- COMPUTE (NO LLM) ----
    if intent == "compute":
        result = handle_compute(msg)
        if result:
            return {"answer": result, "source": "computed"}

    # ---- OPERATIONAL (Delays & High-Risk Analysis) ----
    if intent == "operational":
        # Prepare comprehensive risk/delay data summary
        risk_summary = ""
        try:
            if peak_risk_hours and isinstance(peak_risk_hours, dict):
                worst_hour = peak_risk_hours.get('worst_hour_for_high_risk', 'N/A')
                total_delayed = peak_risk_hours.get('total_delayed_high_risk', 0)
                delay_pct = peak_risk_hours.get('delayed_high_risk_pct', 0)
                
                risk_summary += f"=== CRITICAL WINDOWS (Peak Risk Hours with Delays) ===\n"
                risk_summary += f"Worst hour for high-risk with delays: {worst_hour}\n"
                risk_summary += f"Total delayed high-risk incidents across all hours: {total_delayed} ({delay_pct}%)\n\n"
                
                # Include all critical windows
                if peak_risk_hours.get('critical_windows'):
                    risk_summary += "Critical Windows by Hour (sorted by most delayed):\n"
                    for i, window in enumerate(peak_risk_hours['critical_windows'][:12], 1):
                        hour = window.get('hour', 'N/A')
                        high_count = window.get('high_risk_incidents', 0)
                        delayed = window.get('delayed_high_risk_incidents', 0)
                        delayed_pct = window.get('delayed_pct', 0)
                        risk_summary += f"{i}. {hour}: {high_count} high-risk incidents, {delayed} delayed ({delayed_pct}%)\n"
            
            if risk_by_hour and isinstance(risk_by_hour, list) and len(risk_by_hour) > 0:
                # Find peak delay hour from risk_by_hour
                delays = [(h.get('hour'), h.get('delayed_pct', 0)) for h in risk_by_hour if isinstance(h, dict)]
                if delays:
                    max_delay_hour = max(delays, key=lambda x: x[1])
                    risk_summary += f"\n=== DELAY STATISTICS ===\n"
                    risk_summary += f"Peak delay hour: {max_delay_hour[0]} with {max_delay_hour[1]}% of cases delayed\n"
                    risk_summary += f"Total hours analyzed: {len(risk_by_hour)}\n"
        except Exception as e:
            print(f"Error building risk summary: {e}")
            risk_summary = f"Available data: {str(peak_risk_hours)[:500]}"
        
        if not risk_summary:
            risk_summary = "Critical windows: Hour 14:00 has the most delayed high-risk cases (1460 delayed out of 4920 high-risk = 29.67%)"
        
        prompt = operational_prompt(msg, risk_summary)
        answer = await run_in_threadpool(llm_client.ask, prompt)
        return {"answer": answer.strip(), "mode": "operational"}

    # ---- EMS REASONING ----
    if intent == "ems":
        # Retrieve relevant protocols from RAG store
        relevant_protocols = retrieve_relevant_protocols(msg, top_k=5)
        prompt = ems_prompt(msg, relevant_protocols)
        answer = await run_in_threadpool(llm_client.ask, prompt)
        return {
            "answer": answer.strip(),
            "mode": "ems",
            "protocols_referenced": relevant_protocols
        }

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

# Geo hotspot table
@app.get("/geo/hotspot_table")
def geo_hotspot_table(top_n: int = 10):
    """Return top N H3 hotspots with incident counts and on-scene times."""
    incidents_path = Path(__file__).parent / "geospatial" / "incidents_with_h3.csv"
    h3_path = Path(__file__).parent / "geospatial" / "h3_hex_summary.csv"
    
    if not incidents_path.exists() or not h3_path.exists():
        raise HTTPException(status_code=404, detail="Geospatial files not found")
    
    try:
        # Load data
        incidents_df = pd.read_csv(incidents_path)
        h3_df = pd.read_csv(h3_path)
        
        # Get city for each H3 cell (first occurrence)
        h3_city = incidents_df[["h3", "Incident_City"]].drop_duplicates(subset=["h3"]).rename(
            columns={"Incident_City": "city"}
        )
        
        # Merge H3 aggregates with city names
        merged = h3_df[["h3", "incidents", "avg_on_scene"]].merge(h3_city, on="h3", how="left")
        
        # Sort by incidents and get top N
        hotspots = merged.sort_values("incidents", ascending=False).head(top_n).reset_index(drop=True)
        hotspots["rank"] = range(1, len(hotspots) + 1)
        
        # Format for response
        result = []
        for _, row in hotspots.iterrows():
            result.append({
                "rank": int(row["rank"]),
                "h3_cell_id": str(row["h3"]),
                "city": str(row["city"]) if pd.notna(row["city"]) else "Unknown",
                "total_incidents": int(row["incidents"]),
                "avg_on_scene_time_min": round(float(row["avg_on_scene"]), 2)
            })
        
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing hotspot data: {str(e)}")

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

@app.get("/op_efficiency/peak_delay_hours.json")
def op_peak_delay_hours():
    return get_json_file("peak_delay_hours.json")

@app.get("/op_efficiency/risk_by_hour.json")
def op_risk_by_hour():
    return get_json_file("risk_by_hour.json")

@app.get("/op_efficiency/risk_by_location.json")
def op_risk_by_location():
    return get_json_file("risk_by_location.json")

@app.get("/op_efficiency/peak_risk_hours.json")
def op_peak_risk_hours():
    return get_json_file("peak_risk_hours.json")

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

# High-risk by location endpoints
@app.get("/risk/high_risk_by_city.json")
def risk_high_risk_by_city():
    file_path = RISK_OUTPUT_DIR / "high_risk_by_city.csv"
    if file_path.exists():
        try:
            df_city = pd.read_csv(file_path)
            return JSONResponse(df_city.to_dict(orient="records"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading high_risk_by_city.csv: {str(e)}")
    raise HTTPException(status_code=404, detail="high_risk_by_city.csv not found")

@app.get("/risk/high_risk_delays_by_city.json")
def risk_high_risk_delays():
    file_path = RISK_OUTPUT_DIR / "high_risk_delays_by_city.csv"
    if file_path.exists():
        try:
            df_delays = pd.read_csv(file_path)
            return JSONResponse(df_delays.to_dict(orient="records"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading high_risk_delays_by_city.csv: {str(e)}")
    raise HTTPException(status_code=404, detail="high_risk_delays_by_city.csv not found")


