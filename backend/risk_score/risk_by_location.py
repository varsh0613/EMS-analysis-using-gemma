#!/usr/bin/env python3
"""
Analyze high-risk EMS cases by location (city/county)
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path

# Use relative paths from risk_score folder
OUT_DIR = str(Path(__file__).parent / "outputs")

def analyze_risk_by_location():
    """Load test set with risk labels and analyze by location"""
    
    test_path = os.path.join(OUT_DIR, "test_set.csv")
    
    if not os.path.exists(test_path):
        print(f"Error: {test_path} not found. Run risk_score_pipeline.py first.")
        return
    
    df = pd.read_csv(test_path)
    print(f"Loaded {len(df):,} test cases")
    
    # ===== HIGH RISK BY CITY =====
    print("\n" + "="*70)
    print("HIGH RISK CASES BY CITY (Top 15)")
    print("="*70)
    
    high_risk = df[df['risk_label'] == 'HIGH']
    print(f"\nTotal HIGH risk cases: {len(high_risk):,} out of {len(df):,} ({100*len(high_risk)/len(df):.1f}%)")
    
    city_risk = high_risk['Incident_City'].value_counts().head(15)
    city_summary = pd.DataFrame({
        'City': city_risk.index,
        'High_Risk_Count': city_risk.values
    })
    
    # Add percentage of high-risk within each city
    city_summary['Total_Cases_in_City'] = city_summary['City'].apply(
        lambda city: len(df[df['Incident_City'] == city])
    )
    city_summary['High_Risk_Percentage'] = (
        city_summary['High_Risk_Count'] / city_summary['Total_Cases_in_City'] * 100
    ).round(1)
    
    city_summary = city_summary.sort_values('High_Risk_Count', ascending=False)
    print("\n" + city_summary.to_string(index=False))
    
    # ===== HIGH RISK BY COUNTY =====
    print("\n" + "="*70)
    print("HIGH RISK CASES BY COUNTY")
    print("="*70)
    
    county_risk = high_risk['Incident_County'].value_counts()
    county_summary = pd.DataFrame({
        'County': county_risk.index,
        'High_Risk_Count': county_risk.values
    })
    
    county_summary['Total_Cases_in_County'] = county_summary['County'].apply(
        lambda county: len(df[df['Incident_County'] == county])
    )
    county_summary['High_Risk_Percentage'] = (
        county_summary['High_Risk_Count'] / county_summary['Total_Cases_in_County'] * 100
    ).round(1)
    
    county_summary = county_summary.sort_values('High_Risk_Count', ascending=False)
    print("\n" + county_summary.to_string(index=False))
    
    # ===== DELAYS IN HIGH RISK CASES BY LOCATION =====
    print("\n" + "="*70)
    print("RESPONSE DELAYS IN HIGH RISK CASES - BY CITY (Top 10)")
    print("="*70)
    
    # Get top 10 cities by high risk count
    top_cities = city_risk.head(10).index.tolist()
    
    delays_summary = []
    for city in top_cities:
        city_high_risk = high_risk[high_risk['Incident_City'] == city]
        
        avg_response_time = city_high_risk['response_time_min'].mean()
        avg_turnout_time = city_high_risk['turnout_time_min'].mean()
        avg_on_scene_time = city_high_risk['on_scene_time_min'].mean()
        avg_call_cycle = city_high_risk['call_cycle_time_min'].mean()
        
        delays_summary.append({
            'City': city,
            'High_Risk_Count': len(city_high_risk),
            'Avg_Response_Time_min': round(avg_response_time, 1),
            'Avg_Turnout_Time_min': round(avg_turnout_time, 1),
            'Avg_On_Scene_Time_min': round(avg_on_scene_time, 1),
            'Avg_Call_Cycle_Time_min': round(avg_call_cycle, 1)
        })
    
    delays_df = pd.DataFrame(delays_summary)
    print("\n" + delays_df.to_string(index=False))
    
    # ===== INCIDENT TYPES IN HIGH RISK BY CITY =====
    print("\n" + "="*70)
    print("MOST COMMON INCIDENT TYPES IN HIGH RISK CASES - BY TOP 5 CITIES")
    print("="*70)
    
    for city in top_cities[:5]:
        city_high_risk = high_risk[high_risk['Incident_City'] == city]
        print(f"\n{city} (n={len(city_high_risk)} high-risk cases):")
        incidents = city_high_risk['Primary_Impression'].value_counts().head(5)
        for idx, (incident, count) in enumerate(incidents.items(), 1):
            print(f"  {idx}. {incident}: {count} cases ({100*count/len(city_high_risk):.0f}%)")
    
    # ===== SAVE TO CSV =====
    city_summary.to_csv(os.path.join(OUT_DIR, "high_risk_by_city.csv"), index=False)
    county_summary.to_csv(os.path.join(OUT_DIR, "high_risk_by_county.csv"), index=False)
    delays_df.to_csv(os.path.join(OUT_DIR, "high_risk_delays_by_city.csv"), index=False)
    
    print("\n" + "="*70)
    print("Results saved to:")
    print(f"  - {os.path.join(OUT_DIR, 'high_risk_by_city.csv')}")
    print(f"  - {os.path.join(OUT_DIR, 'high_risk_by_county.csv')}")
    print(f"  - {os.path.join(OUT_DIR, 'high_risk_delays_by_city.csv')}")
    print("="*70)

if __name__ == "__main__":
    analyze_risk_by_location()
