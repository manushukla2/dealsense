import json
import logging
import re
from dataclasses import dataclass, field

from groq import Groq

from config.settings import settings
from src.reasoning.prompts import (
    SYSTEM_PROMPT,
    VALID_EFFECTS,
    build_repair_prompt,
    build_user_prompt,
)
from src.schemas import Exchange, ExchangeAnalysis, format_timestamp
from src.scoring.scorer import DealScore

logger = logging.getLogger(__name__)

MAX_EXCHANGES_IN_PROMPT = 30
BASE_TOKENS = 1500
TOKENS_PER_EXCHANGE = 220
MAX_OUTPUT_TOKENS = 8000
MAX_LIST_ITEMS = 4
EFFECT_TEXT = {"positive": "Positive (+)", "negative": "Negative (-)", "neutral": "Neutral"}
QUOTE_PATTERN = re.compile(r'["\u201c]([^"\u201c\u201d]{8,}?)["\u201d]')


@dataclass
class Moment:
    exchange: int
    timestamp: str
    what_happened: str
    why_it_matters: str
    effect: str


@dataclass
class Explanation:
    percent: float
    verdict: str
    summary: str
    moments: list[Moment] = field(default_factory=list)
    positives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_step: str = ""
    source: str = "fallback"
    model: str = ""
    warnings: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            self.verdict.upper(),
            f"Estimated chance of a positive result: {self.percent:.0f}%",
            "",
            self.summary,
            "",
        ]
        for number, moment in enumerate(self.moments, start=1):
            lines.append(f"Moment {number} ({moment.timestamp}): {moment.what_happened}")
            lines.append(f"   -> {moment.why_it_matters} [{EFFECT_TEXT.get(moment.effect, 'Neutral')}]")
        if self.positives:
            lines += ["", "What is going well:"] + [f"  + {item}" for item in self.positives]
        if self.risks:
            lines += ["", "What could go wrong:"] + [f"  - {item}" for item in self.risks]
        if self.next_step:
            lines += ["", f"Suggested next step: {self.next_step}"]
        if self.warnings:
            lines += [""] + [f"Note: {warning}" for warning in self.warnings]
        return "\n".join(lines)


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object was found in the reply")
    return json.loads(cleaned[start : end + 1])


def _clean_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value]
    return [item for item in items if item][:MAX_LIST_ITEMS]


def _build_explanation(data: dict, percent: float, exchanges: list[Exchange]) -> Explanation:
    if not isinstance(data, dict):
        raise ValueError("the reply was not a JSON object")
    for key in ("verdict", "summary", "moments"):
        if not data.get(key):
            raise ValueError(f"the reply is missing '{key}'")

    starts = {e.index: format_timestamp(e.start) for e in exchanges}
    raw_moments = data["moments"] if isinstance(data["moments"], list) else []
    moments: list[Moment] = []
    for raw in raw_moments:
        if not isinstance(raw, dict):
            continue
        try:
            index = int(raw.get("exchange", -1))
        except (TypeError, ValueError):
            index = -1
        effect = str(raw.get("effect", "neutral")).strip().lower()
        moments.append(Moment(
            exchange=index,
            timestamp=starts.get(index, str(raw.get("timestamp", ""))),
            what_happened=str(raw.get("what_happened", "")).strip(),
            why_it_matters=str(raw.get("why_it_matters", "")).strip(),
            effect=effect if effect in VALID_EFFECTS else "neutral",
        ))
    if not moments:
        raise ValueError("the reply contains no usable moments")
    moments.sort(key=lambda m: m.exchange)

    return Explanation(
        percent=percent,
        verdict=str(data["verdict"]).strip(),
        summary=str(data["summary"]).strip(),
        moments=moments,
        positives=_clean_list(data.get("positives")),
        risks=_clean_list(data.get("risks")),
        next_step=str(data.get("next_step", "")).strip(),
    )


