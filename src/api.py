from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import tempfile, shutil, os, subprocess, uuid
from pathlib import Path
from src.pipeline import run
from src.audio.transcribe import transcribe_audio
from src.nlp.segmenter import segment_exchanges
from src.nlp.sentiment_intent import analyze_exchanges
from src.reasoning.explain import explain_meeting
from src.scoring.calibrate import Calibrator
from src.scoring.features import extract_features
from src.scoring.scorer import DealScorer
from src.schemas import MeetingResult, DealPrediction, Transcript, Turn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_scorer = DealScorer()
_calibrator = Calibrator.load()

def to_wav(input_path: Path) -> Path:
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
        if tmp_path.exists(): os.unlink(tmp_path)
        if wav_path and wav_path != tmp_path and wav_path.exists(): os.unlink(wav_path)
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
            "segments": [{"text": s.text, "start": s.start, "end": s.end} for s in result.segments]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists(): os.unlink(tmp_path)
        if wav_path and wav_path != tmp_path and wav_path.exists(): os.unlink(wav_path)

@app.post("/predict-text")
async def predict_text(payload: dict = Body(...)):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        meeting_id = str(uuid.uuid4())
        # Build a simple transcript from raw text
        lines = text.strip().split("\n")
        turns = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            # Detect "SPEAKER: text" format or alternate speakers
            if ":" in line:
                parts = line.split(":", 1)
                speaker = parts[0].strip().upper()
                t = parts[1].strip()
            else:
                speaker = "SPEAKER_00" if i % 2 == 0 else "SPEAKER_01"
                t = line
            turns.append(Turn(speaker=speaker, text=t, start=0.0, end=0.0))

        transcript = Transcript(turns=turns, num_speakers=2)
        exchanges = segment_exchanges(transcript)
        analyses = analyze_exchanges(exchanges)
        features = extract_features(analyses, transcript)
        score = _scorer.predict(features)
        percent = _calibrator.transform(score.probability) * 100
        explanation = explain_meeting(
            exchanges, analyses, score, percent,
            calibration_note=_calibrator.describe(),
            use_llm=False,
        )
        prediction = DealPrediction(
            probability=score.probability,
            verdict=explanation.verdict,
            summary=explanation.summary,
            positives=explanation.positives,
            risks=explanation.risks,
            analyses=analyses,
        )
        result = MeetingResult(
            meeting_id=meeting_id,
            source_file="text-input",
            transcript=transcript,
            prediction=prediction,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
