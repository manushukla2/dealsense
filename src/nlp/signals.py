import math
import re
from dataclasses import dataclass

from src.schemas import Exchange, Role, Turn, format_timestamp

NEGATION_WORDS = {
    "not", "no", "never", "don't", "doesn't", "didn't", "isn't", "aren't",
    "wasn't", "weren't", "can't", "cannot", "won't", "wouldn't", "couldn't", "hardly",
}
NEGATION_WINDOW = 3   # how many words before a match we check for "not", "don't", etc.


@dataclass(frozen=True)
class SignalRule:
    name: str
    label: str                  # plain-English description used in the reasoning
    weight: float               # -1 (very bad for the deal) to +1 (very good)
    speaker: str                # "client" = only client turns count, "any" = both sides
    patterns: tuple[str, ...]


@dataclass
class Signal:
    """One piece of evidence found in an exchange."""

    name: str
    label: str
    weight: float
    speaker: str      # e.g. "CLIENT"
    timestamp: str    # e.g. "04:12"
    quote: str        # the sentence the evidence came from

    @property
    def polarity(self) -> str:
        if self.weight > 0.05:
            return "positive"
        if self.weight < -0.05:
            return "negative"
        return "neutral"


RULES: list[SignalRule] = [
    # ---------------- positive ----------------
    SignalRule("strong_interest", "Client signalled strong buying intent", 0.7, "client", (
        r"\b(move|moving|go|going) (ahead|forward)\b",
        r"\bready to (start|sign|buy|go|proceed|move|get started)\b",
        r"\b(sign|signing) (the|a|up|off)\b",
        r"\b(send|share|draw up|prepare) (me |us )?(the |a |an )?(contract|agreement|order form|purchase order)\b",
        r"\blet'?s (do it|get started|start|proceed|sign)\b",
        r"\bwe'?d like to (start|sign|buy|purchase|get started|proceed|go with)\b",
        r"\bwe(?:'ll| will) (take it|go with (you|this|your))\b",
    )),
    SignalRule("mild_interest", "Client showed positive interest", 0.4, "client", (
        r"\b(sounds?|looks?|seems?) (really |very |pretty |quite )?(good|great|promising|interesting|reasonable|fair)\b",
        r"\bthat (could|can|should|would) work\b",
        r"\bthat works\b",
        r"\b(we are|we're|i am|i'm) (very |really )?interested\b",
        r"\bmakes sense\b",
        r"\b(love|like) (it|this|that|the idea)\b",
        r"\bimpress(ive|ed)\b",
    )),
    SignalRule("next_step_requested", "Client asked for a concrete next step", 0.5, "client", (
        r"\b(send|share|email|forward)( it| that| this)? (me|us|over)\b",
        r"\b(schedule|set up|book|arrange|plan) (a |another |the |our )?(demo|call|meeting|follow[- ]?up|session|workshop|walkthrough)\b",
        r"\b(next|follow[- ]?up) (call|meeting|demo|steps?)\b",
        r"\bwhat'?s the next step\b",
    )),
    SignalRule("decision_maker_involved", "Client is taking it to a decision-maker", 0.3, "client", (
        r"\b(check|talk|speak|run (it|this) by|loop in|confirm|discuss) (it |this )?(with|by) (my |our |the )?(cfo|ceo|cto|coo|cio|boss|manager|director|vp|vice president|team|board|procurement|legal|finance|leadership|stakeholders?|head of \w+)\b",
        r"\b(get|need|waiting for|pending) (his |her |their |the |our )?(approval|sign[- ]?off|go[- ]?ahead)\b",
        r"\bdecision[- ]?makers?\b",
        r"\bmy (cfo|ceo|cto|boss|manager|director)\b",
    )),
    SignalRule("timeline_stated", "A timeline or deadline was mentioned", 0.3, "client", (
        r"\b(early |late |mid[- ])?next (week|month|quarter)\b",
        r"\bthis (week|month|quarter)\b",
        r"\bby (the )?end of\b",
        r"\bby (monday|tuesday|wednesday|thursday|friday|tomorrow)\b",
        r"\bin (a |one |two |three |four |five |\d+) (days?|weeks?|months?)\b",
        r"\b(go|going) live\b",
        r"\bkick[- ]?off\b",
        r"\bdeadline\b",
    )),
    SignalRule("technical_evaluation", "Client is evaluating the product technically", 0.4, "client", (
        r"\b(integrat\w*|api|apis|sso|single sign[- ]on|soc ?2|gdpr|hipaa|encryption|security|compliance|implementation|onboarding|migrat\w*|webhooks?|sandbox|crm|erp)\b",
        r"\btechnical (document|doc|details|spec|specs|team|review|questions?)\b",
        r"\bdoes it (support|work with|integrate)\b",
        r"\bcan (you|it|we) (integrate|connect|support|sync|export|import)\b",
        r"\bhow (does|would|will) (it|this|that) (work|integrate|scale)\b",
    )),
    SignalRule("budget_confirmed", "Budget is available or approved", 0.5, "client", (
        r"\bwe have (the |a |our )?budget\b",
        r"\bbudget (is |has been |was )?(approved|allocated|set aside|available|secured)\b",
        r"\b(allocated|set aside|earmarked) (a |the )?budget\b",
        r"\bbudget for (this|it)\b",
    )),
    SignalRule("client_engaged", "Client asked a question (engaged)", 0.15, "client", (
        r"\?",
    )),
    SignalRule("pricing_discussion", "Pricing was discussed", 0.1, "any", (
        r"\b(price|prices|pricing|cost|costs|quote|discount|licen[sc]e|per (user|seat|month|year)|subscription|tiers?|rates?)\b",
    )),
    # ---------------- negative ----------------
    SignalRule("price_objection", "Client objected to the price", -0.4, "client", (
        r"\b(too|a bit|bit|quite|rather|really|pretty|very|kind of|a little) (high|expensive|steep|pricey|much)\b",
        r"\b(price|pricing|cost|costs) (seems|is|looks|feels|sounds|are)( a bit| quite| too| really| pretty| very| rather| a little)? (high|steep|expensive|much|off)\b",
        r"\b(out of|over) (our |the )?budget\b",
        r"\b(can'?t|cannot|can not) afford\b",
        r"\bbudget (is )?(tight|limited|constrained|frozen)\b",
        r"\bno budget\b",
        r"\bhigher than\b",
    )),
    SignalRule("competitor_mentioned", "A competitor or current tool was mentioned", -0.3, "client", (
        r"\bcompetitors?\b",
        r"\bother (vendors?|options|solutions|providers|companies|tools)\b",
        r"\banother (vendor|provider|solution|option|company|tool)\b",
        r"\balternatives?\b",
        r"\balso (talking|looking|speaking|evaluating|considering)\b",
        r"\b(comparing|shopping around)\b",
        r"\bcompared (to|with)\b",
        r"\bwhat we (use|have|are using)( now| today| currently)?\b",
        r"\bour current (vendor|provider|tool|solution|system|setup)\b",
        r"\balready (use|using|have|work with)\b",
    )),
    SignalRule("concern_raised", "Client voiced a concern or doubt", -0.3, "client", (
        r"\b(concern|concerned|concerns)\b",
        r"\bworr(y|ied|ies)\b",
        r"\bnot convinced\b",
        r"\b(hesitant|hesitation)\b",
        r"\b(risk|risky)\b",
        r"\b(unsure|doubt|doubts|skeptical|sceptical)\b",
        r"\b(problem|issue|issues) with\b",
        r"\bnot (comfortable|happy) with\b",
        r"\bnot sure (about|if|whether)\b",
    )),
    SignalRule("stalling", "Client is stalling or delaying", -0.45, "client", (
        r"\bnot (ready|certain|there yet)\b",
        r"\bnot at the moment\b",
        r"\bneed (some |more |a little |a bit of )?time\b",
        r"\b(think|thinking) (about|it over|this over|it through)\b",
        r"\bcircle back\b",
        r"\bmaybe (later|next (quarter|year|month))\b",
        r"\brevisit\b",
        r"\bon hold\b",
        r"\bnot a (top )?priority\b",
        r"\b(push|pushed|put) (this|it) (back|off)\b",
        r"\bpostpone\w*\b",
        r"\blater this year\b",
        r"\bnext year\b",
    )),
    SignalRule("rejection", "Client signalled they are not going ahead", -0.8, "client", (
        r"\bnot interested\b",
        r"\bno,? thanks?\b",
        r"\bnot (a )?(good )?fit\b",
        r"\bnot (going|gonna) to (work|happen)\b",
        r"\b(pass|passing) on\b",
        r"\bdecided (against|to go with (another|a different|someone|the other)|not to)\b",
        r"\b(went|going) with (another|a different|someone else|the other|a competitor)\b",
        r"\bnot (moving|going) forward\b",
        r"\b(cancel|cancelling|canceling|terminate)\b",
        r"\bno longer (interested|need|needed|looking)\b",
        r"\bwe(?:'ll| will) pass\b",
        r"\bwon'?t (work|be (a )?fit)\b",
    )),
]

