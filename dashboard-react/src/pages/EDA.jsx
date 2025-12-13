import React, { useEffect, useState } from "react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    LineChart, Line, ResponsiveContainer,
    PieChart, Pie, Legend, Cell, LabelList
} from "recharts";
import {
    fetchAgeDistribution,
    fetchGenderDistribution,
    fetchIncidentPlaces,
    fetchPrimaryImpressionCounts,
    fetchTransportDestinations,
    fetchCallsPerHour,
    fetchIncidentsPerDay,
    fetchMonthlyTrends,
    fetchYearDistribution,
    fetchKpis
} from "../api/gemmaApi";

// ---------------- KPI CARD ----------------
function KpiCard({ title, value }) {
    return (
        <div style={{
            background: "#f3e8ff",
            borderRadius: "14px",
            padding: "18px",
            flex: "1 1 200px",
            margin: "10px",
            textAlign: "center",
            boxShadow: "0 4px 8px rgba(0,0,0,0.08)",
        }}>
            <h4 style={{ margin: 0, color: "#6b21a8", fontWeight: 600 }}>{title}</h4>
            <p style={{
                fontSize: "26px",
                margin: "12px 0 0",
                color: "#111827",
                fontWeight: 500
            }}>
                {value ?? "—"}
            </p>
        </div>
    );
}

