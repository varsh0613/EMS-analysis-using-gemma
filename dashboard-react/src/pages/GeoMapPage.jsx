import React, { useState, useEffect } from "react";
import { fetchOpCitySummary, fetchGeoHotspotTable } from "../api/gemmaApi";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function H3GeoMap() {
  const [kpi, setKpi] = useState({
    totalHexes: 0,
    maxIncidents: 0,
    maxHex: null,
    maxPlace: null,
    avgOnScene: 0,
  });
  
  const [citySummary, setCitySummary] = useState([]);
  const [hotspotTable, setHotspotTable] = useState([]);

  useEffect(() => {
    fetchOpCitySummary()
      .then(data => {
        if (!data) return;
        // Ensure sorting highest → lowest
        const sorted = [...data].sort((a, b) => b.incidents - a.incidents);
        setCitySummary(sorted);
      })
      .catch(console.error);

    fetchGeoHotspotTable(10)
      .then(response => {
        if (response?.data) {
          setHotspotTable(response.data);
        }
      })
      .catch(console.error);
  }, []);



  // simple mapping H3 → place name
  const hexToPlace = (hex) => {
    const map = {
      "882830ba27fffff": "San Rafael",
      // Add more if needed
    };
    return map[hex] || "Unknown Area";
  };

  useEffect(() => {
    fetch("http://127.0.0.1:8000/geo/summary")
      .then(res => res.json())
      .then(data => {
        const hexes = data.features || [];

        let maxInc = 0;
        let maxHex = null;
        let totalTime = 0;
        let timeCount = 0;

        hexes.forEach(f => {
          const p = f.properties || {};
          const inc = Number(p.incidents || 0);

          if (inc > maxInc) {
            maxInc = inc;
            maxHex = p.h3 || null;
          }

          if (p.avg_on_scene != null && p.avg_on_scene !== "") {
            totalTime += Number(p.avg_on_scene);
            timeCount += 1;
          }
        });

        setKpi({
          totalHexes: hexes.length,
          maxIncidents: maxInc,
          maxHex,
          maxPlace: maxHex ? hexToPlace(maxHex) : null,
          avgOnScene: timeCount ? (totalTime / timeCount).toFixed(1) : 0,
        });
      })
      .catch(console.error);
  }, []);

  const pageStyle = {
    width: "100%",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "24px",
    boxSizing: "border-box",
  };

  const headingStyle = {
    fontSize: "22px",
    fontWeight: "700",
    color: "#6b21a8",
    marginBottom: "4px",
  };

  const cardsRowStyle = {
    display: "flex",
    gap: "12px",
    flexWrap: "nowrap",
  };

  const cardStyle = {
    flex: 1,
    backgroundColor: "#ffffff",
    borderLeft: "6px solid #7b5ea3",
    borderRadius: "12px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    padding: "16px",
    textAlign: "center",
  };

  const titleStyle = {
    fontSize: "15px",
    fontWeight: "600",
    marginBottom: "6px",
    color: "#6b21a8",
  };

  const valueStyle = {
    fontSize: "19px",
    fontWeight: "700",
    margin: "0",
    color: "#111827",
  };

  const smallText = {
    fontSize: "13px",
    color: "#374151",
    marginTop: "4px",
  };

  const mapContainerStyle = {
    width: "100%",
    height: "90vh",
    minHeight: "600px",
    borderRadius: "16px",
    overflow: "hidden",
    boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
  };

  const tableContainerStyle = {
    width: "100%",
    backgroundColor: "#ffffff",
    borderRadius: "16px",
    boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
    overflow: "hidden",
  };

  const tableStyle = {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  };

  const thStyle = {
    backgroundColor: "#7b5ea3",
    color: "#ffffff",
    padding: "12px 16px",
    textAlign: "left",
    fontWeight: "600",
  };

  const tdStyle = {
    padding: "12px 16px",
    borderBottom: "1px solid #e5e7eb",
  };

  const rankStyle = {
    ...tdStyle,
    fontWeight: "600",
    color: "#7b5ea3",
  };

  return (
    <div style={pageStyle}>
      <h1 style={{ color: "#7b5ea3", fontSize: "32px", fontWeight: 700 }}>
        Geospatial Analysis
      </h1>

      {/* KPI Cards Row */}
      <div style={cardsRowStyle}>
        <div style={cardStyle}>
          <div style={titleStyle}>Most Incident Place</div>
          <div style={valueStyle}>{kpi.maxPlace || "—"}</div>
          <div style={smallText}>Incidents: {kpi.maxIncidents}</div>
        </div>

        <div style={cardStyle}>
          <div style={titleStyle}>Average On-Scene (mins)</div>
          <div style={valueStyle}>{kpi.avgOnScene}</div>
        </div>

        <div style={cardStyle}>
          <div style={titleStyle}>Total Hexes</div>
          <div style={valueStyle}>{kpi.totalHexes}</div>
        </div>
      </div>

      {/* Map */}
      <div style={mapContainerStyle}>
        <iframe
          src="/ems_h3_map.html"
          title="H3 Geo Map"
          style={{ width: "100%", height: "100%", border: 0 }}
        />
      </div>

      {/* Hotspot Table */}
      <div style={{ marginTop: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: "700", color: "#7b5ea3", marginBottom: "16px" }}>
          Top Incident Hotspots
        </h2>
        <div style={tableContainerStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Rank</th>
                <th style={thStyle}>H3 Cell ID</th>
                <th style={thStyle}>City</th>
                <th style={thStyle}>Total Incidents</th>
                <th style={thStyle}>Avg. On-Scene Time (min)</th>
              </tr>
            </thead>
            <tbody>
              {hotspotTable.length > 0 ? (
                hotspotTable.map((row, idx) => (
                  <tr key={idx}>
                    <td style={rankStyle}>{row.rank}</td>
                    <td style={tdStyle}>{row.h3_cell_id}</td>
                    <td style={tdStyle}>{row.city}</td>
                    <td style={tdStyle}>{row.total_incidents.toLocaleString()}</td>
                    <td style={tdStyle}>{row.avg_on_scene_time_min.toFixed(2)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" style={{ ...tdStyle, textAlign: "center", color: "#999" }}>
                    Loading data...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
