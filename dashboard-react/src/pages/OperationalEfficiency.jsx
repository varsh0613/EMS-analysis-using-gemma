import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar
} from "recharts";

import {
  fetchOpKpis,
  fetchOpTimeTrends,
  fetchOpDistributions,
  fetchOpDelayBuckets,
  fetchOpHourlyResponse,
  fetchOpPeakDelayHours,
} from "../api/gemmaApi";

// ---------- KPI CARD ----------
function KPICard({ label, value }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value ?? "--"}</div>
    </div>
  );
}

// ---------- AGGREGATE TRENDS PER YEAR ----------
function aggregateYearly(data) {
  const yearly = {};
  data.forEach(({ date, avg_response, avg_on_scene, avg_cycle }) => {
    const year = date.slice(0, 4);
    if (!yearly[year]) yearly[year] = { count: 0, response: 0, on_scene: 0, cycle: 0 };
    yearly[year].count += 1;
    yearly[year].response += avg_response;
    yearly[year].on_scene += avg_on_scene;
    yearly[year].cycle += avg_cycle;
  });

  return Object.entries(yearly).map(([year, vals]) => ({
    year,
    avg_response_time: +(vals.response / vals.count).toFixed(2),
    avg_on_scene_time: +(vals.on_scene / vals.count).toFixed(2),
    avg_cycle_time: +(vals.cycle / vals.count).toFixed(2),
  }));
}

// ---------- SMOOTH DISTRIBUTION FUNCTION ----------
function smoothDistribution(data) {
  const result = [];
  const window = 2;
  for (let i = 0; i < data.length; i++) {
    let sum = 0, count = 0;
    for (let j = i - window; j <= i + window; j++) {
      if (data[j]) {
        sum += data[j].count;
        count += 1;
      }
    }
    result.push({ bin: data[i].bin, count: +(sum / count).toFixed(2) });
  }
  return result;
}

