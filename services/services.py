from pathlib import Path
import json
import pandas as pd
from ollama import chat as ollama_chat  # Gemma 7B Instruct API
from typing import List

# Paths
RAG_STORE_PATH = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\rag_store")
CSV_PATH = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv")

# Load dataset (keep in memory or lazy-load)
df = pd.read_csv(CSV_PATH)
df.fillna("", inplace=True)

# Function to retrieve top protocols/SOP snippets from RAG store
def retrieve_protocols(query: str, top_k: int = 5) -> List[str]:
    """Retrieve top-k relevant protocol snippets from JSON/embeddings store."""
    snippets = []
    # For simplicity, assume each file in RAG_STORE_PATH is a JSON with text
    for file in RAG_STORE_PATH.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # data["text"] contains the protocol/SOP
            if query.lower() in data.get("text", "").lower():
                snippets.append(data["text"])
    return snippets[:top_k]

# Function to summarize relevant patient data for prompt
def get_patient_summary(age=None, symptom=None, city=None, top_n=5) -> str:
    df_filtered = df
    if age:
        df_filtered = df_filtered[df_filtered["Patient_Age"] == age]
    if symptom:
        df_filtered = df_filtered[df_filtered["Primary_Impression"].str.contains(symptom, case=False)]
    if city:
        df_filtered = df_filtered[df_filtered["City"].str.contains(city, case=False)]
    summary = df_filtered.head(top_n).to_dict(orient="records")
    return json.dumps(summary, indent=2)

# Function to construct prompt
def construct_prompt(user_query: str, protocols: List[str], patient_summary: str) -> str:
    prompt = f"""
You are Gemma, an EMS assistant. Use the context below to answer questions.

Context:
Protocols/SOPs:
{chr(10).join(protocols)}

Patient data (top {len(patient_summary)}):
{patient_summary}

Question:
{user_query}

Answer clearly with risk level, recommended protocol, and explanation.
"""
    return prompt

# Function to call Gemma 7B Instruct
def query_gemma(prompt: str) -> str:
    response = ollama_chat(model="gemma-7b-instruct", messages=[{"role": "user", "content": prompt}])
    return response.get("content", "")
