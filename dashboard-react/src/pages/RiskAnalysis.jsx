import React, { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, LineChart, Line,
    PieChart, Pie, Cell, Legend, Label, LabelList, ComposedChart
} from "recharts";
import {
    fetchRiskTopProtocols,
    fetchRiskTopPrimaryImpressions,
    fetchConfusionMatrixCSV,
    fetchClassifierReportText,
    fetchRiskLabelDistribution,
    fetchOpPeakRiskHours,
    fetchOpRiskByHour,
    fetchRiskHighRiskByCity,
    fetchRiskHighRiskDelaysByCity
} from "../api/gemmaApi";

const COLORS = {
    HIGH: "#8B7FD8",
    MEDIUM: "#BA68C8",
    LOW: "#E1BEE7"
};

const cardStyle = {
    background: "#fff",
    padding: 20,
    borderRadius: 10,
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    transition: "all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    cursor: "default"
};

const cardHoverStyle = {
    ...cardStyle,
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
    transform: "translateY(-4px)"
};



// Custom label renderer for pie chart
const renderCustomLabel = ({ name, value }) => {
    return `${name}: ${value.toLocaleString()}`;
};

// Custom 3D Interactive Pie Chart Component
const InteractivePieChart = ({ data, colors }) => {
    const [hoveredIndex, setHoveredIndex] = useState(null);

    return (
        <div style={{ perspective: "1200px", width: "100%", height: "100%" }}>
            <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={renderCustomLabel}
                        labelPosition="outside"
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                        isAnimationActive={false}
                        onMouseEnter={(_, index) => setHoveredIndex(index)}
                        onMouseLeave={() => setHoveredIndex(null)}
                    >
                        {data.map((entry, idx) => (
                            <Cell
                                key={`cell-${idx}`}
                                fill={colors[entry.name]}
                                style={{
                                    transition: "all 0.3s ease",
                                    filter: hoveredIndex === idx ? "brightness(1.15) drop-shadow(0 8px 16px rgba(0,0,0,0.25))" : "brightness(1) drop-shadow(0 2px 4px rgba(0,0,0,0.1))",
                                    transform: hoveredIndex === idx ? "scale(1.08)" : "scale(1)",
                                    transformOrigin: "50% 50%"
                                }}
                            />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value) => value.toLocaleString()}
                        contentStyle={{
                            background: "rgba(255, 255, 255, 0.95)",
                            border: "2px solid #ddd",
                            borderRadius: "8px",
                            padding: "10px",
                            boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
                        }}
                    />
                    <Legend
                        verticalAlign="bottom"
                        height={36}
                        wrapperStyle={{ paddingTop: "20px" }}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};

export default function RiskDashboard() {
    const [topProtocols, setTopProtocols] = useState({});
    const [topImpressions, setTopImpressions] = useState({});
    const [confMatrix, setConfMatrix] = useState([]);
    const [classReport, setClassReport] = useState("");
    const [riskFilter, setRiskFilter] = useState("ALL");
    const [labelDist, setLabelDist] = useState({ HIGH: 0, MEDIUM: 0, LOW: 0 });
    const [hoveredCard, setHoveredCard] = useState(null);
    const [peakRiskHours, setPeakRiskHours] = useState({});
    const [riskByHour, setRiskByHour] = useState([]);
    const [highRiskByCity, setHighRiskByCity] = useState([]);
    const [highRiskDelaysByCity, setHighRiskDelaysByCity] = useState([]);

    useEffect(() => {
        fetchRiskTopProtocols().then(data => setTopProtocols(typeof data === 'object' ? data : {}));
        fetchRiskTopPrimaryImpressions().then(data => setTopImpressions(typeof data === 'object' ? data : {}));
        fetchRiskLabelDistribution().then(data => setLabelDist(typeof data === 'object' ? data : { HIGH: 0, MEDIUM: 0, LOW: 0 }));

        fetchConfusionMatrixCSV().then(csv => {
            if (!csv) return;
            const rows = csv.trim().split("\n").map(r => r.split(",").map(v => v.trim()));
            setConfMatrix(rows);
        });

        fetchClassifierReportText().then(setClassReport);
        fetchOpPeakRiskHours().then(setPeakRiskHours);
        fetchOpRiskByHour().then(data => {
            // Sort by hour chronologically (0-23)
            if (Array.isArray(data)) {
                data.sort((a, b) => {
                    const hourA = parseInt(a.hour.split(":")[0]);
                    const hourB = parseInt(b.hour.split(":")[0]);
                    return hourA - hourB;
                });
            }
            setRiskByHour(data);
        });
        fetchRiskHighRiskByCity().then(data => setHighRiskByCity(Array.isArray(data) ? data : []));
        fetchRiskHighRiskDelaysByCity().then(data => setHighRiskDelaysByCity(Array.isArray(data) ? data : []));
    }, []);

    // ===== KPI COUNTS - Use actual label distribution =====
    const riskCounts = {
        HIGH: labelDist.HIGH || 0,
        MEDIUM: labelDist.MEDIUM || 0,
        LOW: labelDist.LOW || 0
    };

    const totalIncidents = riskCounts.HIGH + riskCounts.MEDIUM + riskCounts.LOW;

    // ===== RISK DISTRIBUTION PIE =====
    const riskDistData = ["HIGH", "MEDIUM", "LOW"]
        .map(label => ({
            name: label,
            value: riskCounts[label] || 0
        }))
        .filter(d => d.value > 0);



    // ===== TOP PROTOCOLS BY RISK =====
    const getProtocolsForRisk = (risk) => {
        if (risk === "ALL") {
            const combined = [];
            ["HIGH", "MEDIUM", "LOW"].forEach(label => {
                if (topProtocols[label]) {
                    combined.push(...topProtocols[label]);
                }
            });
            const grouped = {};
            combined.forEach(item => {
                const key = item.Protocol_Used_by_EMS_Personnel;
                grouped[key] = (grouped[key] || 0) + item.count;
            });
            return Object.entries(grouped)
                .map(([name, count]) => ({ name, count }))
                .sort((a, b) => b.count - a.count)
                .slice(0, 5);
        }
        return (topProtocols[risk] || []).slice(0, 5).map(p => ({
            name: p.Protocol_Used_by_EMS_Personnel,
            count: p.count
        }));
    };

    // ===== TOP IMPRESSIONS BY RISK - Filter out Unknown =====
    const getImpressionsForRisk = (risk) => {
        let data = [];
        if (risk === "ALL") {
            const combined = [];
            ["HIGH", "MEDIUM", "LOW"].forEach(label => {
                if (topImpressions[label]) {
                    combined.push(...topImpressions[label]);
                }
            });
            const grouped = {};
            combined.forEach(item => {
                const key = item.primary_impression;
                grouped[key] = (grouped[key] || 0) + item.count;
            });
            data = Object.entries(grouped)
                .map(([name, count]) => ({ name, count }))
                .sort((a, b) => b.count - a.count);
        } else {
            data = (topImpressions[risk] || []).map(p => ({
                name: p.primary_impression,
                count: p.count
            }));
        }

        // Filter out "Unknown" and show "N/A" if empty
        data = data.filter(d => d.name && d.name.toLowerCase() !== "unknown");
        return data.slice(0, 5).length > 0 ? data.slice(0, 5) : [{ name: "N/A", count: 0 }];
    };

    const protocolData = getProtocolsForRisk(riskFilter);
    const impressionData = getImpressionsForRisk(riskFilter);

    // ===== PARSE CLASSIFICATION REPORT =====
    const parseClassReport = () => {
        if (!classReport) return {};
        const lines = classReport.split("\n");
        const reportObj = {};

        lines.forEach(line => {
            const match = line.match(/^\s*(HIGH|MEDIUM|LOW)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
            if (match) {
                const [, label, precision, recall, f1, support] = match;
                reportObj[label] = {
                    precision: parseFloat(precision),
                    recall: parseFloat(recall),
                    f1: parseFloat(f1),
                    support: parseInt(support)
                };
            }
        });
        return reportObj;
    };

    const reportData = parseClassReport();
    const reportTableData = ["HIGH", "MEDIUM", "LOW"]
        .map(label => ({
            label,
            precision: reportData[label]?.precision.toFixed(3) || "N/A",
            recall: reportData[label]?.recall.toFixed(3) || "N/A",
            f1: reportData[label]?.f1.toFixed(3) || "N/A",
            support: reportData[label]?.support || "N/A"
        }))
        .filter(r => r.precision !== "N/A");

    return (
        <div style={{ maxWidth: 1600, margin: "0 auto", padding: 30, fontFamily: "Arial, sans-serif", background: "#f8f9fa" }}>
            <h1 style={{ marginBottom: 30, color: "#333" }}>Risk Analysis Dashboard</h1>

            {/* ===== 1. KPI CARDS ===== */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 15, marginBottom: 30 }}>
                <div
                    style={hoveredCard === "total" ? cardHoverStyle : cardStyle}
                    onMouseEnter={() => setHoveredCard("total")}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <h3 style={{ margin: "0 0 10px 0", color: "#666", fontSize: "14px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>Total Incidents</h3>
                    <p style={{ fontSize: 36, fontWeight: "bold", margin: 0, color: "#333" }}>{totalIncidents.toLocaleString()}</p>
                </div>
                {["HIGH", "MEDIUM", "LOW"].map(label => (
                    <div
                        key={label}
                        style={{
                            ...cardStyle,
                            ...(hoveredCard === label ? cardHoverStyle : {}),
                            borderLeft: `5px solid ${COLORS[label]}`
                        }}
                        onMouseEnter={() => setHoveredCard(label)}
                        onMouseLeave={() => setHoveredCard(null)}
                    >
                        <h3 style={{ margin: "0 0 10px 0", color: "#666", fontSize: "14px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</h3>
                        <p style={{ fontSize: 36, fontWeight: "bold", margin: 0, color: COLORS[label] }}>{riskCounts[label].toLocaleString()}</p>
                    </div>
                ))}
            </div>

            {/* ===== 2. RISK DISTRIBUTION PIE CHART ===== */}
            <div
                style={{ ...cardStyle, marginBottom: 30 }}
                onMouseEnter={() => setHoveredCard("distribution")}
                onMouseLeave={() => setHoveredCard(null)}
            >
                <h2 style={{ marginTop: 0, color: "#333" }}>Risk Distribution</h2>
                <InteractivePieChart data={riskDistData} colors={COLORS} />
            </div>

            {/* ===== 3. RISK FILTER + TOP PROTOCOLS & IMPRESSIONS ===== */}
            <div style={{ marginBottom: 30 }}>
                <div style={{ marginBottom: 20 }}>
                    <label style={{ marginRight: 10, fontWeight: "bold", color: "#333" }}>Filter by Risk:</label>
                    {["ALL", "HIGH", "MEDIUM", "LOW"].map(label => {
                        const isActive = riskFilter === label;
                        const [btnHovered, setBtnHovered] = React.useState(false);
                        return (
                            <button
                                key={label}
                                onClick={() => setRiskFilter(label)}
                                style={{
                                    marginRight: 10,
                                    marginBottom: 10,
                                    padding: "10px 20px",
                                    borderRadius: 6,
                                    border: "none",
                                    background: isActive ? (COLORS[label] || "#7C4DFF") : (btnHovered ? "#d0d0d0" : "#e0e0e0"),
                                    color: isActive ? "white" : "#333",
                                    cursor: "pointer",
                                    fontWeight: isActive ? "bold" : "500",
                                    transition: "all 0.2s ease",
                                    transform: btnHovered && !isActive ? "translateY(-1px)" : "none",
                                    boxShadow: isActive ? "0 4px 12px rgba(0,0,0,0.15)" : (btnHovered ? "0 2px 8px rgba(0,0,0,0.1)" : "none")
                                }}
                                onMouseEnter={() => setBtnHovered(true)}
                                onMouseLeave={() => setBtnHovered(false)}
                            >
                                {label}
                            </button>
                        );
                    })}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                    {/* Top 5 Protocols */}
                    <div
                        style={{ ...cardStyle }}
                        onMouseEnter={() => setHoveredCard("protocols")}
                        onMouseLeave={() => setHoveredCard(null)}
                    >
                        <h3 style={{ marginTop: 0, color: "#333" }}>Top 5 Protocols</h3>
                        {protocolData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={310}>
                                <BarChart
                                    layout="vertical"
                                    data={protocolData}
                                    margin={{ left: 0, right: 50, top: 5, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis type="number" />
                                    <YAxis dataKey="name" type="category" width={145} />
                                    <Tooltip formatter={(value) => value.toLocaleString()} />
                                    <Bar dataKey="count" fill="#7C4DFF" radius={[0, 8, 8, 0]} isAnimationActive={false} maxBarSize={50}>
                                        <LabelList dataKey="count" position="right" fill="#333" fontSize={12} fontWeight={600} offset={5} />
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <p style={{ color: "#999" }}>No data for selected risk</p>
                        )}
                    </div>

                    {/* Top 5 Primary Impressions */}
                    <div
                        style={{ ...cardStyle }}
                        onMouseEnter={() => setHoveredCard("impressions")}
                        onMouseLeave={() => setHoveredCard(null)}
                    >
                        <h3 style={{ marginTop: 0, color: "#333" }}>Top 5 Primary Impressions</h3>
                        {impressionData.length > 0 && impressionData[0].name !== "N/A" ? (
                            <ResponsiveContainer width="100%" height={310}>
                                <BarChart
                                    layout="vertical"
                                    data={impressionData}
                                    margin={{ left: 0, right: 50, top: 5, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis type="number" />
                                    <YAxis dataKey="name" type="category" width={145} />
                                    <Tooltip formatter={(value) => value.toLocaleString()} />
                                    <Bar dataKey="count" fill="#CE93D8" radius={[0, 8, 8, 0]} isAnimationActive={false} maxBarSize={50}>
                                        <LabelList dataKey="count" position="right" fill="#333" fontSize={12} fontWeight={600} offset={5} />
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <p style={{ color: "#999" }}>No data for selected risk</p>
                        )}
                    </div>
                </div>
            </div>

            {/* ===== 4. CRITICAL WINDOWS: HIGH-RISK + DELAYS ===== */}
            <div
                style={{ ...cardStyle, marginBottom: 30, borderLeft: "5px solid #C64545" }}
                onMouseEnter={() => setHoveredCard("criticalWindows")}
                onMouseLeave={() => setHoveredCard(null)}
            >
                <h2 style={{ marginTop: 0, color: "#C64545" }}>Critical Windows: High-Risk Cases with Delays</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
                    <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Worst Hour (High-Risk + Delays)</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#C64545' }}>
                            {peakRiskHours.worst_hour_for_high_risk || '--'}
                        </div>
                    </div>
                    <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Total High-Risk Cases</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#666' }}>
                            {peakRiskHours.total_high_risk_incidents?.toLocaleString() || '--'}
                        </div>
                    </div>
                    <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Delayed High-Risk Cases</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#C64545' }}>
                            {peakRiskHours.total_delayed_high_risk?.toLocaleString() || '--'} ({peakRiskHours.delayed_high_risk_pct}%)
                        </div>
                    </div>
                </div>

                {peakRiskHours.critical_windows && peakRiskHours.critical_windows.length > 0 && (
                    <div>
                        <h3 style={{ margin: '12px 0 12px 0', fontSize: '14px', color: '#333' }}>High-Risk + Delayed by Hour (Top Risk Windows)</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '8px' }}>
                            {peakRiskHours.critical_windows.slice(0, 12).map((window, idx) => (
                                <div key={idx} style={{ padding: '10px', backgroundColor: '#FBE9E7', borderRadius: '6px', border: '1px solid #C64545' }}>
                                    <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#C64545' }}>{window.hour}</div>
                                    <div style={{ fontSize: '11px', color: '#333', marginTop: '4px' }}>
                                        High: {window.high_risk_incidents}
                                    </div>
                                    <div style={{ fontSize: '11px', color: '#C64545', fontWeight: '600' }}>
                                        Delayed: {window.delayed_high_risk_incidents} ({window.delayed_pct}%)
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* ===== RISK DISTRIBUTION BY HOUR ===== */}
            <div
                style={{ ...cardStyle, marginBottom: 30 }}
                onMouseEnter={() => setHoveredCard("riskByHour")}
                onMouseLeave={() => setHoveredCard(null)}
            >
                <h2 style={{ marginTop: 0, color: "#333" }}>High-Risk Cases by Hour with Delay %</h2>
                <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={riskByHour}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                        <YAxis yAxisId="left" label={{ value: 'High-Risk Count', angle: -90, position: 'insideLeft' }} />
                        <YAxis yAxisId="right" orientation="right" label={{ value: 'Delayed %', angle: -90, position: 'insideRight' }} />
                        <Tooltip />
                        <Legend />
                        <Bar yAxisId="left" dataKey="high_risk_count" fill="#8B7FD8" name="High-Risk Cases" />
                        <Line yAxisId="right" type="monotone" dataKey="delayed_pct" stroke="#BA68C8" strokeWidth={2} name="Delayed %" />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* ===== 6. HIGH-RISK BY LOCATION ===== */}
            <div style={{ marginBottom: 30 }}>
                <h2 style={{ color: "#333", marginBottom: 20 }}>High-Risk Cases by City</h2>
                
                <div
                    style={{ ...cardStyle, marginBottom: 20 }}
                    onMouseEnter={() => setHoveredCard("riskByCity")}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <h3 style={{ marginTop: 0, color: "#333" }}>Top 15 Cities by High-Risk Cases</h3>
                    {highRiskByCity.length > 0 ? (
                        <ResponsiveContainer width="100%" height={400}>
                            <BarChart
                                layout="vertical"
                                data={highRiskByCity.slice(0, 15)}
                                margin={{ left: 0, right: 50, top: 5, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis type="number" />
                                <YAxis dataKey="City" type="category" width={120} tick={{ fontSize: 12 }} />
                                <Tooltip 
                                    formatter={(value) => value.toLocaleString()}
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            const data = payload[0].payload;
                                            return (
                                                <div style={{ background: "#fff", padding: "8px", borderRadius: "4px", border: "1px solid #ddd" }}>
                                                    <p style={{ margin: "0 0 4px 0", fontSize: "12px" }}><strong>{data.City}</strong></p>
                                                    <p style={{ margin: "0 0 4px 0", fontSize: "12px" }}>High-Risk: {data.High_Risk_Count}</p>
                                                    <p style={{ margin: "0 0 4px 0", fontSize: "12px" }}>Total: {data.Total_Cases_in_City}</p>
                                                    <p style={{ margin: "0", fontSize: "12px", color: "#C64545", fontWeight: "bold" }}>{data.High_Risk_Percentage}% high-risk</p>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                <Bar dataKey="High_Risk_Count" fill="#8B7FD8" radius={[0, 8, 8, 0]} isAnimationActive={false} maxBarSize={50}>
                                    <LabelList dataKey="High_Risk_Count" position="right" fill="#333" fontSize={11} fontWeight={600} offset={5} />
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p style={{ color: "#999" }}>No data available</p>
                    )}
                </div>

                {/* Response Delays by City */}
                <div
                    style={{ ...cardStyle }}
                    onMouseEnter={() => setHoveredCard("riskDelays")}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <h3 style={{ marginTop: 0, color: "#333" }}>Response Delays in High-Risk Cases by City (Top 10)</h3>
                    {highRiskDelaysByCity.length > 0 ? (
                        <div style={{ overflowX: "auto" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                                <thead>
                                    <tr style={{ background: "#f0f0f0" }}>
                                        <th style={{ padding: "10px", textAlign: "left", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>City</th>
                                        <th style={{ padding: "10px", textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>High-Risk Count</th>
                                        <th style={{ padding: "10px", textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Avg Response (min)</th>
                                        <th style={{ padding: "10px", textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Avg Turnout (min)</th>
                                        <th style={{ padding: "10px", textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Avg On-Scene (min)</th>
                                        <th style={{ padding: "10px", textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Avg Call Cycle (min)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {highRiskDelaysByCity.map((row, i) => (
                                        <tr key={i} style={{ background: i % 2 === 0 ? "#f9f9f9" : "#fff" }}>
                                            <td style={{ padding: "10px", borderBottom: "1px solid #ddd", fontWeight: "bold", color: "#C64545" }}>{row.City}</td>
                                            <td style={{ padding: "10px", textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.High_Risk_Count}</td>
                                            <td style={{ padding: "10px", textAlign: "center", borderBottom: "1px solid #ddd", color: row.Avg_Response_Time_min > 10 ? "#C64545" : "#333" }}>
                                                {row.Avg_Response_Time_min}
                                            </td>
                                            <td style={{ padding: "10px", textAlign: "center", borderBottom: "1px solid #ddd", color: row.Avg_Turnout_Time_min > 2 ? "#C64545" : "#333" }}>
                                                {row.Avg_Turnout_Time_min}
                                            </td>
                                            <td style={{ padding: "10px", textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.Avg_On_Scene_Time_min}</td>
                                            <td style={{ padding: "10px", textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.Avg_Call_Cycle_Time_min}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <p style={{ color: "#999" }}>No data available</p>
                    )}
                </div>
            </div>

            {/* ===== 5. MODEL DIAGNOSTICS ===== */}
            <div style={{ marginTop: 40 }}>
                <h2 style={{ color: "#333" }}>Model Diagnostics & Performance</h2>

                {/* A. Confusion Matrix Heatmap */}
                {confMatrix.length > 0 && (
                    <div
                        style={{ ...cardStyle, marginBottom: 20 }}
                        onMouseEnter={() => setHoveredCard("confusion")}
                        onMouseLeave={() => setHoveredCard(null)}
                    >
                        <h3 style={{ marginTop: 0, color: "#333" }}>Confusion Matrix</h3>
                        <Plot
                            data={[{
                                z: confMatrix.slice(1).map(row => row.slice(1).map(c => Number(c) || 0)),
                                x: confMatrix[0].slice(1),
                                y: confMatrix.slice(1).map(r => r[0]),
                                type: "heatmap",
                                colorscale: [[0, "#F3E5F5"], [1, "#8B7FD8"]],
                                text: confMatrix.slice(1).map(row => row.slice(1).map(c => Number(c) || 0)),
                                texttemplate: "%{text}",
                                textfont: { size: 14, color: "#333" },
                                hovertemplate: "<b>Actual: %{y}</b><br>Predicted: %{x}<br>Count: %{z}<extra></extra>"
                            }]}
                            layout={{
                                title: "Predicted vs Actual Risk Labels",
                                xaxis: { title: "Predicted" },
                                yaxis: { title: "Actual" },
                                height: 400,
                                margin: { l: 100, r: 50, b: 100, t: 80 }
                            }}
                        />
                    </div>
                )}

                {/* B. Classification Report Table */}
                {reportTableData.length > 0 && (
                    <div
                        style={{ ...cardStyle }}
                        onMouseEnter={() => setHoveredCard("report")}
                        onMouseLeave={() => setHoveredCard(null)}
                    >
                        <h3 style={{ marginTop: 0, color: "#333" }}>Classification Report</h3>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                                <tr style={{ background: "#f0f0f0" }}>
                                    <th style={{ padding: 12, textAlign: "left", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Risk Level</th>
                                    <th style={{ padding: 12, textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Precision</th>
                                    <th style={{ padding: 12, textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Recall</th>
                                    <th style={{ padding: 12, textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>F1-Score</th>
                                    <th style={{ padding: 12, textAlign: "center", borderBottom: "2px solid #ddd", fontWeight: "bold" }}>Support</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reportTableData.map((row, i) => (
                                    <tr key={i} style={{ background: i % 2 === 0 ? "#f9f9f9" : "#fff" }}>
                                        <td style={{ padding: 12, borderBottom: "1px solid #ddd", fontWeight: "bold", color: COLORS[row.label] }}>{row.label}</td>
                                        <td style={{ padding: 12, textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.precision}</td>
                                        <td style={{ padding: 12, textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.recall}</td>
                                        <td style={{ padding: 12, textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.f1}</td>
                                        <td style={{ padding: 12, textAlign: "center", borderBottom: "1px solid #ddd" }}>{row.support}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
