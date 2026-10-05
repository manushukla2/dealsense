import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

from config.settings import settings
from src.nlp.signals import RULES
from src.scoring.features import FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_FILE = "scorer.joblib"
SIGNAL_CAP = 2            # a signal seen in more than 2 exchanges stops adding weight
MIN_EXCHANGES = 3         # fewer than this -> result is flagged as low-confidence
MAX_DRIVERS = 8
MIN_DRIVER_EFFECT = 0.005   # ignore drivers that move the answer by less than 0.5 points

# ---------- Starting formula (used until a trained model exists) ----------
HEURISTIC_BIAS = -0.4     # a meeting with no evidence either way lands a little under 50%

HEURISTIC_COEFS: dict[str, float] = {
    "mean_score": 1.2,
    "late_weighted_mean": 1.2,
    "last3_mean": 0.6,
    "min_score": 0.4,
    "trend": 0.3,
    "frac_positive": 0.5,
    "frac_negative": -0.8,
}

SIGNAL_COEFS: dict[str, float] = {
    "rejection": -1.2,
    "stalling": -0.7,
    "strong_interest": 0.8,
    "budget_confirmed": 0.4,
    "decision_maker_involved": 0.3,
    "next_step_requested": 0.25,
    "timeline_stated": 0.2,
    "technical_evaluation": 0.15,
    "mild_interest": 0.15,
    "competitor_mentioned": -0.25,
    "price_objection": -0.25,
    "concern_raised": -0.25,
}

NEUTRAL_VALUES = {"client_word_share": 0.5}
SKIP_FOR_DRIVERS = {"n_exchanges", "duration_minutes", "n_turns", "client_word_share"}

DESCRIPTIONS: dict[str, str] = {
    "mean_score": "Overall tone of the whole meeting",
    "late_weighted_mean": "How the later part of the meeting went",
    "last3_mean": "How the meeting ended",
    "min_score": "The worst moment in the meeting",
    "trend": "Direction of the meeting (improving or getting worse)",
    "frac_positive": "Share of exchanges with a positive tone",
    "frac_negative": "Share of exchanges with a negative tone",
}
DESCRIPTIONS.update({f"sig_{rule.name}": rule.label for rule in RULES})


@dataclass
class Driver:
    """One factor that pushed the probability up or down."""

    feature: str
    description: str
    effect_points: float     # percentage points; positive = pushed the chance up


@dataclass
class DealScore:
    probability: float                       # 0..1 (raw, not yet calibrated)
    source: str                              # "heuristic" or "trained"
    drivers: list[Driver] = field(default_factory=list)
    low_data: bool = False

    @property
    def percent(self) -> float:
        return round(self.probability * 100, 1)

    @property
    def positives(self) -> list[Driver]:
        return [d for d in self.drivers if d.effect_points > 0]

    @property
    def risks(self) -> list[Driver]:
        return [d for d in self.drivers if d.effect_points < 0]


def _sigmoid(value: float) -> float:
    value = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def _heuristic_probability(features: dict[str, float]) -> float:
    z = HEURISTIC_BIAS
    for name, coef in HEURISTIC_COEFS.items():
        z += coef * features.get(name, 0.0)
    for name, coef in SIGNAL_COEFS.items():
        z += coef * min(features.get(f"sig_{name}", 0.0), SIGNAL_CAP)
    return _sigmoid(z)


def default_model_path() -> Path:
    return settings.models_dir / "scorer" / MODEL_FILE


def save_scorer(model: Any, path: Optional[Path] = None, metadata: Optional[dict] = None) -> Path:
    """Save a trained model together with the exact feature order it was trained on."""
    path = Path(path) if path else default_model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_names": list(FEATURE_NAMES), "metadata": metadata or {}},
        path,
    )
    return path


class DealScorer:
    """Turns a meeting's features into a deal probability, plus the reasons behind it."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path) if model_path else default_model_path()
        self._bundle: Optional[dict] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            return
        bundle = joblib.load(self.model_path)
        if bundle.get("feature_names") != list(FEATURE_NAMES):
            logger.warning("Saved scorer was trained on different features; using the starting formula.")
            return
        self._bundle = bundle
        logger.info("Loaded trained scorer from %s", self.model_path)

    @property
    def source(self) -> str:
        return "trained" if self._bundle is not None else "heuristic"

    def _probability(self, features: dict[str, float]) -> float:
        if self._bundle is None:
            return _heuristic_probability(features)
        row = np.array([[features.get(name, 0.0) for name in FEATURE_NAMES]], dtype=float)
        return float(self._bundle["model"].predict_proba(row)[0][1])

    def _drivers(self, features: dict[str, float], probability: float) -> list[Driver]:
        """Switch each feature off (to neutral) one at a time and see how far the answer moves."""
        drivers: list[Driver] = []
        for name in FEATURE_NAMES:
            if name in SKIP_FOR_DRIVERS:
                continue
            neutral = NEUTRAL_VALUES.get(name, 0.0)
            if features.get(name, 0.0) == neutral:
                continue
            altered = dict(features)
            altered[name] = neutral
            effect = probability - self._probability(altered)
            if abs(effect) >= MIN_DRIVER_EFFECT:
                drivers.append(Driver(name, DESCRIPTIONS.get(name, name.replace("_", " ")), round(effect * 100, 1)))
        drivers.sort(key=lambda d: abs(d.effect_points), reverse=True)
        return drivers[:MAX_DRIVERS]

    def predict(self, features: dict[str, float]) -> DealScore:
        """Probability that the meeting leads to a positive result, with its main drivers."""
        n_exchanges = features.get("n_exchanges", 0.0)
        if n_exchanges <= 0:
            return DealScore(probability=0.5, source=self.source, low_data=True)

        probability = self._probability(features)
        return DealScore(
            probability=probability,
            source=self.source,
            drivers=self._drivers(features, probability),
            low_data=n_exchanges < MIN_EXCHANGES,
        )
