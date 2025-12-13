import pandas as pd
import os

FILE_PATH = r"C:\Users\SAHARA\Downloads\Emergency_Medical_Service_(EMS)_Incidents_20251121.csv"
OUTPUT_PATH = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\cleaning\cleaned_ems_outputf.csv"

def clean_ems_dataset():
    print("[INFO] Loading dataset...")
    df = pd.read_csv(FILE_PATH)
    print("[INFO] Original shape:", df.shape)

    # --------------------------------------------------
# 0. Remove duplicates
# --------------------------------------------------
print("[INFO] Checking for duplicates...")

if "Incident_Number" in df.columns and "Time_Call_Was_Received" in df.columns:
    before = df.shape[0]
    df = df.drop_duplicates(subset=["Incident_Number", "Time_Call_Was_Received"])
    after = df.shape[0]
    print(f"[INFO] Removed {before - after} duplicates (Incident_Number + Time_Call).")

    # --------------------------------------------------
    # 1. Clean column names
    # --------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    # --------------------------------------------------
    # 2. Convert datetime columns (raw conversion)
    # --------------------------------------------------
    time_cols = [
        "Time_Call_Was_Received",
        "Time_Vehicle_was_Dispatched",
        "Time_Vehicle_was_en_Route_to_Scene",
        "Time_Arrived_on_Scene",
        "Time_Arrived_at_Patient",
        "Time_Departed_from_the_Scene",
        "Time_Arrived_to_Next_Destination_(i.e.,_Hospital)",
        "Injury_Date"
    ]

    print("[INFO] Converting datetime columns...")
    for col in time_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # --------------------------------------------------
    # 3. Drop rows missing CRITICAL timestamps
    # --------------------------------------------------
    critical_time_cols = [
        "Time_Call_Was_Received",
        "Time_Vehicle_was_Dispatched",
        "Time_Vehicle_was_en_Route_to_Scene",
        "Time_Arrived_on_Scene",
        "Time_Arrived_at_Patient",
        "Time_Departed_from_the_Scene",
        "Time_Arrived_to_Next_Destination_(i.e.,_Hospital)"
    ]

    print("[INFO] Dropping rows with missing critical timestamps...")
    df = df.dropna(subset=critical_time_cols)

    # --------------------------------------------------
    # 4. Drop rows missing latitude/longitude
    # --------------------------------------------------
    print("[INFO] Dropping rows with missing lat/lon...")
    df = df.dropna(subset=["Incident_Latitude", "Incident_Longitude"])

    # --------------------------------------------------
    # 5. Drop rows with missing age
    # --------------------------------------------------
    print("[INFO] Dropping rows with missing Age...")
    df = df.dropna(subset=["Patient_Age"])

    # --------------------------------------------------
    # 6. Fill Injury_Date from Time_Call date ONLY
    # --------------------------------------------------
    print("[INFO] Filling Injury_Date from Time_Call_Was_Received (DATE ONLY)...")
    df["Injury_Date"] = df["Injury_Date"].fillna(df["Time_Call_Was_Received"].dt.date)
    df["Injury_Date"] = pd.to_datetime(df["Injury_Date"], errors="coerce")

    # --------------------------------------------------
    # 7. Extract Year + Month (Month as Jan, Feb...)
    # --------------------------------------------------
    print("[INFO] Extracting Year and Month...")
    df["Year_Call_Received"] = df["Time_Call_Was_Received"].dt.year.astype("Int64")
    df["Month_Call_Received"] = df["Time_Call_Was_Received"].dt.strftime("%b")

    # --------------------------------------------------
    # 8. Fill categorical columns
    # --------------------------------------------------
    print("[INFO] Filling categorical columns...")

    # County always Marine
    if "Incident_County" in df.columns:
        df["Incident_County"] = df["Incident_County"].fillna("Marine")

    # Generic object column fill
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("Unknown")

    # --------------------------------------------------
    # 9. Convert types for numeric columns
    # --------------------------------------------------
    print("[INFO] Converting numeric datatypes...")

    dtype_map = {
        "Year_Call_Received": "Int64",
        "Patient_Age": "Int64",
        "Incident_ZIP_Postal": "Int64",
        "Incident_Latitude": "float",
        "Incident_Longitude": "float"
    }

    for col, dtype in dtype_map.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)

    # --------------------------------------------------
    # 10. Format datetime columns: DD-MM-YYYY HH:MM
    # --------------------------------------------------
    print("[INFO] Applying final datetime formatting...")

    datetime_cols = [
        "Time_Call_Was_Received",
        "Time_Vehicle_was_Dispatched",
        "Time_Vehicle_was_en_Route_to_Scene",
        "Time_Arrived_on_Scene",
        "Time_Arrived_at_Patient",
        "Time_Departed_from_the_Scene",
        "Time_Arrived_to_Next_Destination_(i.e.,_Hospital)"
    ]

    for col in datetime_cols:
        df[col] = df[col].dt.strftime("%d-%m-%Y %H:%M")

    # Date-only fields
    df["Injury_Date"] = df["Injury_Date"].dt.strftime("%d-%m-%Y")

    # --------------------------------------------------
    # 11. Save cleaned dataset
    # --------------------------------------------------
    print("[INFO] Saving cleaned dataset...")
    df.to_csv(OUTPUT_PATH, index=False)

    print("[SUCCESS] Cleaning complete!")
    print("[SUCCESS] Saved cleaned dataset to:", OUTPUT_PATH)
    print("[INFO] Final shape:", df.shape)

if __name__ == "__main__":
    clean_ems_dataset()
