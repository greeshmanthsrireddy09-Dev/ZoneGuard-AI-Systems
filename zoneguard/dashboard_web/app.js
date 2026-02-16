import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import { motion } from "https://esm.sh/framer-motion@11.11.17";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: "easeOut" } },
};

function riskState(latestPred, anomalyCount) {
  if ((latestPred !== null && latestPred < 0.55) || anomalyCount >= 5) {
    return { label: "High Risk", cls: "bg-rose-100 text-rose-800 border-rose-200" };
  }
  if ((latestPred !== null && latestPred < 0.72) || anomalyCount >= 2) {
    return { label: "Watch", cls: "bg-amber-100 text-amber-800 border-amber-200" };
  }
  return { label: "Stable", cls: "bg-emerald-100 text-emerald-800 border-emerald-200" };
}

async function callApi(path, { method = "GET", params = null, body = null } = {}) {
  const url = new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

function ActionCard({ action }) {
  const priority = String(action.priority || "medium").toLowerCase();
  const badgeCls = priority === "high"
    ? "bg-rose-100 text-rose-700 border-rose-200"
    : priority === "low"
    ? "bg-emerald-100 text-emerald-700 border-emerald-200"
    : "bg-amber-100 text-amber-700 border-amber-200";

  return html`
    <${motion.div}
      layout
      initial=${{ opacity: 0, scale: 0.97 }}
      animate=${{ opacity: 1, scale: 1 }}
      transition=${{ duration: 0.25 }}
      className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"
    >
      <div className="flex items-center justify-between gap-3">
        <h4 className="font-semibold text-sm">${action.action}</h4>
        <span className=${`text-[11px] uppercase tracking-wide border rounded-full px-2 py-0.5 ${badgeCls}`}>${priority}</span>
      </div>
      <p className="text-sm text-slate-300 mt-1.5">${action.detail}</p>
    <//>
  `;
}

function App() {
  const [zone, setZone] = useState("zone_01");
  const [horizon, setHorizon] = useState(6);
  const [lookback, setLookback] = useState(120);
  const [status, setStatus] = useState("Ready");

  const [forecast, setForecast] = useState(null);
  const [anomaly, setAnomaly] = useState(null);
  const [reason, setReason] = useState(null);
  const [action, setAction] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [topEvent, setTopEvent] = useState(null);
  const [replay, setReplay] = useState(null);

  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  const preds = forecast?.predictions || [];
  const anomalies = anomaly?.events || [];
  const actions = action?.recommended_actions || [];
  const latestPred = preds.length ? Number(preds[preds.length - 1].predicted_availability) : null;
  const risk = useMemo(() => riskState(latestPred, anomalies.length), [latestPred, anomalies.length]);

  useEffect(() => {
    if (!chartRef.current || !window.Chart) return;
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
      chartInstanceRef.current = null;
    }
    if (!preds.length) return;

    const labels = preds.map((p) => new Date(p.timestamp).toLocaleTimeString());
    const values = preds.map((p) => p.predicted_availability);

    chartInstanceRef.current = new window.Chart(chartRef.current.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Predicted Availability",
          data: values,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37,99,235,.12)",
          borderWidth: 2,
          tension: 0.35,
          fill: true,
          pointRadius: 2,
        }],
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 1 } },
      },
    });
  }, [preds]);

  async function runPipeline() {
    try {
      setStatus("Running full pipeline...");
      const payload = await callApi("/pipeline/zone", { method: "POST", body: { zone, horizon: Number(horizon), lookback: Number(lookback) } });
      setPipeline(payload);
      setForecast(payload.forecast || null);
      setAnomaly(payload.anomalies || null);
      setReason(payload.reasoning || null);
      setAction(payload.actions || null);
      setTopEvent((payload.anomalies?.events || [])[0] || null);
      setStatus("Pipeline completed.");
      document.getElementById("overview")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  async function runForecastOnly() {
    try {
      setStatus("Running forecast...");
      const payload = await callApi("/predict", { params: { zone, horizon: Number(horizon) } });
      setForecast(payload);
      setStatus("Forecast completed.");
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  async function runFlow() {
    try {
      setStatus("Running anomaly -> reason -> action...");
      const anomalyPayload = await callApi("/anomaly", { method: "POST", body: { zone, lookback: Number(lookback) } });
      setAnomaly(anomalyPayload);
      const event = (anomalyPayload.events || [])[0] || null;
      setTopEvent(event);
      if (event) {
        const reasonPayload = await callApi("/reason", { method: "POST", body: { event } });
        setReason(reasonPayload);
        const actionPayload = await callApi("/action", { method: "POST", body: { event, explanation: reasonPayload.explanation } });
        setAction(actionPayload);
      }
      setStatus("Flow completed.");
      document.getElementById("investigation")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  async function submitFeedback() {
    if (!topEvent) return;
    try {
      setStatus("Submitting feedback...");
      await callApi("/feedback", {
        method: "POST",
        body: {
          event_id: topEvent.event_id,
          rating: 5,
          correction: "Recommended action reduced availability risk.",
          metadata: { source: "framer-ui" },
        },
      });
      setStatus("Feedback stored.");
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  async function runReplay() {
    try {
      setStatus("Running replay evaluation...");
      const payload = await callApi("/evaluate/replay", { method: "POST", body: { zone, horizon: Number(horizon), lookback: Number(lookback) } });
      setReplay(payload);
      setStatus("Replay evaluation completed.");
      document.getElementById("impact")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  let reasonObj = {};
  try {
    reasonObj = reason?.explanation ? JSON.parse(reason.explanation) : {};
  } catch {
    reasonObj = { explanation: reason?.explanation || "" };
  }

  return html`
    <div className="max-w-7xl mx-auto px-4 py-6 lg:px-8">
      <${motion.header} variants=${fadeUp} initial="hidden" animate="show" className="glass border border-slate-700 rounded-3xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Zone Reliability AI</p>
            <h1 className="text-3xl md:text-4xl font-bold mt-1">ZoneGuard Motion Console</h1>
            <p className="text-slate-300 mt-2">Production-style multi-agent monitoring with animated operational workflow.</p>
          </div>
          <div className=${`border rounded-full px-4 py-2 text-sm font-semibold ${risk.cls}`}>${risk.label}</div>
        </div>
      <//>

      <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.25 }} className="mt-5 grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="glass border border-slate-700 rounded-2xl p-4"><p className="text-xs uppercase text-slate-400">Zone</p><p className="text-xl font-bold">${zone}</p></div>
        <div className="glass border border-slate-700 rounded-2xl p-4"><p className="text-xs uppercase text-slate-400">Forecast Points</p><p className="text-xl font-bold">${preds.length}</p></div>
        <div className="glass border border-slate-700 rounded-2xl p-4"><p className="text-xs uppercase text-slate-400">Anomalies</p><p className="text-xl font-bold">${anomalies.length}</p></div>
        <div className="glass border border-slate-700 rounded-2xl p-4"><p className="text-xs uppercase text-slate-400">Latest Availability</p><p className="text-xl font-bold">${latestPred === null ? "-" : latestPred.toFixed(3)}</p></div>
      <//>

      <section className="mt-5 grid grid-cols-1 lg:grid-cols-5 gap-4">
        <${motion.aside} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4 lg:col-span-1 h-fit">
          <h2 className="font-semibold text-lg">Controls</h2>
          <div className="space-y-3 mt-3">
            <div>
              <label className="text-xs uppercase text-slate-400">Zone ID</label>
              <input value=${zone} onChange=${(e) => setZone(e.target.value)} className="w-full mt-1 rounded-xl border border-slate-600 bg-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase text-slate-400">Horizon</label>
              <input type="number" min="1" max="24" value=${horizon} onChange=${(e) => setHorizon(e.target.value)} className="w-full mt-1 rounded-xl border border-slate-600 bg-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase text-slate-400">Lookback</label>
              <input type="number" min="24" max="240" value=${lookback} onChange=${(e) => setLookback(e.target.value)} className="w-full mt-1 rounded-xl border border-slate-600 bg-slate-900 px-3 py-2 text-sm" />
            </div>

            <${motion.button} whileHover=${{ scale: 1.02 }} whileTap=${{ scale: 0.98 }} onClick=${runPipeline} className="w-full rounded-xl bg-blue-600 text-white font-semibold py-2.5 shadow hover:bg-blue-700">Run Full Pipeline<//>
            <${motion.button} whileHover=${{ scale: 1.02 }} whileTap=${{ scale: 0.98 }} onClick=${runForecastOnly} className="w-full rounded-xl bg-slate-800 border border-slate-600 font-semibold py-2.5 hover:bg-slate-700">Forecast Only<//>
            <${motion.button} whileHover=${{ scale: 1.02 }} whileTap=${{ scale: 0.98 }} onClick=${runFlow} className="w-full rounded-xl bg-slate-800 border border-slate-600 font-semibold py-2.5 hover:bg-slate-700">Detect + Explain + Action<//>
            <${motion.button} whileHover=${{ scale: topEvent ? 1.02 : 1 }} whileTap=${{ scale: topEvent ? 0.98 : 1 }} onClick=${submitFeedback} disabled=${!topEvent} className="w-full rounded-xl bg-emerald-600 disabled:bg-emerald-300 text-white font-semibold py-2.5">Submit Positive Feedback<//>
            <${motion.button} whileHover=${{ scale: 1.02 }} whileTap=${{ scale: 0.98 }} onClick=${runReplay} className="w-full rounded-xl bg-indigo-600 text-white font-semibold py-2.5 hover:bg-indigo-700">Run Replay Evaluation<//>
          </div>
          <p className="text-xs text-slate-400 mt-4">${status}</p>
        <//>

        <div id="overview" className="lg:col-span-4 grid grid-cols-1 xl:grid-cols-3 gap-4">
          <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">Forecast Curve</h3>
              <span className="text-xs text-slate-400">Latest: ${latestPred === null ? "-" : latestPred.toFixed(3)}</span>
            </div>
            <div className="h-64 mt-3"><canvas ref=${chartRef}></canvas></div>
          <//>

          <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4 overflow-auto">
            <h3 className="font-semibold">Anomaly Radar</h3>
            <table className="w-full text-sm mt-3">
              <thead className="text-left text-xs uppercase text-slate-400"><tr><th className="pb-2">Timestamp</th><th className="pb-2">Score</th></tr></thead>
              <tbody>
                ${!anomalies.length ? html`<tr><td className="py-2 text-slate-400" colSpan="2">No anomalies</td></tr>` : anomalies.slice(0, 12).map((row) => html`<tr key=${row.event_id}><td className="py-1 pr-2 text-slate-300">${new Date(row.timestamp).toLocaleString()}</td><td className="py-1 font-semibold">${Number(row.score).toFixed(3)}</td></tr>`) }
              </tbody>
            </table>
          <//>

          <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4">
            <h3 className="font-semibold">Action Board</h3>
            <div className="mt-3 space-y-2">
              ${!actions.length ? html`<p className="text-sm text-slate-400">No actions generated yet.</p>` : actions.map((item, idx) => html`<${ActionCard} key=${`${item.action}-${idx}`} action=${item} />`)}
            </div>
          <//>
        </div>
      </section>

      <section id="investigation" className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
        <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4">
          <h3 className="font-semibold">Reasoning</h3>
          <pre className="mt-3 bg-slate-950 text-slate-100 rounded-xl p-3 text-xs overflow-auto max-h-80">${JSON.stringify(reasonObj, null, 2)}</pre>
        <//>
        <${motion.section} variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="glass border border-slate-700 rounded-2xl p-4">
          <h3 className="font-semibold">Trace and Payloads</h3>
          <pre className="mt-3 bg-slate-950 text-slate-100 rounded-xl p-3 text-xs overflow-auto max-h-80">${JSON.stringify({ pipeline, forecast, anomaly }, null, 2)}</pre>
        <//>
      </section>

      <${motion.section} id="impact" variants=${fadeUp} initial="hidden" whileInView="show" viewport=${{ once: true, amount: 0.2 }} className="mt-4 glass border border-slate-700 rounded-2xl p-4">
        <h3 className="font-semibold">Business Impact Replay</h3>
        ${!replay ? html`<p className="text-sm text-slate-300 mt-2">Run replay evaluation to generate recruiter-facing impact metrics.</p>` : html`
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">Forecast MAPE</p><p className="text-xl font-bold">${replay.forecast_mape}</p></div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">Forecast RMSE</p><p className="text-xl font-bold">${replay.forecast_rmse}</p></div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">Anomaly Events</p><p className="text-xl font-bold">${replay.anomaly_events}</p></div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">Incident Prevention Rate</p><p className="text-xl font-bold">${replay.business_impact?.incident_prevention_rate}</p></div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">MTTR Reduction (min)</p><p className="text-xl font-bold">${replay.business_impact?.estimated_mttr_reduction_minutes}</p></div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"><p className="text-xs uppercase text-slate-400">Ops Hours Saved</p><p className="text-xl font-bold">${replay.business_impact?.estimated_ops_hours_saved}</p></div>
          </div>
        `}
      <//>
    </div>
  `;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
