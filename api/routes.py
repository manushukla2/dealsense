import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from api.db import get_db, MeetingRecord
from src.audio.preprocess import preprocess
from src.audio.transcribe import transcribe
from src.audio.diarize import diarize
from src.audio.merge import merge
from src.nlp.segmenter import segment_transcript
from src.nlp.sentiment_intent import analyse
from src.nlp.signals import detect_signals
from src.scoring.features import extract_features
from src.scoring.scorer import DealScorer
from src.scoring.calibrate import Calibrator
from src.reasoning.explain import explain_meeting
from src.schemas import MeetingResult
import tempfile, os

router = APIRouter()
scorer = DealScorer()
calibrator = Calibrator.load()

@router.post("/upload")
async def upload_meeting(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".wav", ".mp3", ".m4a", ".mp4")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    meeting_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        audio = preprocess(tmp_path)
        segments = transcribe(audio)
        diarization = diarize(audio)
        transcript = merge(segments, diarization)
        exchanges = segment_transcript(transcript)
        analyses = [analyse(ex) for ex in exchanges]
        analyses = [detect_signals(ex, an) for ex, an in zip(exchanges, analyses)]
        features = extract_features(analyses)
        score = scorer.predict(features)
        percent = calibrator.transform(score.probability) * 100
        explanation = explain_meeting(exchanges, analyses, score, percent, calibrator.describe())

        record = MeetingRecord(
            meeting_id=meeting_id,
            source_file=file.filename,
            probability=score.probability,
            verdict=explanation.verdict,
            summary=explanation.summary,
            transcript=transcript.model_dump(),
            prediction={
                "probability": score.probability,
                "percent": percent,
                "verdict": explanation.verdict,
                "summary": explanation.summary,
                "positives": explanation.positives,
                "risks": explanation.risks,
                "moments": [m.__dict__ for m in explanation.moments],
                "next_step": explanation.next_step,
                "source": explanation.source,
                "warnings": explanation.warnings,
            }
        )
        db.add(record)
        db.commit()

        return {"meeting_id": meeting_id, "result": record.prediction}

    finally:
        os.unlink(tmp_path)


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    record = db.query(MeetingRecord).filter(MeetingRecord.meeting_id == meeting_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"meeting_id": record.meeting_id, "result": record.prediction}


@router.get("/meetings")
def list_meetings(db: Session = Depends(get_db)):
    records = db.query(MeetingRecord).order_by(MeetingRecord.created_at.desc()).limit(20).all()
    return [{"meeting_id": r.meeting_id, "source_file": r.source_file, "verdict": r.verdict, "probability": r.probability} for r in records]
