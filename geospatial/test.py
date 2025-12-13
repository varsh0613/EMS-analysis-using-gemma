import geopandas as gpd

gdf = gpd.read_file(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\geospatial\h3_hex_summary.geojson")
print(gdf.columns)
print(gdf.head())
