import logging
from dataclasses import dataclass
from typing import Optional

from src.audio.diarize import SpeakerSegment
from src.audio.transcribe import Segment, TranscriptionResult, Word
from src.schemas import Role, Transcript, Turn

logger = logging.getLogger(__name__)

MAX_SNAP_SECONDS = 1.0       # a word that overlaps nobody snaps to a speaker this close
MAX_TURN_GAP_SECONDS = 3.0   # same speaker, pause shorter than this -> one turn
DEFAULT_SPEAKER = "SPEAKER_00"


@dataclass
class _Piece:
    speaker: str
    start: float
    end: float
    text: str


def _mid(word: Word) -> float:
    return (word.start + word.end) / 2


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _distance(moment: float, seg: SpeakerSegment) -> float:
    if seg.start <= moment <= seg.end:
        return 0.0
    return min(abs(moment - seg.start), abs(moment - seg.end))


def _speaker_for_span(start: float, end: float, diarization: list[SpeakerSegment]) -> Optional[str]:
    """Who talks the most between start and end; if nobody, the closest speaker (within 1 s)."""
    if not diarization:
        return None
    totals: dict[str, float] = {}
    for seg in diarization:
        shared = _overlap(start, end, seg.start, seg.end)
        if shared > 0:
            totals[seg.speaker] = totals.get(seg.speaker, 0.0) + shared
    if totals:
        return max(totals, key=totals.get)

    moment = (start + end) / 2
    closest = min(diarization, key=lambda s: _distance(moment, s))
    return closest.speaker if _distance(moment, closest) <= MAX_SNAP_SECONDS else None


def _pieces_for_segment(
    seg: Segment,
    seg_words: list[Word],
    diarization: list[SpeakerSegment],
    previous_speaker: Optional[str],
) -> list[_Piece]:
    """Turn one Whisper segment into one or more single-speaker pieces."""
    if not seg_words:
        speaker = _speaker_for_span(seg.start, seg.end, diarization) or previous_speaker or DEFAULT_SPEAKER
        return [_Piece(speaker, seg.start, seg.end, seg.text.strip())]

    labelled = []
    for word in seg_words:
        speaker = (
            _speaker_for_span(word.start, word.end, diarization)
            or (labelled[-1][1] if labelled else None)
            or previous_speaker
            or DEFAULT_SPEAKER
        )
        labelled.append((word, speaker))

    # Group consecutive words by speaker.
    runs: list[tuple[str, list[Word]]] = []
    for word, speaker in labelled:
        if runs and runs[-1][0] == speaker:
            runs[-1][1].append(word)
        else:
            runs.append((speaker, [word]))

    if len(runs) == 1:
        return [_Piece(runs[0][0], seg.start, seg.end, seg.text.strip())]

    # Speaker changed inside the segment: split the text, keeping punctuation if we can.
    tokens = seg.text.split()
    can_split_text = len(tokens) == len(seg_words)
    pieces: list[_Piece] = []
    cursor = 0
    for speaker, run_words in runs:
        if can_split_text:
            text = " ".join(tokens[cursor : cursor + len(run_words)])
        else:
            text = " ".join(w.text for w in run_words)
        cursor += len(run_words)
        pieces.append(_Piece(speaker, run_words[0].start, run_words[-1].end, text))
    return pieces


def _merge_pieces(pieces: list[_Piece]) -> list[Turn]:
    """Join consecutive pieces by the same speaker into turns."""
    turns: list[Turn] = []
    for piece in pieces:
        if not piece.text.strip():
            continue
        if (
            turns
            and turns[-1].speaker == piece.speaker
            and piece.start - turns[-1].end <= MAX_TURN_GAP_SECONDS
        ):
            turns[-1].text = f"{turns[-1].text} {piece.text}".strip()
            turns[-1].end = max(turns[-1].end, piece.end)
        else:
            turns.append(Turn(speaker=piece.speaker, start=piece.start, end=piece.end, text=piece.text.strip()))
    return turns


def assign_roles(turns: list[Turn], rep_speaker: Optional[str] = None) -> list[Turn]:
    """Label each turn REP or CLIENT.

    Rule of thumb: the person who talks the most is the sales rep. Pass
    rep_speaker (e.g. "SPEAKER_01") to override the guess.
    """
    word_counts: dict[str, int] = {}
    for turn in turns:
        word_counts[turn.speaker] = word_counts.get(turn.speaker, 0) + len(turn.text.split())

    if len(word_counts) < 2:
        logger.warning("Only one speaker found; roles left as unknown.")
        return turns

    rep = rep_speaker or max(word_counts, key=word_counts.get)
    return [
        turn.model_copy(update={"role": Role.REP if turn.speaker == rep else Role.CLIENT})
        for turn in turns
    ]


def swap_roles(transcript: Transcript) -> Transcript:
    """Flip REP and CLIENT (for when the automatic guess is wrong)."""
    flipped = {Role.REP: Role.CLIENT, Role.CLIENT: Role.REP}
    turns = [t.model_copy(update={"role": flipped.get(t.role, t.role)}) for t in transcript.turns]
    return transcript.model_copy(update={"turns": turns})


def build_transcript(
    transcription: TranscriptionResult,
    diarization: list[SpeakerSegment],
    rep_speaker: Optional[str] = None,
) -> Transcript:
    """Combine Whisper text and pyannote speaker labels into a speaker-labelled Transcript."""
    words = sorted(transcription.words, key=lambda w: w.start)
    segments = sorted(transcription.segments, key=lambda s: s.start)

    pieces: list[_Piece] = []
    index = 0
    previous_speaker: Optional[str] = None
    for seg in segments:
        while index < len(words) and _mid(words[index]) < seg.start:
            index += 1
        seg_words: list[Word] = []
        while index < len(words) and _mid(words[index]) <= seg.end:
            seg_words.append(words[index])
            index += 1

        new_pieces = _pieces_for_segment(seg, seg_words, diarization, previous_speaker)
        pieces.extend(new_pieces)
        previous_speaker = new_pieces[-1].speaker

    turns = assign_roles(_merge_pieces(pieces), rep_speaker)
    return Transcript(turns=turns, language=transcription.language, duration=transcription.duration)
