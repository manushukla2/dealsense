from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def format_timestamp(seconds: float) -> str:
    """Turn seconds into a MM:SS string, e.g. 252.4 -> '04:12'."""
    total = int(max(seconds, 0))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


class Role(str, Enum):
    CLIENT = "client"
    REP = "rep"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ---------- Stage 1: transcript ----------

class Turn(BaseModel):
    """One continuous piece of speech by one speaker."""

    speaker: str = "SPEAKER_00"
    role: Role = Role.UNKNOWN
    start: float
    end: float
    text: str

    @property
    def timestamp(self) -> str:
        return format_timestamp(self.start)

    @property
    def label(self) -> str:
        if self.role != Role.UNKNOWN:
            return self.role.value.upper()
        return self.speaker


class Transcript(BaseModel):
    """The full meeting as an ordered list of turns."""

    turns: list[Turn] = Field(default_factory=list)
    language: Optional[str] = None
    duration: float = 0.0

    def as_text(self) -> str:
        return "\n".join(
            f"[{t.label} {t.timestamp}] {t.text.strip()}" for t in self.turns
        )


# ---------- Stage 2: exchanges and their analysis ----------

class Exchange(BaseModel):
    """A short back-and-forth: statement -> reply -> response."""

    index: int
    turns: list[Turn]

    @property
    def start(self) -> float:
        return self.turns[0].start if self.turns else 0.0

    @property
    def end(self) -> float:
        return self.turns[-1].end if self.turns else 0.0

    @property
    def text(self) -> str:
        return "\n".join(
            f"[{t.label} {t.timestamp}] {t.text.strip()}" for t in self.turns
        )


class ExchangeAnalysis(BaseModel):
    """What the model concluded about one exchange."""

    exchange_index: int
    sentiment: Sentiment = Sentiment.NEUTRAL
    intent: str = "unknown"
    signals: list[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
    reasoning: str = ""


# ---------- Stage 3: prediction and final result ----------

class DealPrediction(BaseModel):
    """The final verdict for a meeting."""

    probability: float = Field(ge=0.0, le=1.0)
    verdict: str = ""
    summary: str = ""
    positives: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    analyses: list[ExchangeAnalysis] = Field(default_factory=list)

    @property
    def percent(self) -> float:
        return round(self.probability * 100, 1)


class MeetingResult(BaseModel):
    """Everything the pipeline returns for one uploaded meeting."""

    meeting_id: str
    source_file: str
    transcript: Transcript
    prediction: Optional[DealPrediction] = None
