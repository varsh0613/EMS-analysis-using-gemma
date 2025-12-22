// src/components/DatasetViewer.jsx
import React, { useState, useEffect } from "react";
import { fetchDatasetPage } from "../api/gemmaApi";

const DatasetViewer = ({ defaultPageSize = 25 }) => {
  const [data, setData] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(defaultPageSize);
  const [totalRows, setTotalRows] = useState(0);
  const [search, setSearch] = useState("");

  const fetchData = async () => {
    const res = await fetchDatasetPage(page, limit);
    setData(res.rows || []);
    setTotalRows(res.total_rows || 0);
  };

  useEffect(() => { fetchData(); }, [page, limit]);

  const filteredData = data.filter(row =>
    Object.values(row).some(val =>
      String(val).toLowerCase().includes(search.toLowerCase())
    )
  );

  const totalPages = Math.ceil(totalRows / limit);

  return (
    <div style={{
      width: "90%",
      maxWidth: 1000,
      margin: "0 auto",
      fontFamily: "'Segoe UI', sans-serif",
      backgroundColor: "#fff",
      padding: 20,
      borderRadius: 12,
      boxShadow: "0 4px 12px rgba(0,0,0,0.08)"
    }}>

      {/* Metadata Cards */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        {/* Total Records */}
        <div style={{
          flex: "1 1 200px",
          backgroundColor: "#e5dbf7",
          padding: 16,
          borderRadius: 12,
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
        }}>
          <h3 style={{ margin: 0, fontSize: 18, color: "#7b5ea3" }}>Total Records</h3>
          <p style={{ fontSize: 24, margin: "8px 0 0", color: "#333" }}>{totalRows}</p>
        </div>

        {/* Timeline */}
        <div style={{
          flex: "1 1 200px",
          backgroundColor: "#e5dbf7",
          padding: 16,
          borderRadius: 12,
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
        }}>
          <h3 style={{ margin: 0, fontSize: 18, color: "#7b5ea3" }}>Timeline</h3>
          <p style={{ fontSize: 20, margin: "8px 0 0", color: "#333" }}>March 2013 → April 2021</p>
        </div>

        {/* Data Provider */}
        <div style={{
          flex: "1 1 200px",
          backgroundColor: "#e5dbf7",
          padding: 16,
          borderRadius: 12,
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
        }}>
          <h3 style={{ margin: 0, fontSize: 18, color: "#7b5ea3" }}>Data Provider</h3>
          <p style={{ fontSize: 20, margin: "8px 0 0", color: "#333" }}>County of Marin, CA</p>
        </div>
      </div>

      {/* Search + Rows per page */}
<div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 10, flexWrap: "wrap", gap: 10 }}>
  <input
    type="text"
    placeholder="Search..."
    value={search}
    onChange={e => setSearch(e.target.value)}
    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ccc", flex: 1, minWidth: 200 }}
  />
  <select
    value={limit}
    onChange={e => { setLimit(Number(e.target.value)); setPage(1); }}
    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ccc", backgroundColor: "#fff" }}
  >
    {[10, 25, 50].map(opt => <option key={opt} value={opt}>{opt} rows</option>)}
  </select>
</div>

      {/* Table */}
      <div style={{ overflow: "auto", height: 490, borderRadius: 8, border: "1px solid #ccc" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14, color: "#333" }}>
          <thead style={{ position: "sticky", top: 0, backgroundColor: "#f0f0f0", zIndex: 1 }}>
            <tr>
              {data[0] && Object.keys(data[0]).map(col => (
                <th key={col} style={{ padding: 10, textAlign: "left", borderBottom: "1px solid #ccc" }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, idx) => (
              <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                {Object.values(row).map((val, i) => (
                  <td key={i} style={{ padding: 10 }}>{val}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <button
          onClick={() => setPage(p => Math.max(p - 1, 1))}
          disabled={page === 1}
          style={{ padding: "6px 14px", borderRadius: 8, border: "none", backgroundColor: "#7b5ea3", color: "#fff", cursor: page === 1 ? "not-allowed" : "pointer" }}
        >
          Prev
        </button>
        <span style={{ fontSize: 14, color: "#333" }}>Page {page} of {totalPages}</span>
        <button
          onClick={() => setPage(p => Math.min(p + 1, totalPages))}
          disabled={page === totalPages}
          style={{ padding: "6px 14px", borderRadius: 8, border: "none", backgroundColor: "#7b5ea3", color: "#fff", cursor: page === totalPages ? "not-allowed" : "pointer" }}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default DatasetViewer;
