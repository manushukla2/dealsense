"""
Evaluate the current scorer and calibrator against a labelled JSONL file.
Run:  python -m training.evaluate
      python -m training.evaluate --data data/synthetic/synthetic_calls.jsonl
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)

from config.settings import settings
from src.nlp.segmenter import segment_exchanges
from src.nlp.sentiment_intent import analyze_exchanges
from src.schemas import Transcript, Turn, Role
from src.scoring.calibrate import Calibrator, evaluate, reliability_table
from src.scoring.features import extract_features
from src.scoring.scorer import DealScorer

DEFAULT_DATA = settings.processed_dir / "scorer_train.jsonl"


def _transcript_from_text(text: str) -> Transcript:
    turns = []
    for i, line in enumerate(text.strip().splitlines()):
        if ":" not in line:
            continue
        speaker, _, utt = line.partition(":")
        role = Role.REP if speaker.strip().upper() == "REP" else Role.CLIENT
        turns.append(Turn(speaker=speaker.strip(), role=role,
                          start=float(i * 8), end=float(i * 8 + 6), text=utt.strip()))
    return Transcript(turns=turns, duration=float(len(turns) * 8))


def run_eval(data_path: Path) -> None:
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Evaluating on {len(rows)} rows from {data_path}\n")

    scorer = DealScorer()
    calibrator = Calibrator.load()
    print("Scorer source:", scorer.source)
    print("Calibrator:   ", calibrator.describe(), "\n")

    probs_raw, probs_cal, labels = [], [], []
    for i, row in enumerate(rows):
        try:
            transcript = _transcript_from_text(row["text"])
            exchanges = segment_exchanges(transcript)
            analyses = analyze_exchanges(exchanges)
            features = extract_features(analyses, transcript)
            score = scorer.predict(features)
            probs_raw.append(score.probability)
            probs_cal.append(calibrator.transform(score.probability))
            labels.append(int(row["label"]))
        except Exception as exc:
            print(f"  skipped row {i}: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  processed {i + 1}/{len(rows)}")

    y = np.array(labels)
    raw = np.array(probs_raw)
    cal = np.array(probs_cal)
    preds = (cal >= 0.5).astype(int)

    print("\n--- Raw scorer ---")
    print(evaluate(raw, y))
    print("\n--- Calibrated ---")
    print(evaluate(cal, y))

    try:
        print(f"\nAUC (calibrated): {roc_auc_score(y, cal):.4f}")
    except Exception:
        pass

    print(f"\nAccuracy at 0.5 threshold: {accuracy_score(y, preds):.4f}")
    print("\nClassification report:")
    print(classification_report(y, preds, target_names=["lost", "won"]))

    print("\nReliability table (calibrated):")
    for row in reliability_table(cal, y):
        print(" ", row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    run_eval(args.data)
