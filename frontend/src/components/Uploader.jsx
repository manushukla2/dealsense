import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";

export default function Uploader({ setResult, setLoading, setError }) {
  const [fileName, setFileName] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setFileName(file.name);
    setResult(null);
    setError(null);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8000/predict", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Something went wrong. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  }, [setResult, setLoading, setError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "audio/*": [] },
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`mx-auto w-full max-w-lg rounded-2xl border-2 border-dashed p-12 text-center cursor-pointer transition-all duration-300
        ${isDragActive
          ? "border-blue-500 bg-blue-500/10 scale-105"
          : "border-white/10 hover:border-blue-500/50 hover:bg-white/5 bg-white/[0.03]"
        }`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 border border-white/10 flex items-center justify-center text-2xl">
          🎙
        </div>
        <p className="text-gray-300 text-sm font-medium">
          {isDragActive ? "Drop it here..." : "Drag & drop your meeting audio"}
        </p>
        <p className="text-gray-600 text-xs">or click to browse · WAV, MP3, M4A supported</p>
        {fileName && (
          <div className="mt-2 flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-blue-400 text-xs">
            <span>📎</span> {fileName}
          </div>
        )}
      </div>
    </div>
  );
}
