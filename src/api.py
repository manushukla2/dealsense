from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile, shutil, os, subprocess
from pathlib import Path
from src.pipeline import run
from src.audio.transcribe import transcribe_audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def to_wav(input_path: Path) -> Path:
    """Convert any audio format to 16kHz mono WAV using ffmpeg."""
    wav_path = input_path.with_suffix(".wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)
    ], check=True, capture_output=True)
    return wav_path

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    wav_path = None
    try:
        if suffix.lower() != ".wav":
            wav_path = to_wav(tmp_path)
        else:
            wav_path = tmp_path
        result = run(wav_path, num_speakers=2, use_llm=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            os.unlink(tmp_path)
        if wav_path and wav_path != tmp_path and wav_path.exists():
            os.unlink(wav_path)

    return result

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    wav_path = None
    try:
        if suffix.lower() != ".wav":
            wav_path = to_wav(tmp_path)
        else:
            wav_path = tmp_path
        result = transcribe_audio(wav_path)
        return {
            "text": result.as_text(),
            "language": result.language,
            "duration": result.duration,
            "segments": [
                {"text": s.text, "start": s.start, "end": s.end}
                for s in result.segments
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            os.unlink(tmp_path)
        if wav_path and wav_path != tmp_path and wav_path.exists():
            os.unlink(wav_path)
