import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";

import Dataset from "./pages/Dataset";
import EDA from "./pages/EDA";
import GeoMapPage from "./pages/GeoMapPage";
import OperationalEfficiency from "./pages/OperationalEfficiency";
import RiskAnalysis from "./pages/RiskAnalysis";
import GemmaChatbot from "./pages/GemmaChatbot"; // <- make this page

function App() {
  const menuItems = [
    { label: "Dataset", path: "/dataset" },
    { label: "EDA", path: "/eda" },
    { label: "Geo Hotspot Map", path: "/geo" },
    { label: "Operational Efficiency", path: "/operational-efficiency" },
    { label: "Risk Analysis", path: "/risk-analysis" },
    { label: "Gemma Chatbot", path: "/chatbot" }, // <- added
  ];

  return (
    <Router>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar menu={menuItems} />
        <div style={{ flex: 1, padding: "20px" }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dataset" replace />} />
            <Route path="/dataset" element={<Dataset />} />
            <Route path="/eda" element={<EDA />} />
            <Route path="/geo" element={<GeoMapPage />} />
            <Route path="/operational-efficiency" element={<OperationalEfficiency />} />
            <Route path="/risk-analysis" element={<RiskAnalysis />} />
            <Route path="/chatbot" element={<GemmaChatbot />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
