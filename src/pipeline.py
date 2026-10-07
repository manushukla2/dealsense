import logging
import uuid
from pathlib import Path
from typing import Optional

from src.audio.diarize import diarize_audio
from src.audio.merge import build_transcript
from src.audio.preprocess import preprocess_audio
from src.audio.transcribe import transcribe_audio
from src.nlp.segmenter import segment_exchanges
from src.nlp.sentiment_intent import analyze_exchanges
from src.reasoning.explain import explain_meeting
from src.schemas import MeetingResult
from src.scoring.calibrate import Calibrator
from src.scoring.features import extract_features
from src.scoring.scorer import DealScorer

logger = logging.getLogger(__name__)
_scorer = DealScorer()
_calibrator = Calibrator.load()


def run(
    audio_path: Path,
    meeting_id: Optional[str] = None,
    num_speakers: int = 2,
    language: Optional[str] = None,
    denoise: bool = False,
    rep_speaker: Optional[str] = None,
    use_llm: bool = True,
) -> MeetingResult:
    audio_path = Path(audio_path)
    meeting_id = meeting_id or str(uuid.uuid4())
    logger.info("Pipeline started: %s", audio_path.name)

    wav = preprocess_audio(audio_path, denoise=denoise)
    transcription = transcribe_audio(wav, language=language)
    diarization = diarize_audio(wav, num_speakers=num_speakers)
    transcript = build_transcript(transcription, diarization, rep_speaker=rep_speaker)
    exchanges = segment_exchanges(transcript)
    analyses = analyze_exchanges(exchanges)
    features = extract_features(analyses, transcript)
    score = _scorer.predict(features)
    percent = _calibrator.transform(score.probability) * 100
    explanation = explain_meeting(
        exchanges, analyses, score, percent,
        calibration_note=_calibrator.describe(),
        use_llm=use_llm,
    )

    from src.schemas import DealPrediction
    prediction = DealPrediction(
        probability=score.probability,
        verdict=explanation.verdict,
        summary=explanation.summary,
        positives=explanation.positives,
        risks=explanation.risks,
        analyses=analyses,
    )
    return MeetingResult(
        meeting_id=meeting_id,
        source_file=audio_path.name,
        transcript=transcript,
        prediction=prediction,
    )
