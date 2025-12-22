import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import h3  # make sure your version supports latlng_to_cell

# =======================================================
# Load data
# =======================================================
def load_incidents(path):
    print("[1] Loading incidents...")
    df = pd.read_csv(path)

    if "Incident_Latitude" not in df or "Incident_Longitude" not in df:
        raise ValueError("Dataset must contain Incident_Latitude and Incident_Longitude.")

    return df

# =======================================================
# Compute on-scene time
# =======================================================
def compute_on_scene_time(df):
    print("[2] Computing on-scene time...")

    df["Time_Arrived_on_Scene"] = pd.to_datetime(df["Time_Arrived_on_Scene"])
    df["Time_Departed_from_the_Scene"] = pd.to_datetime(df["Time_Departed_from_the_Scene"])

    df["on_scene_time_min"] = (
        df["Time_Departed_from_the_Scene"] - df["Time_Arrived_on_Scene"]
    ).dt.total_seconds() / 60

    df["on_scene_time_min"] = df["on_scene_time_min"].clip(lower=0, upper=200)

    return df

# =======================================================
# Add H3 index (incident-level)
# =======================================================
def add_h3(df, resolution=8):
    print("[3] Adding H3 hex indices...")

    df["h3"] = df.apply(
        lambda r: h3.latlng_to_cell(
            r["Incident_Latitude"],
            r["Incident_Longitude"],
            resolution
        ),
        axis=1
    )

    return df

# =======================================================
# Aggregate by H3 cell
# =======================================================
def compute_h3_aggregates(df):
    print("[4] Computing H3 aggregates...")

    agg = df.groupby("h3").agg(
        incidents=("Incident_Number", "count"),
        avg_on_scene=("on_scene_time_min", "mean"),
        min_on_scene=("on_scene_time_min", "min"),
        max_on_scene=("on_scene_time_min", "max"),
    ).reset_index()

    return agg

# =======================================================
# Add polygon geometry from H3 cell
# =======================================================
def add_hex_geometry(agg):
    def hex_to_poly(h):
        # H3 returns list of (lat, lon)
        boundary = h3.cell_to_boundary(h)
        coords = [(lon, lat) for lat, lon in boundary]
        return Polygon(coords)

    agg["geometry"] = agg["h3"].apply(hex_to_poly)
    return gpd.GeoDataFrame(agg, geometry="geometry", crs="EPSG:4326")

# =======================================================
# Save outputs
# =======================================================
def save_outputs(df_incidents, gdf_hex):
    print("[6] Saving outputs...")
    
    from pathlib import Path
    output_dir = Path(__file__).parent

    # Incident-level CSV with H3 mapping
    df_incidents.to_csv(
        output_dir / "incidents_with_h3.csv",
        index=False
    )

    # Aggregated H3 hex-level CSV + GeoJSON
    gdf_hex.to_csv(
        output_dir / "h3_hex_summary.csv",
        index=False
    )

    gdf_hex.to_file(
        output_dir / "h3_hex_summary.geojson",
        driver="GeoJSON"
    )

    print("[OK] Saved incident-level CSV, aggregated CSV, and GeoJSON.")

# =======================================================
# MAIN
# =======================================================
def main():
    from pathlib import Path
    # Path from geospatial folder to eda folder (both in backend)
    eda_csv = Path(__file__).parent.parent / "eda" / "eda.csv"
    df = load_incidents(str(eda_csv))

    df = compute_on_scene_time(df)
    df = add_h3(df, resolution=8)

    agg = compute_h3_aggregates(df)
    gdf = add_hex_geometry(agg)

    save_outputs(df, gdf)

    print("[DONE] Geospatial engine finished.")

if __name__ == "__main__":
    main()
