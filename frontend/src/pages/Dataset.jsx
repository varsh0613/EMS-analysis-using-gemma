// src/pages/DatasetPage.jsx
import React from "react";
import DatasetViewer from "../components/DatasetViewer";

const DatasetPage = () => {
  return (
    <div style={{
      fontFamily: "'Segoe UI', sans-serif",
      backgroundColor: "#f9f9f9",
      minHeight: "100vh",
      padding: 40
    }}>

      {/* Header */}
      <header style={{ textAlign: "center", marginBottom: 30 }}>
        <h1 style={{ fontSize: 36, color: "#7b5ea3", marginBottom: 10 }}>EMS Dataset Overview</h1>
        <p style={{ maxWidth: 800, margin: "0 auto", color: "#333", fontSize: 16, lineHeight: 1.6 }}>
          This dataset contains detailed records of emergency medical service (EMS) incidents including incident types, locations, patient impressions, and response times. It provides a comprehensive view of EMS operations for analysis and reporting.
        </p>
      </header>

      {/* Dataset Table */}
      <section>
        <DatasetViewer />
      </section>
    </div>
  );
};

export default DatasetPage;