// ---------------- CHART CARD ----------------
function ChartCard({ title, height = 350, children }) {
    return (
        <div style={{
            background: "#faf5ff",
            borderRadius: "14px",
            padding: "20px",
            margin: "10px",
            boxShadow: "0 4px 8px rgba(0,0,0,0.05)",
            width: "100%"
        }}>
            <h4 style={{ margin: "0 0 12px", color: "#6b21a8", fontWeight: 600 }}>
                {title}
            </h4>
            <div style={{ width: "100%", height, minHeight: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                    {children}
                </ResponsiveContainer>
            </div>
        </div>
    );
}

// ---------------- EDA PAGE ----------------
export default function EDA() {
    const [summary, setSummary] = useState({});
    const [ageDist, setAgeDist] = useState([]);
    const [genderDist, setGenderDist] = useState([]);
    const [incidentPlaces, setIncidentPlaces] = useState([]);
    const [impressions, setImpressions] = useState([]);
    const [destinations, setDestinations] = useState([]);
    const [callsHour, setCallsHour] = useState([]);
    const [incidentDay, setIncidentDay] = useState([]);
    const [incidentMonth, setIncidentMonth] = useState([]);
    const [incidentYear, setIncidentYear] = useState([]);

    useEffect(() => {
        fetchKpis().then(data => setSummary(data));

        fetchAgeDistribution().then(data => {
            if (!data) return;
            const filtered = data.filter(d => {
                const max = Number(d.bin.match(/\d+/g)?.[1] ?? 0);
                return max <= 120;
            });
            setAgeDist(filtered);
        });

        fetchGenderDistribution().then(data => {
            if (!data) return;
            const filtered = data
                .filter(d => ["male", "female"].includes(d.feature.toLowerCase()))
                .map(d => ({ gender: d.feature, count: d.value }));
            setGenderDist(filtered);
        });

        fetchIncidentPlaces().then(setIncidentPlaces);
        fetchPrimaryImpressionCounts().then(setImpressions);
        fetchTransportDestinations().then(setDestinations);
        fetchCallsPerHour().then(setCallsHour);
        fetchIncidentsPerDay().then(setIncidentDay);
        fetchMonthlyTrends().then(setIncidentMonth);
        fetchYearDistribution().then(setIncidentYear);
    }, []);

    const mostCommonInjuryPlace = summary.most_common_injury_place
        ? `${Object.keys(summary.most_common_injury_place)[0]} (${Object.values(summary.most_common_injury_place)[0]})`
        : "—";

    return (
        <div style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto", fontFamily: "Inter, sans-serif" }}>
            <h1 style={{ color: "#6b21a8", fontSize: "32px", fontWeight: 700 }}>EDA</h1>

            {/* ---------------- KPI ROW ---------------- */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "20px", justifyContent: "space-between" }}>
                <KpiCard title="Total Incidents" value={summary.total_incidents} />
                <KpiCard title="Number of Hospitals" value={summary.num_hospitals} />
                <KpiCard title="Primary Impressions" value={summary.num_primary_impressions} />
                <KpiCard title="Average Patient Age" value={summary.average_patient_age?.toFixed(1)} />
                <KpiCard title="Most Common Incident Place" value={mostCommonInjuryPlace} />
            </div>

            {/* ---------------- ROW 1 – Age + Gender ---------------- */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "32px", marginTop: "30px" }}>
                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Age Distribution" height={350}>
                        <BarChart data={ageDist} margin={{ top: 20, bottom: 20, right: 40 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="bin" />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="count" fill="rgba(167,139,250,0.5)" />
                            <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={3} dot={false} />
                        </BarChart>
                    </ChartCard>
                </div>

                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Gender Distribution" height={350}>
                        <PieChart>
                            <Pie
                                data={genderDist}
                                dataKey="count"
                                nameKey="gender"
                                cx="50%"
                                cy="50%"
                                outerRadius={120}
                                labelLine
                                label={({ percent, name, value }) => (percent > 0.05 ? `${name}: ${value}` : "")}
                            >
                                {genderDist.map((entry, index) => {
                                    const colors = ["#c4b5fd", "#a78bfa"];
                                    return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />;
                                })}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ChartCard>
                </div>
            </div>

            {/* ---------------- ROW 2 – Injury + Impressions ---------------- */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "32px", marginTop: "30px" }}>
                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Top Injury Places" height={430}>
                        <BarChart data={incidentPlaces} layout="vertical" margin={{ left: 100, right: 50 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" />
                            <YAxis type="category" dataKey="feature" width={150} />
                            <Tooltip />
                            <Bar dataKey="value" fill="#8b5cf6" isAnimationActive={false}>
                                <LabelList dataKey="value" position="right" fill="#333" fontSize={11} fontWeight={600} offset={5} />
                            </Bar>
                        </BarChart>
                    </ChartCard>
                </div>

                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Top Primary Impressions" height={430}>
                        <BarChart data={impressions} layout="vertical" margin={{ left: 100, right: 50 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" />
                            <YAxis type="category" dataKey="feature" width={150} />
                            <Tooltip />
                            <Bar dataKey="value" fill="#9333ea" isAnimationActive={false}>
                                <LabelList dataKey="value" position="right" fill="#333" fontSize={11} fontWeight={600} offset={5} />
                            </Bar>
                        </BarChart>
                    </ChartCard>
                </div>
            </div>

            {/* ---------------- ROW 3 – Patient Flow ---------------- */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", marginTop: "30px" }}>
                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Top Transport Destinations" height={430}>
                        <BarChart data={destinations} layout="vertical" margin={{ left: 100, right: 50 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" />
                            <YAxis type="category" dataKey="feature" width={150} />
                            <Tooltip />
                            <Bar dataKey="value" fill="#7e22ce" isAnimationActive={false}>
                                <LabelList dataKey="value" position="right" fill="#333" fontSize={11} fontWeight={600} offset={5} />
                            </Bar>
                        </BarChart>
                    </ChartCard>
                </div>
            </div>

            {/* ---------------- ROW 4 – Calls + Incidents per Day ---------------- */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "32px", marginTop: "30px" }}>

                {/* ---------------- Calls per Hour ---------------- */}
                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Calls per Hour" height={350}>
                        <BarChart data={callsHour} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="hour"
                                tick={{ fontSize: 12 }}
                                interval={0}
                                angle={-45}
                                textAnchor="end"
                            />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="count" fill="#a78bfa" />
                        </BarChart>
                    </ChartCard>
                </div>

                {/* ---------------- Incidents per Weekday ---------------- */}
                <div style={{ flex: 1, minWidth: 350, margin: "10px" }}>
                    <ChartCard title="Incidents per Weekday" height={350}>
                        <BarChart
                            data={incidentDay.sort((a, b) => {
                                const weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
                                return weekdays.indexOf(a.day) - weekdays.indexOf(b.day);
                            })}
                            margin={{ top: 20, right: 20, bottom: 60, left: 20 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="day"
                                tick={{ fontSize: 12 }}
                                interval={0}
                                angle={-45}
                                textAnchor="end"
                            />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="count" fill="#8b5cf6" isAnimationActive={false}>
                                <LabelList dataKey="count" position="top" fill="#333" fontSize={10} fontWeight={600} />
                            </Bar>
                        </BarChart>
                    </ChartCard>
                </div>

            </div>


            {/* ---------------- ROW 5 – Month Trend (FULL WIDTH) ---------------- */}
            <div style={{ width: "100%", marginTop: "20px" }}>
                <ChartCard title="Incidents per Month" height={350}>
                    <LineChart data={incidentMonth}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" />
                        <YAxis />
                        <Tooltip />
                        <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={3} />
                    </LineChart>
                </ChartCard>
            </div>

            {/* ---------------- ROW 6 – Year Trend (FULL WIDTH) ---------------- */}
            <div style={{ width: "100%", marginTop: "30px" }}>
                <ChartCard title="Incidents per Year" height={350}>
                    <LineChart data={incidentYear}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="year" />
                        <YAxis />
                        <Tooltip />
                        <Line type="monotone" dataKey="count" stroke="#6d28d9" strokeWidth={3} />
                    </LineChart>
                </ChartCard>
            </div>
        </div>
    );
}
