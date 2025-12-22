import geopandas as gpd
import folium

# Load GeoJSON
gdf = gpd.read_file(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\geospatial\h3_hex_summary.geojson")

# Pick which metric to visualize
metric = "incidents"  # you can change to: avg_on_scene, min_on_scene, max_on_scene

# Create Folium map centered on data
m = folium.Map(
    location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()],
    zoom_start=9,
    tiles="cartodbpositron"
)

# Choropleth
folium.Choropleth(
    geo_data=gdf,
    data=gdf,
    columns=["h3", metric],
    key_on="feature.properties.h3",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    nan_fill_color="white",
    legend_name=metric.replace("_", " ").title()
).add_to(m)

# Popup values
folium.GeoJson(
    gdf,
    name="hexes",
    tooltip=folium.GeoJsonTooltip(
        fields=["h3", "incidents", "avg_on_scene", "min_on_scene", "max_on_scene"],
        aliases=["H3", "Incidents", "Avg On Scene", "Min On Scene", "Max On Scene"]
    )
).add_to(m)

# Save
m.save(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\geospatial\ems_h3_map.html")

print("Map saved → ems_h3_map.html")
