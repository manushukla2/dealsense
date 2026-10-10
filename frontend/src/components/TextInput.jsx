import { useState } from "react";
import axios from "axios";

const PIPELINE_STAGES = [
  { id: 1, label: "Text Parsing",          icon: "📋", desc: "Reading and splitting transcript lines" },
  { id: 2, label: "Exchange Segmentation", icon: "🔗", desc: "Grouping turns into exchanges" },
  { id: 3, label: "Sentiment Analysis",    icon: "🧠", desc: "RoBERTa scoring each exchange" },
  { id: 4, label: "Deal Scoring",          icon: "📊", desc: "Computing deal probability" },
  { id: 5, label: "Reasoning",             icon: "💡", desc: "Generating plain-English explanation" },
];

const STAGE_DELAYS = [800, 2000, 2500, 1500, 1200];

const PLACEHOLDER = `Paste your transcript here. Supported formats:

Format 1 — labelled speakers:
REP: Hi, thanks for joining the call today.
CLIENT: Sure, I wanted to ask about your pricing.
REP: We offer flexible plans starting at $99/month.
CLIENT: That seems a bit high. We use a cheaper tool right now.

Format 2 — plain alternating lines (auto-labelled):
Hi, thanks for joining the call today.
Sure, I wanted to ask about your pricing.
We offer flexible plans starting at $99/month.
That seems a bit high.`;

export default function TextInput({ setResult, setError }) {
  const [text, setText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [completedStages, setCompletedStages] = useState([]);

  const runPipeline = async () => {
    if (!text.trim()) return;
    setResult(null);
    setError(null);
    setAnalyzing(true);
    setCompletedStages([]);
    setActiveStage(1);

    let current = 1;
    const advance = () => {
      if (current >= PIPELINE_STAGES.length) return;
      const delay = STAGE_DELAYS[current - 1];
      setTimeout(() => {
        setCompletedStages((prev) => [...prev, current]);
        current++;
        setActiveStage(current);
        advance();
      }, delay);
    };
    advance();

    try {
      const res = await axios.post("http://localhost:8000/predict-text", { text });
      setCompletedStages(PIPELINE_STAGES.map((s) => s.id));
      setActiveStage(0);
      setTimeout(() => setResult(res.data), 600);
    } catch (e) {
      setError(e.response?.data?.detail || "Analysis failed. Is the backend running?");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">

      {/* Text input card */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-4">
        <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Paste Transcript</p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={PLACEHOLDER}
          rows={12}
          className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-sm text-gray-300 placeholder-gray-700 resize-none focus:outline-none focus:border-blue-500/50 transition font-mono leading-relaxed"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">
            {text.trim().split("\n").filter(l => l.trim()).length} lines · {text.length} chars
          </span>
          <div className="flex gap-3">
            <button
              onClick={() => setText("")}
              disabled={!text || analyzing}
              className="text-gray-600 hover:text-gray-400 text-sm transition disabled:opacity-30"
            >
              Clear
            </button>
            <button
              onClick={runPipeline}
              disabled={!text.trim() || analyzing}
              className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition"
            >
              {analyzing ? "Analysing..." : "⚡ Analyse Deal"}
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline stages */}
      {analyzing && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-3">
          <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-4">Pipeline Progress</p>
          {PIPELINE_STAGES.map((stage) => {
            const done = completedStages.includes(stage.id);
            const active = activeStage === stage.id;
            return (
              <div key={stage.id} className={`flex items-center gap-4 px-4 py-3 rounded-xl border transition-all duration-500
                ${done ? "border-green-500/20 bg-green-500/5" : active ? "border-blue-500/30 bg-blue-500/10" : "border-white/5 bg-white/[0.02]"}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border transition-all
                  ${done ? "border-green-500 bg-green-500/20 text-green-400" : active ? "border-blue-500 bg-blue-500/20 animate-pulse" : "border-white/10"}`}>
                  {done ? "✓" : stage.icon}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${done ? "text-green-300" : active ? "text-blue-300" : "text-gray-500"}`}>
                    {stage.label}
                  </p>
                  <p className="text-xs text-gray-600">{stage.desc}</p>
                </div>
                {active && <div className="w-4 h-4 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
