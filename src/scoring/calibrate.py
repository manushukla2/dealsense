import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from config.settings import settings

logger = logging.getLogger(__name__)

CALIBRATOR_FILE = "calibrator.joblib"
MIN_SAMPLES_PLATT = 30       # below this many real outcomes, leave the score unchanged
MIN_SAMPLES_ISOTONIC = 200   # from this many, use the more flexible method
MIN_PER_CLASS = 5            # need at least this many won AND lost meetings
FLOOR = 0.02                 # never show below 2% or above 98%: a model is never that sure
CEIL = 0.98
EPS = 1e-6


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _as_arrays(raw, outcomes) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(raw, dtype=float).ravel()
    y = np.asarray(outcomes, dtype=int).ravel()
    if len(p) != len(y):
        raise ValueError(f"{len(p)} predictions but {len(y)} outcomes.")
    return p, y


# ---------- measuring how trustworthy the percentages are ----------

def brier_score(raw, outcomes) -> float:
    """Average squared miss between the predicted chance and what happened. Lower is better."""
    p, y = _as_arrays(raw, outcomes)
    return float(np.mean((p - y) ** 2))


def _bin_index(p: np.ndarray, bins: int) -> np.ndarray:
    return np.minimum((np.clip(p, 0, 1) * bins).astype(int), bins - 1)


def expected_calibration_error(raw, outcomes, bins: int = 10) -> float:
    """Average gap between 'predicted chance' and 'share that really won', per band. Lower is better."""
    p, y = _as_arrays(raw, outcomes)
    index = _bin_index(p, bins)
    total, error = len(p), 0.0
    for b in range(bins):
        mask = index == b
        if mask.any():
            error += mask.sum() / total * abs(p[mask].mean() - y[mask].mean())
    return float(error)


def reliability_table(raw, outcomes, bins: int = 5) -> list[dict]:
    """For each probability band: how many meetings, what was predicted, what actually happened."""
    p, y = _as_arrays(raw, outcomes)
    index = _bin_index(p, bins)
    rows = []
    for b in range(bins):
        mask = index == b
        if mask.any():
            rows.append({
                "band": f"{b / bins:.0%}-{(b + 1) / bins:.0%}",
                "count": int(mask.sum()),
                "predicted": round(float(p[mask].mean()), 3),
                "actual_win_rate": round(float(y[mask].mean()), 3),
            })
    return rows


def evaluate(raw, outcomes) -> dict:
    p, _ = _as_arrays(raw, outcomes)
    return {
        "n": len(p),
        "brier": round(brier_score(raw, outcomes), 4),
        "ece": round(expected_calibration_error(raw, outcomes), 4),
    }


# ---------- the calibrator itself ----------

def default_calibrator_path() -> Path:
    return settings.models_dir / "scorer" / CALIBRATOR_FILE


class Calibrator:
    """Maps the scorer's raw probability onto the real-world win rate."""

    def __init__(self) -> None:
        self.method = "identity"
        self.n_samples = 0
        self._model = None

    def fit(self, raw, outcomes) -> "Calibrator":
        """Learn the mapping from past meetings. raw = scorer outputs, outcomes = 1 won / 0 lost."""
        p, y = _as_arrays(raw, outcomes)
        n = len(p)
        won = int(y.sum())
        lost = n - won
        self.n_samples = n
        self._model = None
        self.method = "identity"

        if n < MIN_SAMPLES_PLATT or min(won, lost) < MIN_PER_CLASS:
            logger.warning(
                "Only %s meetings (%s won, %s lost): not enough to calibrate, scores left unchanged.",
                n, won, lost,
            )
            return self

        if n < MIN_SAMPLES_ISOTONIC:
            model = LogisticRegression(C=10.0)
            model.fit(_logit(p).reshape(-1, 1), y)
            self.method = "platt"
        else:
            model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            model.fit(p, y)
            self.method = "isotonic"
        self._model = model
        return self

    def transform_many(self, raw) -> np.ndarray:
        p = np.asarray(raw, dtype=float).ravel()
        if self.method == "platt":
            out = self._model.predict_proba(_logit(p).reshape(-1, 1))[:, 1]
        elif self.method == "isotonic":
            out = self._model.predict(p)
        else:
            out = p
        return np.clip(out, FLOOR, CEIL)

    def transform(self, probability: float) -> float:
        return float(self.transform_many([probability])[0])

    def describe(self) -> str:
        if self.method == "identity":
            return "not calibrated yet (no real won/lost data); percentages are estimates"
        return f"calibrated with {self.method} regression on {self.n_samples} past meetings"

    def save(self, path: Optional[Path] = None) -> Path:
        path = Path(path) if path else default_calibrator_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"method": self.method, "n_samples": self.n_samples, "model": self._model}, path)
        return path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Calibrator":
        """Load a saved calibrator, or an 'identity' one if none has been trained yet."""
        calibrator = cls()
        path = Path(path) if path else default_calibrator_path()
        if path.exists():
            bundle = joblib.load(path)
            calibrator.method = bundle["method"]
            calibrator.n_samples = bundle["n_samples"]
            calibrator._model = bundle["model"]
        return calibrator
