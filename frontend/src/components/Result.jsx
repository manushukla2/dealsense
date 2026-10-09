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
      <RadialBarChart
        width={200} height={200}
        cx={100} cy={100}
        innerRadius={70} outerRadius={90}
        barSize={14}
        data={data}
        startAngle={90} endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          background={{ fill: "#1f2937" }}
          dataKey="value"
          angleAxisId={0}
          fill={color}
          cornerRadius={8}
        />
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
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#9ca3af" }}
          formatter={(v, n, p) => [`${v}%`, p.payload.speaker]}
        />
        {data.map((entry, i) => (
          <Bar key={i} dataKey="score" radius={[4, 4, 0, 0]}>
            {data.map((e, idx) => (
              <Cell key={idx} fill={e.score >= 60 ? "#22c55e" : e.score >= 40 ? "#eab308" : "#ef4444"} />
            ))}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function Result({ data }) {
  const p = data.prediction;
  const pct = Math.round(p.probability * 100);
  const color = pct >= 70 ? "text-green-400" : pct >= 40 ? "text-yellow-400" : "text-red-400";
  const bgColor = pct >= 70 ? "from-green-500/10" : pct >= 40 ? "from-yellow-500/10" : "from-red-500/10";

  return (
    <div className="max-w-4xl mx-auto px-4 pb-20 space-y-6">

      {/* Top summary card */}
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
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{data.transcript?.turns?.length ?? 0}</p>
              <p className="text-xs text-gray-500">Turns</p>
            </div>
            <div className="w-px bg-white/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-green-400">{p.positives?.length ?? 0}</p>
              <p className="text-xs text-gray-500">Positives</p>
            </div>
            <div className="w-px bg-white/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-red-400">{p.risks?.length ?? 0}</p>
              <p className="text-xs text-gray-500">Risks</p>
            </div>
          </div>
        </div>
      </div>

      {/* Signals row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Positives */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-3">
          <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Positive Signals</p>
          {p.positives?.length > 0 ? p.positives.map((item, i) => (
            <div key={i} className="flex items-start gap-3 bg-green-500/5 border border-green-500/10 rounded-xl px-4 py-3">
              <span className="text-green-400 mt-0.5 text-sm">✓</span>
              <span className="text-sm text-gray-300">{item}</span>
            </div>
          )) : <p className="text-gray-600 text-sm">No positive signals detected.</p>}
        </div>

        {/* Risks */}
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

      {/* Sentiment chart */}
      {data.transcript?.turns?.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-4">Sentiment per Turn</p>
          <SentimentBar turns={data.transcript.turns} />
        </div>
      )}

      {/* Transcript */}
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
  );
}
