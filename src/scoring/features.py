from typing import Optional

import numpy as np
import pandas as pd

from src.nlp.sentiment_intent import INTENTS
from src.nlp.signals import RULES
from src.schemas import ExchangeAnalysis, Role, Sentiment, Transcript

SIGNAL_NAMES = [rule.name for rule in RULES]
INTENT_NAMES = [intent.key for intent in INTENTS] + ["no_client_response"]
RULE_WEIGHT = {rule.name: rule.weight for rule in RULES}
LABEL_TO_NAME = {rule.label: rule.name for rule in RULES}

BASE_FEATURES = [
    # how the scores of the exchanges look overall
    "n_exchanges", "mean_score", "min_score", "max_score", "std_score",
    # how the meeting started, ended and moved
    "first_score", "last_score", "last3_mean", "late_weighted_mean", "trend",
    # tone mix
    "frac_positive", "frac_negative", "frac_neutral",
    # total strength of evidence found
    "positive_signal_weight", "negative_signal_weight",
    # shape of the conversation
    "client_word_share", "duration_minutes", "n_turns",
]

# Fixed order. Every trained model depends on this exact list.
FEATURE_NAMES: list[str] = (
    BASE_FEATURES
    + [f"sig_{name}" for name in SIGNAL_NAMES]
    + [f"intent_{name}" for name in INTENT_NAMES]
)


def _signal_name(signal_text: str) -> Optional[str]:
    """Map a stored signal line ('<label> (CLIENT 04:12): "...") back to its rule name."""
    for label, name in LABEL_TO_NAME.items():
        if signal_text.startswith(label + " ("):
            return name
    return None


def _conversation_shape(transcript: Optional[Transcript]) -> tuple[float, float, float]:
    """(client share of words, duration in minutes, number of turns)."""
    if transcript is None:
        return 0.5, 0.0, 0.0
    client_words = rep_words = 0
    for turn in transcript.turns:
        words = len(turn.text.split())
        if turn.role == Role.CLIENT:
            client_words += words
        elif turn.role == Role.REP:
            rep_words += words
    total = client_words + rep_words
    share = client_words / total if total else 0.5
    return share, transcript.duration / 60.0, float(len(transcript.turns))


def extract_features(
    analyses: list[ExchangeAnalysis],
    transcript: Optional[Transcript] = None,
) -> dict[str, float]:
    """Turn the per-exchange analyses of one meeting into a fixed set of numbers."""
    features = {name: 0.0 for name in FEATURE_NAMES}
    share, minutes, turns = _conversation_shape(transcript)
    features["client_word_share"] = share
    features["duration_minutes"] = minutes
    features["n_turns"] = turns

    n = len(analyses)
    if n == 0:
        return {name: round(value, 4) for name, value in features.items()}

    scores = np.array([a.score for a in analyses], dtype=float)
    features["n_exchanges"] = float(n)
    features["mean_score"] = scores.mean()
    features["min_score"] = scores.min()
    features["max_score"] = scores.max()
    features["std_score"] = scores.std()
    features["first_score"] = scores[0]
    features["last_score"] = scores[-1]
    features["last3_mean"] = scores[-3:].mean()
    features["late_weighted_mean"] = np.average(scores, weights=np.arange(1, n + 1))
    features["trend"] = np.polyfit(np.linspace(0, 1, n), scores, 1)[0] if n >= 2 else 0.0

    for sentiment in (Sentiment.POSITIVE, Sentiment.NEGATIVE, Sentiment.NEUTRAL):
        features[f"frac_{sentiment.value}"] = sum(a.sentiment == sentiment for a in analyses) / n

    positive_weight = negative_weight = 0.0
    for analysis in analyses:
        found = {_signal_name(text) for text in analysis.signals}
        found.discard(None)
        for name in found:
            features[f"sig_{name}"] += 1.0
            weight = RULE_WEIGHT[name]
            if weight > 0:
                positive_weight += weight
            else:
                negative_weight += -weight
        if analysis.intent in INTENT_NAMES:
            features[f"intent_{analysis.intent}"] += 1.0 / n
    features["positive_signal_weight"] = positive_weight
    features["negative_signal_weight"] = negative_weight

    return {name: round(float(value), 4) for name, value in features.items()}


def features_to_vector(features: dict[str, float]) -> list[float]:
    """The feature dict as a list in the one fixed order models are trained on."""
    return [float(features[name]) for name in FEATURE_NAMES]


def features_table(feature_dicts: list[dict[str, float]]) -> pd.DataFrame:
    """Many meetings' features as a table (one row each), ready for training."""
    return pd.DataFrame([features_to_vector(f) for f in feature_dicts], columns=FEATURE_NAMES)


def nonzero_features(features: dict[str, float]) -> dict[str, float]:
    """Only the features that are not zero, for readable debugging."""
    return {name: value for name, value in features.items() if value != 0}
