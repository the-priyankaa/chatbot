from .nlu import is_toxic

MODERATION_BLOCK_MESSAGE = (
    "I can't help with that request. If you're experiencing difficulty, "
    "please rephrase your question or contact support."
)

MIN_INPUT_LENGTH = 1
MAX_INPUT_LENGTH = 4000


def moderate_input(text: str) -> str | None:
    """Returns an error message if the input should be blocked, else None."""
    if len(text) > MAX_INPUT_LENGTH:
        return "Message is too long."
    if is_toxic(text):
        return MODERATION_BLOCK_MESSAGE
    return None


def moderate_output(text: str) -> str:
    """Lightweight guard on model output. Full LLM review is skipped to save
    latency/cost; this filters the most obvious policy violations."""
    if is_toxic(text):
        return MODERATION_BLOCK_MESSAGE
    return text
