import re


NEGATION_CUE_PATTERN = re.compile(
    r"(?:\b(?:denies|deny|denied|no|without|never)\b"
    r"|\bnegative\s+for\b"
    r"|\babsence\s+of\b"
    r"|\bfree\s+of\b"
    r"|\bno\s+(?:evidence|signs?|symptoms?)\s+of\b"
    r"|\bnot\b(?!\s+only\b)"
    r"|\b(?:isn't|wasn't|doesn't|don't|didn't|hasn't|haven't|hadn't|can't)\b)"
    r"(?:\s+\w+){0,5}\s*$",
    re.IGNORECASE,
)


def is_negated(sentence_prefix: str) -> bool:
    """Return true for a nearby negation cue in the current clause."""
    clause_prefix = re.split(
        r"[,;:]|\b(?:but|however|although|except)\b",
        sentence_prefix,
        flags=re.IGNORECASE,
    )[-1]
    return bool(NEGATION_CUE_PATTERN.search(clause_prefix))
