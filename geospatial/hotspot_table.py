"""
Generate H3 hotspot table with city names and rankings.
"""

import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma")

def generate_hotspot_table(top_n=10):
    """
    Generate a hotspot table ranked by incident count.
    """
    # Load incidents with H3 mapping
    incidents_path = BASE_DIR / "geospatial" / "incidents_with_h3.csv"
    incidents_df = pd.read_csv(incidents_path)
    
    # Load H3 aggregates
    h3_path = BASE_DIR / "geospatial" / "h3_hex_summary.csv"
    h3_df = pd.read_csv(h3_path)
    
    # Merge to get city names for each H3 cell
    incidents_h3_city = incidents_df[["h3", "Incident_City"]].drop_duplicates(subset=["h3"]).rename(columns={"Incident_City": "city"})
    
    # Join with H3 aggregates
    merged = h3_df[["h3", "incidents", "avg_on_scene"]].merge(
        incidents_h3_city,
        on="h3",
        how="left"
    )
    
    # Sort by incidents (descending) and get top N
    hotspots = merged.sort_values("incidents", ascending=False).head(top_n).reset_index(drop=True)
    hotspots["rank"] = range(1, len(hotspots) + 1)
    
    # Rename columns for clarity
    hotspots = hotspots[["rank", "h3", "city", "incidents", "avg_on_scene"]].rename(columns={
        "h3": "h3_cell_id",
        "city": "city",
        "incidents": "total_incidents",
        "avg_on_scene": "avg_on_scene_time_min"
    })
    
    # Round on-scene time to 2 decimals
    hotspots["avg_on_scene_time_min"] = hotspots["avg_on_scene_time_min"].round(2)
    
    return hotspots

def save_hotspot_table(hotspots, format="json"):
    """Save hotspot table in JSON or CSV format."""
    output_dir = BASE_DIR / "geospatial" / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    if format == "json":
        output_path = output_dir / "hotspot_table.json"
        hotspots.to_json(output_path, orient="records", indent=2)
    elif format == "csv":
        output_path = output_dir / "hotspot_table.csv"
        hotspots.to_csv(output_path, index=False)
    
    return output_path

if __name__ == "__main__":
    hotspots = generate_hotspot_table(top_n=10)
    print(hotspots)
    
    json_path = save_hotspot_table(hotspots, format="json")
    csv_path = save_hotspot_table(hotspots, format="csv")
    
    print(f"\nSaved JSON: {json_path}")
    print(f"Saved CSV: {csv_path}")
