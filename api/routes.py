import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.db import MeetingRecord, get_db
from config.settings import settings
from src.pipeline import run

router = APIRouter()


def _save(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _record_from(meeting_id: str, filename: str, result) -> MeetingRecord:
    p = result.prediction
    exp = None
    moments = []
    return MeetingRecord(
        meeting_id=meeting_id,
        source_file=filename,
        probability=p.probability if p else None,
        verdict=p.verdict if p else None,
        summary=p.summary if p else None,
        transcript=result.transcript.model_dump(),
        prediction={
            "probability": p.probability if p else None,
            "verdict": p.verdict if p else None,
            "summary": p.summary if p else None,
            "positives": p.positives if p else [],
            "risks": p.risks if p else [],
            "next_step": "",
            "source": "pipeline",
            "warnings": [],
        } if p else {},
    )


@router.post("/upload")
async def upload_meeting(
    file: UploadFile,
    num_speakers: int = 2,
    use_llm: bool = True,
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".wav", ".mp3", ".m4a", ".flac", ".mp4", ".webm", ".mov"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    meeting_id = str(uuid.uuid4())
    audio_path = settings.raw_dir / f"{meeting_id}{ext}"

    try:
        _save(audio_path, await file.read())
        result = run(
            audio_path,
            meeting_id=meeting_id,
            num_speakers=num_speakers,
            use_llm=use_llm,
        )
        record = _record_from(meeting_id, file.filename, result)
        db.add(record)
        db.commit()
        return {"meeting_id": meeting_id, "result": record.prediction}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    record = db.query(MeetingRecord).filter(MeetingRecord.meeting_id == meeting_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"meeting_id": record.meeting_id, "result": record.prediction}


@router.get("/meetings")
def list_meetings(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    records = (
        db.query(MeetingRecord)
        .order_by(MeetingRecord.created_at.desc())
        .offset(skip).limit(limit).all()
    )
    return [
        {
            "meeting_id": r.meeting_id,
            "source_file": r.source_file,
            "verdict": r.verdict,
            "probability": r.probability,
        }
        for r in records
    ]


@router.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    record = db.query(MeetingRecord).filter(MeetingRecord.meeting_id == meeting_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(record)
    db.commit()
    return {"deleted": meeting_id}