def _flat(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", text.lower()).split())


def _unmatched_quotes(moments: list[Moment], exchanges: list[Exchange]) -> list[str]:
    transcript = _flat(" ".join(e.text for e in exchanges))
    bad: list[str] = []
    for moment in moments:
        for quote in QUOTE_PATTERN.findall(moment.what_happened):
            for part in re.split(r"\.\.\.|\u2026", quote):
                flat = _flat(part)
                if len(flat.split()) >= 2 and flat not in transcript:
                    bad.append(quote)
                    break
    return bad


def _check_config() -> None:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is empty in .env")
    model = settings.groq_llm_model.strip()
    if not model or model.startswith("your_"):
        raise RuntimeError("GROQ_LLM_MODEL is not set in .env")


def _ask(client: Groq, content: str, max_tokens: int) -> str:
    response = client.chat.completions.create(
        model=settings.groq_llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    if response.choices[0].finish_reason == "length":
        logger.warning("The explanation was cut off at the token limit.")
    return response.choices[0].message.content or ""


def _select_exchanges(
    exchanges: list[Exchange], analyses: list[ExchangeAnalysis]
) -> tuple[list[Exchange], list[ExchangeAnalysis]]:
    if len(exchanges) <= MAX_EXCHANGES_IN_PROMPT:
        return exchanges, analyses
    by_index = {a.exchange_index: a for a in analyses}
    chosen = {exchanges[0].index, exchanges[-1].index}
    ranked = sorted(
        exchanges,
        key=lambda e: abs(by_index[e.index].score) if e.index in by_index else 0.0,
        reverse=True,
    )
    for exchange in ranked:
        if len(chosen) >= MAX_EXCHANGES_IN_PROMPT:
            break
        chosen.add(exchange.index)
    return (
        [e for e in exchanges if e.index in chosen],
        [a for a in analyses if a.exchange_index in chosen],
    )


def _explain_with_llm(exchanges, analyses, score, percent, calibration_note) -> Explanation:
    _check_config()
    chosen, chosen_analyses = _select_exchanges(exchanges, analyses)
    prompt = build_user_prompt(chosen, chosen_analyses, percent, score, calibration_note)

    warnings: list[str] = []
    if len(chosen) < len(exchanges):
        prompt += (
            f"\n\nNOTE: the meeting had {len(exchanges)} exchanges; "
            f"only the {len(chosen)} most important are shown above."
        )
        warnings.append(
            f"Long meeting: the walkthrough covers the {len(chosen)} most important of {len(exchanges)} exchanges."
        )

    client = Groq(api_key=settings.groq_api_key)
    max_tokens = min(MAX_OUTPUT_TOKENS, BASE_TOKENS + TOKENS_PER_EXCHANGE * len(chosen))

    reply = _ask(client, prompt, max_tokens)
    try:
        explanation = _build_explanation(_parse_json(reply), percent, exchanges)
    except ValueError as error:
        logger.warning("First reply was not usable (%s); asking once more.", error)
        reply = _ask(client, prompt + "\n\n" + build_repair_prompt(reply, str(error)), max_tokens)
        explanation = _build_explanation(_parse_json(reply), percent, exchanges)

    unmatched = _unmatched_quotes(explanation.moments, exchanges)
    if unmatched:
        warnings.append(
            f"{len(unmatched)} quoted phrase(s) in the walkthrough could not be matched word for word "
            "to the transcript; check them before relying on them."
        )
    explanation.source = "llm"
    explanation.model = settings.groq_llm_model
    explanation.warnings = warnings
    return explanation


def _verdict_for(percent: float) -> str:
    if percent >= 70:
        return "Leaning positive"
    if percent >= 45:
        return "Mixed, could go either way"
    return "Leaning negative"


def _fallback(exchanges, analyses, score, percent, calibration_note, warnings) -> Explanation:
    starts = {e.index: format_timestamp(e.start) for e in exchanges}
    moments = []
    for analysis in analyses:
        effect = "positive" if analysis.score > 0.15 else "negative" if analysis.score < -0.15 else "neutral"
        moments.append(Moment(
            exchange=analysis.exchange_index,
            timestamp=starts.get(analysis.exchange_index, ""),
            what_happened=analysis.reasoning or "No client reply to analyse.",
            why_it_matters=(
                f"Automatic score for this exchange: {analysis.score:+.2f} "
                "(from -1 very negative to +1 very positive)."
            ),
            effect=effect,
        ))

    if exchanges:
        summary = f"The estimated chance of a positive result is {percent:.0f}%, from the {score.source} scoring method."
        if score.low_data:
            summary += " There is little evidence in this meeting, so treat it as a rough guide."
        if calibration_note:
            summary += f" Calibration status: {calibration_note}."
    else:
        summary = "No conversation was found in this meeting, so there is nothing to explain."

    return Explanation(
        percent=percent,
        verdict=_verdict_for(percent),
        summary=summary,
        moments=moments,
        positives=[d.description for d in score.positives][:MAX_LIST_ITEMS],
        risks=[d.description for d in score.risks][:MAX_LIST_ITEMS],
        source="fallback",
        warnings=warnings,
    )


def explain_meeting(
    exchanges: list[Exchange],
    analyses: list[ExchangeAnalysis],
    score: DealScore,
    percent: float,
    calibration_note: str = "",
    use_llm: bool = True,
) -> Explanation:
    warnings: list[str] = []
    if use_llm and exchanges:
        try:
            return _explain_with_llm(exchanges, analyses, score, percent, calibration_note)
        except Exception as error:
            logger.warning("LLM explanation failed: %s", error)
            warnings.append(
                f"The AI-written explanation was unavailable ({type(error).__name__}: {error}); "
                "this is the automatic summary instead."
            )
    return _fallback(exchanges, analyses, score, percent, calibration_note, warnings)
