from src.schemas import ExchangeAnalysis, Sentiment
from src.scoring.features import extract_features
from src.scoring.scorer import DealScorer


def _analysis(i, score, sentiment, intent, signals=None):
    return ExchangeAnalysis(
        exchange_index=i, score=score, sentiment=sentiment,
        intent=intent, signals=signals or [],
    )


def test_positive_meeting():
    analyses = [
        _analysis(0, 0.5, Sentiment.POSITIVE, "interested",
                  ['Client showed positive interest (CLIENT 00:00): "That could work."']),
        _analysis(1, 0.6, Sentiment.POSITIVE, "ready_to_proceed",
                  ['Client is taking it to a decision-maker (CLIENT 00:05): "Let me check with my CFO."',
                   'A timeline or deadline was mentioned (CLIENT 00:05): "Back to you next week."']),
        _analysis(2, 0.4, Sentiment.POSITIVE, "evaluating",
                  ['Client asked for a concrete next step (CLIENT 00:10): "Send me the document."']),
    ]
    result = DealScorer().predict(extract_features(analyses))
    assert result.probability > 0.6
    assert result.source == "heuristic"
    assert len(result.positives) > 0


def test_negative_meeting():
    analyses = [
        _analysis(0, -0.7, Sentiment.NEGATIVE, "rejecting",
                  ['Client signalled they are not going ahead (CLIENT 00:00): "Not interested."']),
        _analysis(1, -0.5, Sentiment.NEGATIVE, "stalling",
                  ['A competitor or current tool was mentioned (CLIENT 00:05): "Talking to others."']),
    ]
    result = DealScorer().predict(extract_features(analyses))
    assert result.probability < 0.2
    assert len(result.risks) > 0


def test_empty_returns_50():
    result = DealScorer().predict(extract_features([]))
    assert result.probability == 0.5
    assert result.low_data is True


def test_low_data_flag():
    analyses = [_analysis(0, 0.3, Sentiment.POSITIVE, "interested")]
    result = DealScorer().predict(extract_features(analyses))
    assert result.low_data is True
