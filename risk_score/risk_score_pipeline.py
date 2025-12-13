#!/usr/bin/env python3
"""
risk_score_pipeline_fixed.py (v3)
STRATIFIED SPLIT:
1. Cluster ALL data
2. LLM labels ALL clusters
3. Stratified split: 70% train, 30% test (maintains class proportions)
4. Train on 70%
5. Test on 30% (held-out, stratified to have LOW/MEDIUM/HIGH proportions)
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import OneHotEncoder

try:
    import lightgbm as lgb
    _HAS_LGB = True
except Exception:
    _HAS_LGB = False

from tqdm import tqdm
from llm_client import LLMClient

# ------------------------- CONFIG -------------------------
INPUT_CSV = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv"
OUT_DIR = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs"
os.makedirs(OUT_DIR, exist_ok=True)

N_CLUSTERS = 30
SAMPLES_PER_CLUSTER = 30
RANDOM_STATE = 42
LLM_SLEEP = 0.25

llm = LLMClient(sleep_between_calls=LLM_SLEEP)

# ------------------------- HELPERS ------------------------
def safe_read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} rows from {path}")
    return df

def preprocess_age(age):
    try:
        a = float(age)
    except Exception:
        return "unknown"
    if a <= 1:
        return "infant"
    if a <= 12:
        return "child"
    if a <= 18:
        return "teen"
    if a <= 65:
        return "adult"
    return "elderly"

def safe_name(s: str) -> str:
    s = str(s)
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^0-9a-z_]", "_", s)
    s = re.sub(r"_+", "_", s)
    if s == "":
        s = "na"
    return s

def make_unique(names):
    out = []
    seen = {}
    for n in names:
        if n not in seen:
            seen[n] = 0
            out.append(n)
        else:
            seen[n] += 1
            new = f"{n}__dup{seen[n]}"
            while new in seen:
                seen[n] += 1
                new = f"{n}__dup{seen[n]}"
            seen[new] = 0
            out.append(new)
    return out

# --------------------- BUILD MEDICAL TEXT ---------------------
def build_medical_text(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["primary_impression"] = df.get("Primary_Impression", "").fillna("").astype(str)
    df["protocol_used"] = df.get("Protocol_Used_by_EMS_Personnel", "").fillna("").astype(str)
    df["Patient_Age"] = df.get("Patient_Age", pd.Series([np.nan]*len(df)))
    df["age_group"] = df["Patient_Age"].apply(preprocess_age)
    df["medical_text"] = (
        df["primary_impression"].str.lower().str.strip().fillna("") + " | " +
        df["protocol_used"].str.lower().str.strip().fillna("") + " | " +
        df["age_group"].astype(str)
    )
    return df

# ----------------------- CLUSTERING --------------------------
def cluster_medical_text(df: pd.DataFrame, n_clusters: int = N_CLUSTERS) -> pd.DataFrame:
    tfidf = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1,2))
    X = tfidf.fit_transform(df["medical_text"].fillna(""))
    joblib.dump(tfidf, os.path.join(OUT_DIR, "tfidf_vectorizer.joblib"))
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    df["cluster_id"] = kmeans.fit_predict(X)
    joblib.dump(kmeans, os.path.join(OUT_DIR, "kmeans_model.joblib"))
    return df

# ----------------------- SAMPLE -------------------------------
def sample_clusters(df: pd.DataFrame, samples_per_cluster: int = SAMPLES_PER_CLUSTER):
    out = {}
    for cid, sub in df.groupby("cluster_id"):
        n = min(len(sub), samples_per_cluster)
        out[int(cid)] = sub.sample(n, random_state=RANDOM_STATE).to_dict(orient="records")
    return out

# ---------------------- LABEL EXTRACTION ----------------------
def extract_label(summary: str) -> str:
    s = (summary or "").lower()
    high_kw = ["cardiac arrest", "life-threatening", "severe", "airway", "major", "unconscious", "seizure", "obvious death", "dead on arrival", "expired"]
    low_kw = ["low risk", "minor", "no injury", "epistaxis", "nosebleed", "public assist", "lift assist", "non traumatic", "non-traumatic", "no treatment"]
    med_kw = ["moderate", "stable", "transport", "observation", "requires transport", "non life-threatening"]
    if any(k in s for k in high_kw):
        return "HIGH"
    if any(k in s for k in low_kw):
        return "LOW"
    if any(k in s for k in med_kw):
        return "MEDIUM"
    if "hospital" in s or "ed" in s or "transport" in s:
        return "MEDIUM"
    return "MEDIUM"

# ---------------------- CLUSTER DIAGNOSTICS --------------------
def cluster_diagnostics(df: pd.DataFrame, label_map: Dict[int, str], out_dir: str):
    diagnostics = {}
    for cid, sub in df.groupby("cluster_id"):
        lbl = label_map.get(int(cid), "MEDIUM")
        example_rows = sub.head(3)[["Incident_Number","primary_impression","protocol_used","age_group"]].to_dict(orient="records")
        diagnostics[int(cid)] = {
            "assigned_label": lbl,
            "cluster_size": int(len(sub)),
            "examples": example_rows
        }
    with open(os.path.join(out_dir, "cluster_diagnostics.json"), "w", encoding="utf-8") as fh:
        json.dump(diagnostics, fh, indent=2, ensure_ascii=False)
    print(f"Wrote cluster diagnostics to {os.path.join(out_dir, 'cluster_diagnostics.json')}")

# ------------------------ MAIN PIPELINE (STRATIFIED) ----------------
def run_pipeline(input_csv: str, out_dir: str):
    df = safe_read_csv(input_csv)
    df = build_medical_text(df)

    print(f"\n=== STEP 1: CLUSTERING ALL DATA ===")
    df = cluster_medical_text(df, n_clusters=N_CLUSTERS)
    print(f"Clustered {len(df):,} rows into {N_CLUSTERS} clusters")

    print(f"\n=== STEP 2: LLM SUMMARIZATION & LABELING ===")
    # Sample and summarize clusters
    cluster_samples = sample_clusters(df, samples_per_cluster=SAMPLES_PER_CLUSTER)
    cluster_summaries = {}
    for cid, samples in tqdm(cluster_samples.items(), desc="LLM cluster summarization"):
        try:
            summary = llm.summarize_cluster(samples=samples, cluster_id=cid)
            if not summary:
                summary = "[NO LLM RESPONSE]"
        except Exception as e:
            print(f"LLM summarization failed for cluster {cid}: {e}")
            summary = "[ERROR]"
        cluster_summaries[int(cid)] = {"summary": summary}

    summaries_path = os.path.join(out_dir, "cluster_summaries.json")
    with open(summaries_path, "w", encoding="utf-8") as fh:
        json.dump(cluster_summaries, fh, indent=2, ensure_ascii=False)
    print(f"Wrote cluster summaries to {summaries_path}")

    # Create label map
    label_map = {cid: extract_label(v["summary"]) for cid, v in cluster_summaries.items()}
    df["risk_label"] = df["cluster_id"].map(label_map).fillna("MEDIUM")
    
    print(f"\nOverall label distribution:")
    print(df["risk_label"].value_counts())

    # Save cluster diagnostics
    cluster_diagnostics(df, label_map, out_dir)

    print(f"\n=== STEP 3: STRATIFIED SPLIT (70% train, 30% test) ===")
    # Stratified split to maintain class proportions
    df_train, df_test = train_test_split(
        df,
        test_size=0.3,
        random_state=RANDOM_STATE,
        stratify=df["risk_label"]  # <-- keeps LOW/MEDIUM/HIGH proportions equal
    )
    
    print(f"Train set: {len(df_train):,} rows")
    print(f"Train distribution:\n{df_train['risk_label'].value_counts()}\n")
    print(f"Test set: {len(df_test):,} rows")
    print(f"Test distribution:\n{df_test['risk_label'].value_counts()}\n")

    train_path = os.path.join(out_dir, "train_set.csv")
    test_path = os.path.join(out_dir, "test_set.csv")
    df_train.to_csv(train_path, index=False)
    df_test.to_csv(test_path, index=False)

    # ===== CLASSIFIER TRAINING =====
    if not _HAS_LGB:
        print("LightGBM not available; skipping classifier training.")
        return

    print(f"\n=== STEP 4: TRAINING CLASSIFIER ===")
    print("Using BOTH medical text AND operational features")
    
    # Prepare operational features
    X_train_df = pd.DataFrame(index=df_train.index)
    
    # Numeric features
    numeric_cols = ["response_time_min", "turnout_time_min", "call_cycle_time_min", "on_scene_time_min"]
    for col in numeric_cols:
        X_train_df[col] = pd.to_numeric(df_train.get(col, pd.Series([np.nan]*len(df_train))), errors="coerce").fillna(-1)
    
    # Patient age
    X_train_df["patient_age"] = pd.to_numeric(df_train.get("Patient_Age", pd.Series([np.nan]*len(df_train))), errors="coerce").fillna(-1)
    
    # Medical text features (TF-IDF)
    tfidf = TfidfVectorizer(max_features=500, stop_words="english", ngram_range=(1,2))
    X_tfidf_train = tfidf.fit_transform(df_train["medical_text"].fillna(""))
    joblib.dump(tfidf, os.path.join(OUT_DIR, "tfidf_classifier.joblib"))
    X_tfidf_train_df = pd.DataFrame(X_tfidf_train.toarray(), columns=[f"tfidf_{i}" for i in range(X_tfidf_train.shape[1])], index=df_train.index)
    
    # Categorical features
    cat_cols = ["Patient_Gender", "Incident_County", "Primary_Impression"]
    X_cats_train = df_train[cat_cols].fillna("unknown").astype(str)
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False) if hasattr(OneHotEncoder(), "sparse_output") else OneHotEncoder(handle_unknown="ignore", sparse=False)
    X_ohe_train = ohe.fit_transform(X_cats_train)
    
    # Build feature names for categorical
    feature_names_cat = []
    for col_idx, categories in enumerate(ohe.categories_):
        prefix = f"col{col_idx}"
        for cat in categories:
            safe = safe_name(cat)
            feature_names_cat.append(f"{prefix}__{safe}")
    
    feature_names_cat = make_unique(feature_names_cat)
    X_cat_df = pd.DataFrame(X_ohe_train, columns=feature_names_cat, index=df_train.index)
    
    # Combine all features
    X_train_df = pd.concat([X_train_df, X_tfidf_train_df, X_cat_df], axis=1)
    feature_names = list(X_train_df.columns)

    y_train = df_train["risk_label"].map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})

    ltrain = lgb.Dataset(X_train_df, label=y_train)

    params = {
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "verbosity": -1,
        "seed": RANDOM_STATE,
        "num_leaves": 31,
        "learning_rate": 0.05
    }

    print("Training LightGBM...")
    model = lgb.train(params, ltrain, num_boost_round=500)
    joblib.dump(model, os.path.join(out_dir, "classifier_model.joblib"))
    print(f"Model trained on {len(df_train):,} samples")

    # ===== EVALUATION =====
    print(f"\n=== STEP 5: EVALUATION ON TEST SET ===")
    
    # Prepare test features
    X_test_df = pd.DataFrame(index=df_test.index)
    
    # Numeric features
    for col in numeric_cols:
        X_test_df[col] = pd.to_numeric(df_test.get(col, pd.Series([np.nan]*len(df_test))), errors="coerce").fillna(-1)
    
    # Patient age
    X_test_df["patient_age"] = pd.to_numeric(df_test.get("Patient_Age", pd.Series([np.nan]*len(df_test))), errors="coerce").fillna(-1)
    
    # Medical text features (using same TF-IDF encoder)
    X_tfidf_test = tfidf.transform(df_test["medical_text"].fillna(""))
    X_tfidf_test_df = pd.DataFrame(X_tfidf_test.toarray(), columns=[f"tfidf_{i}" for i in range(X_tfidf_test.shape[1])], index=df_test.index)
    
    # Categorical features
    X_cats_test = df_test[cat_cols].fillna("unknown").astype(str)
    X_ohe_test = ohe.transform(X_cats_test)
    X_cat_test_df = pd.DataFrame(X_ohe_test, columns=feature_names_cat, index=df_test.index)
    
    # Combine all features
    X_test_df = pd.concat([X_test_df, X_tfidf_test_df, X_cat_test_df], axis=1)

    y_test = df_test["risk_label"].map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})

    # Predictions
    y_pred_prob = model.predict(X_test_df)
    y_pred = np.argmax(y_pred_prob, axis=1)

    # Report
    report = classification_report(y_test, y_pred, labels=[0,1,2], target_names=["LOW","MEDIUM","HIGH"], zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0,1,2])

    report_path = os.path.join(out_dir, "classifier_report.txt")
    with open(report_path, "w") as f:
        f.write("=== DATA SPLIT ===\n")
        f.write(f"Train: {len(df_train):,} rows (70%)\n")
        f.write(f"Test: {len(df_test):,} rows (30%)\n\n")
        f.write("=== STRATIFIED CLASS DISTRIBUTION ===\n")
        f.write("Train:\n")
        f.write(df_train["risk_label"].value_counts().to_string())
        f.write("\n\nTest:\n")
        f.write(df_test["risk_label"].value_counts().to_string())
        f.write("\n\n=== Classification Report ===\n")
        f.write(report + "\n\n")
        f.write("=== Confusion Matrix ===\n")
        f.write(str(cm))
    print(f"Saved classification report to {report_path}")

    # Confusion matrix CSV
    cm_df = pd.DataFrame(cm, index=["true_LOW","true_MEDIUM","true_HIGH"], columns=["pred_LOW","pred_MEDIUM","pred_HIGH"])
    cm_df.to_csv(os.path.join(out_dir, "confusion_matrix.csv"))

    # Misclassified
    test_orig = df_test.copy()
    test_orig["_pred_label"] = y_pred
    test_orig["_pred_prob_LOW"] = y_pred_prob[:,0]
    test_orig["_pred_prob_MEDIUM"] = y_pred_prob[:,1]
    test_orig["_pred_prob_HIGH"] = y_pred_prob[:,2]
    test_orig["_true_label"] = y_test.values

    mis = test_orig[test_orig["_pred_label"] != test_orig["_true_label"]]
    mis_path = os.path.join(out_dir, "misclassified_samples.csv")
    mis.to_csv(mis_path, index=False)
    print(f"Saved {len(mis):,} misclassified samples to {mis_path}")

    print("\n=== PIPELINE COMPLETE ===")

if __name__ == "__main__":
    run_pipeline(INPUT_CSV, OUT_DIR)
