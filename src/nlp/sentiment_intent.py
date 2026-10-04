import logging
from dataclasses import dataclass
from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.nlp.signals import extract_signals, net_signal_score
from src.schemas import Exchange, ExchangeAnalysis, Role, Sentiment

logger = logging.getLogger(__name__)

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
NLI_MODEL = "cross-encoder/nli-distilroberta-base"
MAX_TOKENS = 256

# How the three evidence sources are blended into one score for an exchange (first guesses).
W_SIGNALS = 0.40
W_INTENT = 0.35
W_SENTIMENT = 0.25
SENTIMENT_THRESHOLD = 0.25   # |score| above this counts as positive / negative, else neutral


@dataclass(frozen=True)
class Intent:
    key: str
    hypothesis: str   # sentence the NLI model tests against the client's words
    phrase: str       # plain-English wording used in the reasoning
    value: float      # how good this intent is for the deal (-1 to +1)


INTENTS: list[Intent] = [
    Intent("ready_to_proceed", "The customer wants to move forward with the purchase.", "ready to move forward", 0.9),
    Intent("interested", "The customer is interested and wants to learn more.", "interested and wanting to learn more", 0.5),
    Intent("evaluating", "The customer is asking how the product works.", "evaluating how the product works", 0.3),
    Intent("small_talk", "The customer is greeting or making small talk.", "making small talk", 0.0),
    Intent("price_concern", "The customer thinks the price is too high.", "worried about the price", -0.4),
    Intent("comparing", "The customer is comparing other options.", "comparing other options", -0.3),
    Intent("stalling", "The customer wants to delay the decision.", "wanting to delay the decision", -0.5),
    Intent("rejecting", "The customer is not interested.", "not interested", -0.9),
]


@dataclass
class TextReading:
    """What the two models concluded about a piece of client speech."""

    sentiment_score: float          # -1 (negative) .. +1 (positive)
    sentiment: Sentiment
    intent: Intent                  # the most likely intent
    intent_confidence: float        # 0..1, share of probability on that intent
    intent_value: float             # probability-weighted deal value of all intents, -1..1
    intent_probs: dict[str, float]


@lru_cache(maxsize=4)
def _load(model_name: str):
    """Download (first run) and load a model once per run."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    if torch.cuda.is_available():
        model.to("cuda")
    return tokenizer, model


def _label_index(model, wanted: str) -> int:
    """Find which output column holds a label such as 'positive' or 'entailment'."""
    for index, name in model.config.id2label.items():
        if str(name).lower() == wanted:
            return int(index)
    raise RuntimeError(f"Label '{wanted}' not found in {model.config.id2label}")


def _logits(model_name: str, first: list[str], second: list[str] | None = None) -> torch.Tensor:
    tokenizer, model = _load(model_name)
    batch = tokenizer(
        first, second, padding=True, truncation=True,
        max_length=MAX_TOKENS, return_tensors="pt",
    )
    device = next(model.parameters()).device
    batch = {key: value.to(device) for key, value in batch.items()}
    with torch.no_grad():
        return model(**batch).logits.float().cpu()


def _sentiment_score(text: str) -> float:
    """Positive probability minus negative probability, from -1 to +1."""
    _, model = _load(SENTIMENT_MODEL)
    probs = torch.softmax(_logits(SENTIMENT_MODEL, [text]), dim=-1)[0]
    return float(probs[_label_index(model, "positive")] - probs[_label_index(model, "negative")])


def _sentiment_label(score: float) -> Sentiment:
    if score > SENTIMENT_THRESHOLD:
        return Sentiment.POSITIVE
    if score < -SENTIMENT_THRESHOLD:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


def _intent_probs(text: str) -> dict[str, float]:
    """Zero-shot intent: how strongly does the text entail each intent sentence?"""
    _, model = _load(NLI_MODEL)
    entail = _label_index(model, "entailment")
    logits = _logits(NLI_MODEL, [text] * len(INTENTS), [intent.hypothesis for intent in INTENTS])
    probs = torch.softmax(logits[:, entail], dim=0)
    return {intent.key: float(p) for intent, p in zip(INTENTS, probs)}


def analyze_text(text: str) -> TextReading:
    """Run both models on one piece of client speech."""
    score = _sentiment_score(text)
    probs = _intent_probs(text)
    top = max(INTENTS, key=lambda intent: probs[intent.key])
    expected = sum(probs[intent.key] * intent.value for intent in INTENTS)
    return TextReading(
        sentiment_score=score,
        sentiment=_sentiment_label(score),
        intent=top,
        intent_confidence=probs[top.key],
        intent_value=expected,
        intent_probs=probs,
    )


def _client_text(exchange: Exchange) -> str:
    """What the client said in this exchange (all turns if roles are unknown)."""
    has_roles = any(turn.role != Role.UNKNOWN for turn in exchange.turns)
    turns = [t for t in exchange.turns if t.role == Role.CLIENT] if has_roles else exchange.turns
    return " ".join(turn.text.strip() for turn in turns).strip()


def analyze_exchange(exchange: Exchange) -> ExchangeAnalysis:
    """Score one exchange using rule signals, intent and sentiment together."""
    signals = extract_signals(exchange)
    signal_lines = [f'{s.label} ({s.speaker} {s.timestamp}): "{s.quote}"' for s in signals]

    text = _client_text(exchange)
    if not text:
        return ExchangeAnalysis(
            exchange_index=exchange.index,
            sentiment=Sentiment.NEUTRAL,
            intent="no_client_response",
            signals=signal_lines,
            score=0.0,
            reasoning="The client did not reply in this exchange, so there is nothing to score.",
        )

    reading = analyze_text(text)
    blended = (
        W_SIGNALS * net_signal_score(signals)
        + W_INTENT * reading.intent_value
        + W_SENTIMENT * reading.sentiment_score
    )
    score = round(max(-1.0, min(1.0, blended)), 2)

    quote = text if len(text) <= 160 else text[:157] + "..."
    parts = [
        f'Client said: "{quote}"',
        f"This reads as {reading.intent.phrase} (about {reading.intent_confidence:.0%} confident), "
        f"with a {reading.sentiment.value} tone.",
    ]
    if signals:
        parts.append("Evidence: " + "; ".join(s.label for s in signals) + ".")
    else:
        parts.append("No specific buying or risk signals were found.")

    return ExchangeAnalysis(
        exchange_index=exchange.index,
        sentiment=reading.sentiment,
        intent=reading.intent.key,
        signals=signal_lines,
        score=score,
        reasoning=" ".join(parts),
    )


def analyze_exchanges(exchanges: list[Exchange]) -> list[ExchangeAnalysis]:
    """Analyse every exchange of a meeting, in order."""
    results = []
    for exchange in exchanges:
        logger.info("Analysing exchange %s/%s", exchange.index + 1, len(exchanges))
        results.append(analyze_exchange(exchange))
    return results
