import { useState, useRef } from "react";
import axios from "axios";
import API_URL from "../api.js";

const PIPELINE_STAGES = [
  { id: 1, label: "Audio Ingestion",       icon: "🎙", desc: "Receiving and preparing audio" },
  { id: 2, label: "Transcription",         icon: "📝", desc: "Whisper converting speech to text" },
  { id: 3, label: "Speaker Diarization",   icon: "👥", desc: "pyannote labelling who spoke" },
  { id: 4, label: "Exchange Segmentation", icon: "🔗", desc: "Grouping turns into exchanges" },
  { id: 5, label: "Sentiment Analysis",    icon: "🧠", desc: "RoBERTa scoring each exchange" },
  { id: 6, label: "Deal Scoring",          icon: "📊", desc: "Computing deal probability" },
  { id: 7, label: "Reasoning",             icon: "💡", desc: "Generating plain-English explanation" },
];

const STAGE_DELAYS = [800, 3000, 2500, 1500, 2000, 1500, 1200];

export default function VoiceRecorder({ setResult, setError }) {
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [transcribing, setTranscribing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [completedStages, setCompletedStages] = useState([]);
  const [seconds, setSeconds] = useState(0);

  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const transcribeBlob = async (blob) => {
    setTranscribing(true);
    setTranscript("");
    try {
      const fd = new FormData();
      fd.append("file", blob, "recording.webm");
      const res = await axios.post(`${API_URL}/transcribe`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTranscript(res.data.text);
    } catch (e) {
      setTranscript("Transcription failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setTranscribing(false);
    }
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream);
    mediaRef.current = mr;
    chunksRef.current = [];
    mr.ondataavailable = (e) => chunksRef.current.push(e.data);
    mr.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setAudioBlob(blob);
      setAudioUrl(URL.createObjectURL(blob));
      transcribeBlob(blob);
    };
    mr.start();
    setRecording(true);
    setSeconds(0);
    setTranscript("");
    setAudioBlob(null);
    setAudioUrl(null);
    setCompletedStages([]);
    setActiveStage(0);
    setResult(null);
    setError(null);
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
  };

  const stopRecording = () => {
    mediaRef.current?.stop();
    mediaRef.current?.stream.getTracks().forEach((t) => t.stop());
    setRecording(false);
    clearInterval(timerRef.current);
  };

  const runPipeline = async () => {
    if (!audioBlob) return;
    setResult(null);
    setError(null);
    setAnalyzing(true);
    setCompletedStages([]);
    setActiveStage(1);

    let current = 1;
    const advance = () => {
      if (current >= PIPELINE_STAGES.length) return;
      setTimeout(() => {
        setCompletedStages((prev) => [...prev, current]);
        current++;
        setActiveStage(current);
        advance();
      }, STAGE_DELAYS[current - 1]);
    };
    advance();

    try {
      const fd = new FormData();
      fd.append("file", audioBlob, "recording.webm");
      const res = await axios.post(`${API_URL}/predict`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setCompletedStages(PIPELINE_STAGES.map((s) => s.id));
      setActiveStage(0);
      setTimeout(() => setResult(res.data), 600);
    } catch (e) {
      setError(e.response?.data?.detail || "Pipeline failed. Is the backend running?");
    } finally {
      setAnalyzing(false);
    }
  };

  const fmt = (s) => `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center space-y-5">
        <div className="flex flex-col items-center gap-2">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl border-2 transition-all duration-300
            ${recording ? "border-red-500 bg-red-500/10 animate-pulse" : "border-white/10 bg-white/5"}`}>
            🎙
          </div>
          {recording && (
            <div className="flex items-center gap-2 text-red-400 text-sm font-mono">
              <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse"></span>
              {fmt(seconds)}
            </div>
          )}
          {!recording && !audioBlob && (
            <p className="text-gray-500 text-sm">Press Start to record your meeting</p>
          )}
          {transcribing && (
            <p className="text-blue-400 text-xs animate-pulse">Transcribing with Whisper...</p>
          )}
        </div>

        <div className="flex justify-center gap-3">
          {!recording ? (
            <button onClick={startRecording} disabled={analyzing}
              className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition">
              🔴 Start Recording
            </button>
          ) : (
            <button onClick={stopRecording}
              className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition">
              ⏹ Stop Recording
            </button>
          )}
          {audioBlob && !recording && !transcribing && (
            <button onClick={runPipeline} disabled={analyzing}
              className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition">
              {analyzing ? "Analysing..." : "⚡ Analyse Deal"}
            </button>
          )}
        </div>

        {audioUrl && !recording && (
          <audio controls src={audioUrl} className="w-full mt-2 rounded-lg" />
        )}
      </div>

      {(transcribing || transcript) && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Live Transcript</p>
          {transcribing ? (
            <div className="flex items-center gap-2 text-blue-400 text-sm">
              <div className="w-3 h-3 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              Transcribing with Whisper...
            </div>
          ) : (
            <p className="text-gray-300 text-sm leading-relaxed">{transcript}</p>
          )}
        </div>
      )}

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
                  <p className={`text-sm font-medium ${done ? "text-green-300" : active ? "text-blue-300" : "text-gray-500"}`}>{stage.label}</p>
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
