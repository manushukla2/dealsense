import { useState } from "react";
import Uploader from "./components/Uploader";
import VoiceRecorder from "./components/VoiceRecorder";
import Result from "./components/Result";

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("upload");

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Navbar */}
      <nav className="border-b border-white/10 px-8 py-4 flex items-center justify-between backdrop-blur-sm sticky top-0 z-50 bg-[#0a0a0f]/80">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-xs font-bold">DS</div>
          <span className="font-semibold text-lg tracking-tight">DealSense</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-gray-400">
          <span className="hover:text-white cursor-pointer transition">Dashboard</span>
          <span className="hover:text-white cursor-pointer transition">History</span>
          <span className="hover:text-white cursor-pointer transition">Settings</span>
          <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm transition">Get Started</button>
        </div>
      </nav>

      {/* Hero */}
      <div className="text-center py-16 px-4">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-blue-400 text-xs mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
          AI-Powered Meeting Intelligence
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight mb-4 bg-gradient-to-r from-white via-blue-100 to-violet-300 bg-clip-text text-transparent">
          Predict Deal Outcomes<br />from Any Meeting
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto text-base mb-10">
          Upload a recording or record live. DealSense transcribes it, analyses every exchange, and gives you a probability score with full reasoning.
        </p>

        {/* Tabs */}
        <div className="inline-flex bg-white/5 border border-white/10 rounded-xl p-1 mb-8">
          <button
            onClick={() => { setTab("upload"); setResult(null); setError(null); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${tab === "upload" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
          >
            📁 Upload File
          </button>
          <button
            onClick={() => { setTab("record"); setResult(null); setError(null); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${tab === "record" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
          >
            🎙 Record Live
          </button>
        </div>

        {/* Tab content */}
        {tab === "upload" && (
          <>
            <Uploader setResult={setResult} setLoading={setLoading} setError={setError} />
            {loading && (
              <div className="mt-10 flex flex-col items-center gap-3">
                <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                <p className="text-blue-400 text-sm animate-pulse">Analysing meeting audio...</p>
              </div>
            )}
          </>
        )}

        {tab === "record" && (
          <VoiceRecorder setResult={setResult} setError={setError} />
        )}

        {error && (
          <div className="mt-8 inline-flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl px-5 py-3 text-red-400 text-sm">
            ⚠ {error}
          </div>
        )}
      </div>

      {result && <Result data={result} />}

      {/* Footer */}
      <footer className="border-t border-white/10 mt-20 py-8 text-center text-gray-600 text-xs">
        © 2026 DealSense · Built with Whisper, pyannote, RoBERTa & React
      </footer>
    </div>
  );
}