COMPILED = {rule.name: [re.compile(p, re.IGNORECASE) for p in rule.patterns] for rule in RULES}

# If the key signal is present, the signals it dominates are dropped (they would contradict it).
DOMINATES: dict[str, set[str]] = {
    "strong_interest": {"mild_interest"},
    "rejection": {"stalling", "timeline_stated", "mild_interest"},
    "stalling": {"timeline_stated"},
}


def _normalize(text: str) -> str:
    """Straighten curly quotes. Same length as the original, so positions still line up."""
    return (
        text.replace("\u2019", "'").replace("\u2018", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
    )


def _is_negated(text: str, position: int) -> bool:
    """True if one of the 3 words before position (in the same sentence) is a negation."""
    sentence_start = re.split(r"[.!?]", text[:position])[-1]
    words = re.findall(r"[a-z']+", sentence_start.lower())[-NEGATION_WINDOW:]
    return any(word in NEGATION_WORDS for word in words)


def _sentence_around(text: str, position: int) -> str:
    begin = max(text.rfind(mark, 0, position) for mark in ".!?") + 1
    ends = [i for i in (text.find(mark, position) for mark in ".!?") if i != -1]
    end = min(ends) + 1 if ends else len(text)
    return text[begin:end].strip()


def _signals_in_turn(turn: Turn) -> list[Signal]:
    text = _normalize(turn.text)
    found: list[Signal] = []
    for rule in RULES:
        if rule.speaker == "client" and turn.role == Role.REP:
            continue
        for pattern in COMPILED[rule.name]:
            match = next(
                (m for m in pattern.finditer(text)
                 if not (rule.weight > 0 and _is_negated(text, m.start()))),
                None,
            )
            if match:
                found.append(Signal(
                    name=rule.name,
                    label=rule.label,
                    weight=rule.weight,
                    speaker=turn.label,
                    timestamp=turn.timestamp,
                    quote=_sentence_around(text, match.start()),
                ))
                break
    return found


def extract_signals(exchange: Exchange) -> list[Signal]:
    """All deal signals in one exchange, each signal type counted at most once."""
    signals: list[Signal] = []
    seen: set[str] = set()
    for turn in exchange.turns:
        for signal in _signals_in_turn(turn):
            if signal.name not in seen:
                seen.add(signal.name)
                signals.append(signal)

    dropped: set[str] = set()
    for name in seen:
        dropped |= DOMINATES.get(name, set())
    return [s for s in signals if s.name not in dropped]


def net_signal_score(signals: list[Signal]) -> float:
    """Squash the total of all weights into the range -1 to +1."""
    return round(math.tanh(sum(s.weight for s in signals)), 2)


def describe_signals(signals: list[Signal]) -> str:
    if not signals:
        return "(no signals)"
    return "\n".join(
        f"{s.weight:+.2f}  {s.label}  <- {s.speaker} {s.timestamp}: \"{s.quote}\""
        for s in signals
    )
