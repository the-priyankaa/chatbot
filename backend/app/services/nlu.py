import re

GREETING_PATTERN = re.compile(
    r"\b(hi|hello|hey|good (morning|afternoon|evening)|yo|hola)\b", re.IGNORECASE
)
KB_PATTERN = re.compile(
    r"\b(info|knowledge|faq|document|source|reference)\b", re.IGNORECASE
)
ESCALATION_PATTERN = re.compile(
    r"\b(human|agent|support|person|representative|escalat)\b", re.IGNORECASE
)
FRUSTRATION_PATTERN = re.compile(
    r"\b(bad|terrible|awful|useless|stupid|wrong|angry|furious|hate|fed up|"
    r"unacceptable|disappointed)\b",
    re.IGNORECASE,
)

TOXIC_PATTERN = re.compile(
    r"\b(hate speech|kill you|i will kill|slur|nazi|dumbass|idiot)\b", re.IGNORECASE
)


def detect_intent(text: str) -> str:
    if ESCALATION_PATTERN.search(text):
        return "escalation"
    if GREETING_PATTERN.search(text):
        return "greeting"
    if KB_PATTERN.search(text):
        return "knowledge_query"
    return "general"


def detect_sentiment(text: str) -> str:
    if FRUSTRATION_PATTERN.search(text):
        return "negative"
    return "neutral"


def is_toxic(text: str) -> bool:
    return TOXIC_PATTERN.search(text) is not None
