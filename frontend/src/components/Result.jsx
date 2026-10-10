import { useRef } from "react";
import html2canvas from "html2canvas";
import {
  RadialBarChart, RadialBar, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";

function ProbabilityGauge({ probability }) {
  const pct = Math.round(probability * 100);
  const color = pct >= 70 ? "#22c55e" : pct >= 40 ? "#eab308" : "#ef4444";
  const data = [{ value: pct }];
  return (
    <div className="flex flex-col items-center justify-center">
      <RadialBarChart width={200} height={200} cx={100} cy={100} innerRadius={70} outerRadius={90} barSize={14} data={data} startAngle={90} endAngle={-270}>
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar background={{ fill: "#1f2937" }} dataKey="value" angleAxisId={0} fill={color} cornerRadius={8} />
      </RadialBarChart>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-extrabold" style={{ color }}>{pct}%</span>
        <span className="text-xs text-gray-500 mt-1">probability</span>
      </div>
    </div>
  );
}

function SentimentBar({ turns }) {
  if (!turns?.length) return null;
  const data = turns.map((t, i) => ({
    name: `T${i + 1}`,
    speaker: t.speaker,
    score: t.sentiment_score !== undefined ? Math.round(t.sentiment_score * 100) : 50,
  }));
  return (
    <ResponsiveContainer width="100%" height={140}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }} labelStyle={{ color: "#9ca3af" }} formatter={(v, n, p) => [`${v}%`, p.payload.speaker]} />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((e, idx) => (
            <Cell key={idx} fill={e.score >= 60 ? "#22c55e" : e.score >= 40 ? "#eab308" : "#ef4444"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function Result({ data }) {
  const cardRef = useRef(null);
  const p = data.prediction;
  const pct = Math.round(p.probability * 100);
  const color = pct >= 70 ? "text-green-400" : pct >= 40 ? "text-yellow-400" : "text-red-400";
  const bgColor = pct >= 70 ? "from-green-500/10" : pct >= 40 ? "from-yellow-500/10" : "from-red-500/10";
  const hexColor = pct >= 70 ? "#22c55e" : pct >= 40 ? "#eab308" : "#ef4444";

  const downloadCard = () => {
    const turns = data.transcript?.turns || [];
    const positives = p.positives || [];
    const risks = p.risks || [];

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0a0f; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 40px; }
  .card { max-width: 800px; margin: 0 auto; }
  .header { display: flex; align-items: center; gap: 10px; margin-bottom: 32px; }
  .logo { width: 32px; height: 32px; background: linear-gradient(135deg, #3b82f6, #7c3aed); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; }
  .brand { font-size: 18px; font-weight: 600; }
  .date { margin-left: auto; color: #4b5563; font-size: 12px; }
  .summary { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 32px; display: flex; gap: 32px; align-items: center; margin-bottom: 24px; }
  .gauge { text-align: center; min-width: 120px; }
  .gauge .pct { font-size: 56px; font-weight: 900; color: ${hexColor}; line-height: 1; }
  .gauge .label { font-size: 12px; color: #6b7280; margin-top: 4px; }
  .verdict { font-size: 28px; font-weight: 800; color: ${hexColor}; margin-bottom: 8px; }
  .badge { display: inline-block; border: 1px solid ${hexColor}40; background: ${hexColor}15; color: ${hexColor}; border-radius: 999px; padding: 3px 12px; font-size: 11px; margin-bottom: 12px; }
  .summary-text { color: #9ca3af; font-size: 14px; line-height: 1.6; margin-bottom: 16px; }
  .stats { display: flex; gap: 24px; }
  .stat { text-align: center; }
  .stat .val { font-size: 24px; font-weight: 700; }
  .stat .lbl { font-size: 11px; color: #6b7280; }
  .divider { width: 1px; background: #1f2937; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .section { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 20px; }
  .section-title { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 12px; }
  .signal { display: flex; gap: 10px; align-items: flex-start; padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }
  .pos { background: #052e1640; border: 1px solid #16a34a30; color: #86efac; }
  .neg { background: #450a0a40; border: 1px solid #dc262630; color: #fca5a5; }
  .transcript { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 20px; }
  .turn { margin-bottom: 12px; }
  .turn-speaker { font-size: 11px; color: #6b7280; font-weight: 600; margin-bottom: 3px; }
  .turn-text { font-size: 13px; color: #d1d5db; line-height: 1.5; }
  .footer { text-align: center; color: #374151; font-size: 11px; margin-top: 32px; }
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="logo">DS</div>
    <span class="brand">DealSense</span>
    <span class="date">${new Date().toLocaleDateString()}</span>
  </div>

  <div class="summary">
    <div class="gauge">
      <div class="pct">${pct}%</div>
      <div class="label">probability</div>
    </div>
    <div style="flex:1">
      <div class="verdict">${p.verdict}</div>
      <div class="badge">${pct >= 70 ? "High confidence" : pct >= 40 ? "Moderate" : "Low confidence"}</div>
      <div class="summary-text">${p.summary}</div>
      <div class="stats">
        <div class="stat"><div class="val">${turns.length}</div><div class="lbl">Turns</div></div>
        <div class="divider"></div>
        <div class="stat"><div class="val" style="color:#22c55e">${positives.length}</div><div class="lbl">Positives</div></div>
        <div class="divider"></div>
        <div class="stat"><div class="val" style="color:#ef4444">${risks.length}</div><div class="lbl">Risks</div></div>
      </div>
    </div>
  </div>

  <div class="grid">
    <div class="section">
      <div class="section-title">Positive Signals</div>
      ${positives.map(i => `<div class="signal pos"><span>✓</span><span>${i}</span></div>`).join("") || "<div style='color:#4b5563;font-size:13px'>None detected</div>"}
    </div>
    <div class="section">
      <div class="section-title">Risk Signals</div>
      ${risks.map(i => `<div class="signal neg"><span>✗</span><span>${i}</span></div>`).join("") || "<div style='color:#4b5563;font-size:13px'>None detected</div>"}
    </div>
  </div>

  ${turns.length > 0 ? `
  <div class="transcript">
    <div class="section-title">Transcript</div>
    ${turns.map(t => `<div class="turn"><div class="turn-speaker">${t.speaker}</div><div class="turn-text">${t.text}</div></div>`).join("")}
  </div>` : ""}

  <div class="footer">Generated by DealSense · ${new Date().toLocaleString()}</div>
</div>
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dealsense-${Date.now()}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 pb-20 space-y-6">

      {/* Download button */}
      <div className="flex justify-end">
        <button
          onClick={downloadCard}
          className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white px-5 py-2.5 rounded-xl text-sm font-medium transition"
        >
          ⬇ Download Result Card
        </button>
      </div>

      {/* Card */}
      <div ref={cardRef} className="space-y-6 bg-[#0a0a0f] p-2 rounded-2xl">
        <div className="flex items-center gap-2 px-2 pt-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-xs font-bold">DS</div>
          <span className="text-sm font-semibold text-gray-300">DealSense</span>
          <span className="ml-auto text-xs text-gray-600">{new Date().toLocaleDateString()}</span>
        </div>

        <div className={`rounded-2xl border border-white/10 bg-gradient-to-br ${bgColor} to-transparent p-8 flex flex-col md:flex-row items-center gap-8`}>
          <div className="relative flex items-center justify-center w-[200px] h-[200px] shrink-0">
            <ProbabilityGauge probability={p.probability} />
          </div>
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <span className={`text-3xl font-extrabold ${color}`}>{p.verdict}</span>
              <span className={`text-xs px-3 py-1 rounded-full border ${pct >= 70 ? "border-green-500/30 bg-green-500/10 text-green-400" : pct >= 40 ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400" : "border-red-500/30 bg-red-500/10 text-red-400"}`}>
                {pct >= 70 ? "High confidence" : pct >= 40 ? "Moderate" : "Low confidence"}
              </span>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">{p.summary}</p>
            <div className="flex gap-4 pt-2">
              <div className="text-center"><p className="text-2xl font-bold text-white">{data.transcript?.turns?.length ?? 0}</p><p className="text-xs text-gray-500">Turns</p></div>
              <div className="w-px bg-white/10" />
              <div className="text-center"><p className="text-2xl font-bold text-green-400">{p.positives?.length ?? 0}</p><p className="text-xs text-gray-500">Positives</p></div>
              <div className="w-px bg-white/10" />
              <div className="text-center"><p className="text-2xl font-bold text-red-400">{p.risks?.length ?? 0}</p><p className="text-xs text-gray-500">Risks</p></div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Positive Signals</p>
            {p.positives?.length > 0 ? p.positives.map((item, i) => (
              <div key={i} className="flex items-start gap-3 bg-green-500/5 border border-green-500/10 rounded-xl px-4 py-3">
                <span className="text-green-400 mt-0.5 text-sm">✓</span>
                <span className="text-sm text-gray-300">{item}</span>
              </div>
            )) : <p className="text-gray-600 text-sm">No positive signals detected.</p>}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Risk Signals</p>
            {p.risks?.length > 0 ? p.risks.map((item, i) => (
              <div key={i} className="flex items-start gap-3 bg-red-500/5 border border-red-500/10 rounded-xl px-4 py-3">
                <span className="text-red-400 mt-0.5 text-sm">✗</span>
                <span className="text-sm text-gray-300">{item}</span>
              </div>
            )) : <p className="text-gray-600 text-sm">No risk signals detected.</p>}
          </div>
        </div>

        {data.transcript?.turns?.length > 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-4">Sentiment per Turn</p>
            <SentimentBar turns={data.transcript.turns} />
          </div>
        )}

        {data.transcript?.turns?.length > 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-4">Full Transcript</p>
            <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
              {data.transcript.turns.map((turn, i) => (
                <div key={i} className={`flex gap-3 ${turn.speaker?.includes("00") ? "flex-row" : "flex-row-reverse"}`}>
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-xs font-bold shrink-0">
                    {turn.speaker?.slice(-2) ?? i}
                  </div>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${turn.speaker?.includes("00") ? "bg-white/5 text-gray-300 rounded-tl-none" : "bg-blue-600/20 text-blue-100 rounded-tr-none"}`}>
                    <p className="text-xs text-gray-500 mb-1 font-medium">{turn.speaker}</p>
                    {turn.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
