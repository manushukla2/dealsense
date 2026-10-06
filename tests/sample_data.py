from src.schemas import Exchange, ExchangeAnalysis, Role, Sentiment, Turn


def _turn(role: Role, start: float, text: str) -> Turn:
    return Turn(
        speaker="SPEAKER_01" if role == Role.REP else "SPEAKER_00",
        role=role, start=start, end=start + 8, text=text,
    )


def sample_meeting() -> tuple[list[Exchange], list[ExchangeAnalysis]]:
    """A small four-exchange sales call with its (hand-written) analysis."""
    exchanges = [
        Exchange(index=0, turns=[
            _turn(Role.REP, 0, "Our platform plugs into the tools your team uses."),
            _turn(Role.CLIENT, 12, "Your pricing seems a bit high compared to what we use now.")]),
        Exchange(index=1, turns=[
            _turn(Role.REP, 60, "We can offer a three month pilot at a discount."),
            _turn(Role.CLIENT, 72, "That could work. Let me check with my CFO and get back to you early next week.")]),
        Exchange(index=2, turns=[
            _turn(Role.REP, 108, "Happy to compare us side by side with anyone else you are looking at."),
            _turn(Role.CLIENT, 120, "We are also talking to two other vendors, so we are still comparing options.")]),
        Exchange(index=3, turns=[
            _turn(Role.REP, 168, "Would a technical walkthrough help?"),
            _turn(Role.CLIENT, 180, "Okay, please send me the technical document. Does it integrate with our CRM?")]),
    ]
    analyses = [
        ExchangeAnalysis(
            exchange_index=0, score=-0.37, sentiment=Sentiment.NEGATIVE, intent="price_concern",
            signals=[
                'Pricing was discussed (CLIENT 00:12): "Your pricing seems a bit high compared to what we use now."',
                'Client objected to the price (CLIENT 00:12): "Your pricing seems a bit high compared to what we use now."',
                'A competitor or current tool was mentioned (CLIENT 00:12): "Your pricing seems a bit high compared to what we use now."',
            ],
            reasoning='Client said: "Your pricing seems a bit high compared to what we use now." This reads as worried about the price (about 40% confident), with a negative tone. Evidence: Pricing was discussed; Client objected to the price; A competitor or current tool was mentioned.'),
        ExchangeAnalysis(
            exchange_index=1, score=0.46, sentiment=Sentiment.POSITIVE, intent="interested",
            signals=[
                'Pricing was discussed (REP 01:00): "We can offer a three month pilot at a discount."',
                'Client showed positive interest (CLIENT 01:12): "That could work."',
                'Client is taking it to a decision-maker (CLIENT 01:12): "Let me check with my CFO and get back to you early next week."',
                'A timeline or deadline was mentioned (CLIENT 01:12): "Let me check with my CFO and get back to you early next week."',
            ],
            reasoning='Client said: "That could work. Let me check with my CFO and get back to you early next week." This reads as interested and wanting to learn more (about 38% confident), with a positive tone. Evidence: Pricing was discussed; Client showed positive interest; Client is taking it to a decision-maker; A timeline or deadline was mentioned.'),
        ExchangeAnalysis(
            exchange_index=2, score=-0.25, sentiment=Sentiment.NEUTRAL, intent="comparing",
            signals=[
                'A competitor or current tool was mentioned (CLIENT 02:00): "We are also talking to two other vendors, so we are still comparing options."',
            ],
            reasoning='Client said: "We are also talking to two other vendors, so we are still comparing options." This reads as comparing other options (about 52% confident), with a neutral tone. Evidence: A competitor or current tool was mentioned.'),
        ExchangeAnalysis(
            exchange_index=3, score=0.41, sentiment=Sentiment.NEUTRAL, intent="evaluating",
            signals=[
                'Client asked for a concrete next step (CLIENT 03:00): "Okay, please send me the technical document."',
                'Client is evaluating the product technically (CLIENT 03:00): "Does it integrate with our CRM?"',
                'Client asked a question (engaged) (CLIENT 03:00): "Does it integrate with our CRM?"',
            ],
            reasoning='Client said: "Okay, please send me the technical document. Does it integrate with our CRM?" This reads as evaluating how the product works (about 49% confident), with a neutral tone. Evidence: Client asked for a concrete next step; Client is evaluating the product technically; Client asked a question (engaged).'),
    ]
    return exchanges, analyses
