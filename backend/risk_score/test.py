import pandas as pd
import numpy as np
import json
from sklearn.decomposition import PCA
from umap import UMAP
from joblib import load

def generate_dashboard_jsons(
    clustering_method: str = "umap",  # "umap" or "pca"
    max_points_per_cluster: int = 50
):
    # --- Paths ---
    scored_csv_path = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs\final_risk_scored.csv"
    features_path = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs\engineered_features.joblib"
    output_dir = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs"

    # --- Load data ---
    df = pd.read_csv(scored_csv_path)
    features = load(features_path)  # shape (n_samples, n_features)

    # --- 1️⃣ Cluster embeddings ---
    if clustering_method.lower() == "umap":
        reducer = UMAP(n_components=2, random_state=42)
    elif clustering_method.lower() == "pca":
        reducer = PCA(n_components=2)
    else:
        raise ValueError("clustering_method must be 'umap' or 'pca'")

    embeddings = reducer.fit_transform(features)
    df_emb = pd.DataFrame(embeddings, columns=["x", "y"])
    df_emb["risk_label"] = df["risk_label"]
    df_emb["cluster_id"] = df["cluster_id"] if "cluster_id" in df.columns else 0

    # Sample points per cluster
    sampled_embs = (
        df_emb.groupby("cluster_id")
        .apply(lambda x: x.sample(n=min(len(x), max_points_per_cluster), random_state=42))
        .reset_index(drop=True)
    )

    # Save cluster embeddings JSON
    cluster_json = sampled_embs.to_dict(orient="records")
    with open(f"{output_dir}/cluster_embeddings.json", "w") as f:
        json.dump(cluster_json, f, indent=2)

    # --- 2️⃣ Top 5 protocols per risk ---
    top_protocols = (
        df.groupby("risk_label")["Protocol_Used_by_EMS_Personnel"]
        .value_counts()
        .groupby(level=0)
        .head(5)
        .reset_index(name="count")
    )
    top_protocols_json = {
        label: grp[["Protocol_Used_by_EMS_Personnel", "count"]].to_dict(orient="records")
        for label, grp in top_protocols.groupby("risk_label")
    }
    with open(f"{output_dir}/top_protocols.json", "w") as f:
        json.dump(top_protocols_json, f, indent=2)

    # --- 3️⃣ Top 5 primary impressions per risk ---
    top_impressions = (
        df.groupby("risk_label")["primary_impression"]
        .value_counts()
        .groupby(level=0)
        .head(5)
        .reset_index(name="count")
    )
    top_impressions_json = {
        label: grp[["primary_impression", "count"]].to_dict(orient="records")
        for label, grp in top_impressions.groupby("risk_label")
    }
    with open(f"{output_dir}/top_primary_impressions.json", "w") as f:
        json.dump(top_impressions_json, f, indent=2)

    # --- 4️⃣ Label distribution ---
    label_dist = df["risk_label"].value_counts().to_dict()
    with open(f"{output_dir}/label_distribution.json", "w") as f:
        json.dump(label_dist, f, indent=2)

    print("✅ Dashboard JSON files generated in:", output_dir)

# --- Run the function ---
if __name__ == "__main__":
    generate_dashboard_jsons(clustering_method="umap")