// ---------- MAIN COMPONENT ----------
export default function OperationalEfficiency() {
  const [kpis, setKpis] = useState({});
  const [trends, setTrends] = useState([]);
  const [dists, setDists] = useState({});
  const [delayBuckets, setDelayBuckets] = useState([]);
  const [hourly, setHourly] = useState([]);
  const [peakDelayHours, setPeakDelayHours] = useState({});

  useEffect(() => {
    fetchOpKpis().then(setKpis);
    fetchOpTimeTrends().then(data => setTrends(aggregateYearly(data)));
    fetchOpDistributions().then(data => {
      const smoothed = {};
      ["response_hist", "on_scene_hist", "cycle_hist"].forEach(key => {
        if (data[key]) smoothed[key] = smoothDistribution(data[key]);
      });
      setDists(smoothed);
    });
    fetchOpDelayBuckets().then(setDelayBuckets);
    fetchOpHourlyResponse().then(setHourly);
    fetchOpPeakDelayHours().then(setPeakDelayHours);
  }, []);

  return (
    <div className="dashboard-container">
      <style>{`
        .dashboard-container { padding: 24px; display: flex; flex-direction: column; gap: 40px; font-family: Arial, sans-serif; }
        .kpi-container { display: flex; flex-wrap: wrap; gap: 16px; }
        .kpi-card { background-color: #fff; padding: 20px; border-radius: 12px; border: 1px solid #c8a2c8; width: 200px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; transition: box-shadow 0.2s ease; }
        .kpi-card:hover { box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .kpi-label { font-size: 14px; color: #666; margin-bottom: 8px; }
        .kpi-value { font-size: 24px; font-weight: bold; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .chart-card { background-color: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .chart-card h2 { margin-bottom: 16px; font-size: 18px; color: #333; }
        .distribution-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
      `}</style>
<h1 style={{ color: "#7b5ea3", fontSize: "32px", fontWeight: 700 }}>Operational Efficiency</h1>
<div className="kpi-container" style={{ display: "flex", flexWrap: "wrap", gap: "21px" }}>
  {[
    { label: "Avg Response Time", value: kpis.avg_response_time },
    { label: "90th Percentile (response)", value: kpis.p90_response_time },
    { label: "Avg On-Scene Time", value: kpis.avg_on_scene_time },
    { label: "Avg Cycle Time", value: kpis.avg_total_cycle_time },
    { label: "Avg Turnout Time", value: kpis.avg_turnout_time },
    { label: "Calls / Day", value: kpis.calls_per_day },
    { label: "Busiest City", value: kpis.busiest_city || "--" },
    { label: "Busiest Hour", value: kpis.busiest_hour || "--" },
    { label: "SLA ≤8 min %", value: kpis.sla_8_min_pct },
  ].map(({ label, value }) => (
    <div
      key={label}
      style={{
        flex: "1 1 calc(20% - 16px)", // 5 per row max with gap adjustment
        minWidth: "150px",            // prevent shrinking too small
      }}
    >
      <KPICard label={label} value={value} />
    </div>
  ))}
</div>

{/* DISTRIBUTIONS ROW */}
<div className="distribution-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
  {["response_hist", "on_scene_hist", "cycle_hist"].map(key => (
    <div key={key} className="chart-card">
      <h2>
        {key === "response_hist" && "Response Time Distribution"}
        {key === "on_scene_hist" && "On-Scene Time Distribution"}
        {key === "cycle_hist" && "Cycle Time Distribution"}
      </h2>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={dists[key] || []}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="bin" tick={{ fontSize: 12 }} angle={-45} height={60} />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="count" stroke="#c8a2c8" strokeWidth={2} dot={false} fill="#e0c3e0" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  ))}
</div>


      {/* TRENDS PER YEAR */}
      <div className="chart-card">
        <h2>Operational Trends Per Year</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="avg_response_time" stroke="#a463a8" name="Response" />
            <Line type="monotone" dataKey="avg_on_scene_time" stroke="#c8a2c8" name="On Scene" />
            <Line type="monotone" dataKey="avg_cycle_time" stroke="#7d4b7d" name="Cycle" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* HOURLY RESPONSE TIME */}
      <div className="chart-card">
        <h2>Response Time by Hour</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={hourly}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" orientation="left" label={{ value: 'Avg Response (min)', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" label={{ value: 'Call Count', angle: -90, position: 'insideRight' }} />
            <Tooltip />
            <Line yAxisId="left" type="monotone" dataKey="avg_response" stroke="#a463a8" strokeWidth={2} dot />
            <Line yAxisId="right" type="monotone" dataKey="count" stroke="#c8a2c8" strokeWidth={2} dot />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* DELAY BUCKETS */}
<div className="chart-card">
  <h2>Delay Buckets (Response)</h2>
  <ResponsiveContainer width="100%" height={260}>
    <BarChart data={delayBuckets}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="delay_bucket" />
      <YAxis />
      <Tooltip />
      <Bar
        dataKey="count"
        fill="#a463a8"
        radius={[6, 6, 0, 0]}
      />
    </BarChart>
  </ResponsiveContainer>
</div>

      {/* PEAK DELAY HOURS SUMMARY */}
      <div className="chart-card">
        <h2>Peak Delay Hours (SLA &gt; 8 min)</h2>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
            <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Worst Hour (Most Delays)</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#a463a8' }}>
                {peakDelayHours.worst_hour || '--'}
              </div>
            </div>
            <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Best Hour (Fewest Delays)</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#7d4b7d' }}>
                {peakDelayHours.best_hour || '--'}
              </div>
            </div>
            <div style={{ padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #ddd' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Total Delayed Incidents</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#666' }}>
                {peakDelayHours.total_delayed_incidents?.toLocaleString() || '--'}
              </div>
            </div>
          </div>

          {peakDelayHours.peak_hours && peakDelayHours.peak_hours.length > 0 && (
            <div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#333' }}>Delayed Incidents by Hour</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '8px' }}>
                {peakDelayHours.peak_hours.map((hour, idx) => (
                  <div key={idx} style={{ padding: '10px', backgroundColor: '#ffe6f2', borderRadius: '6px', border: '1px solid #c8a2c8' }}>
                    <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#a463a8' }}>{hour.hour}</div>
                    <div style={{ fontSize: '12px', color: '#333', marginTop: '4px' }}>
                      {hour.delayed_incident_count.toLocaleString()} incidents
                    </div>
                    <div style={{ fontSize: '11px', color: '#999' }}>{hour.pct_of_total_delays}% of delays</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
