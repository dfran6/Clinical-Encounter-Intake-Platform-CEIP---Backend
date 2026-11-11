import re
from dataclasses import dataclass

import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Span

from src.extraction.negation import is_negated
from src.extraction.vocab import DIAGNOSIS_TERMS, MEDICATION_NAMES


_nlp = spacy.blank("en")
_nlp.add_pipe("sentencizer")
_phrase_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_phrase_matcher.add(
    "DIAGNOSIS",
    [_nlp.make_doc(term) for term in DIAGNOSIS_TERMS],
)
_phrase_matcher.add(
    "MEDICATION",
    [_nlp.make_doc(name) for name in MEDICATION_NAMES],
)

_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|units?)\b", re.IGNORECASE)
_FREQUENCY = re.compile(
    r"\b(?:once|twice|three times|four times)\s+(?:a\s+)?daily\b"
    r"|\b(?:daily|weekly|nightly|bid|tid|qid)\b"
    r"|\bevery\s+\d+\s*(?:hours?|hrs?)\b",
    re.IGNORECASE,
)
_BLOOD_PRESSURE = re.compile(
    r"\b(?:bp|blood pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})\b",
    re.IGNORECASE,
)
_HEART_RATE = re.compile(r"\b(?:hr|heart rate|pulse)\s*[:=]?\s*(\d{2,3})\b", re.IGNORECASE)


@dataclass(frozen=True)
class _Match:
    label: str
    span: Span
    canonical: str


def _find_matches(doc) -> list[_Match]:
    candidates: list[_Match] = []
    for match_id, start, end in _phrase_matcher(doc):
        label = doc.vocab.strings[match_id]
        span = doc[start:end]
        canonical = span.text.casefold()
        if label == "DIAGNOSIS":
            # Keep the term that actually matched. Substring-based selection
            # can silently turn "hypertension" into "essential hypertension".
            canonical = next(
                (term for term in DIAGNOSIS_TERMS if term.casefold() == canonical),
                canonical,
            )
        elif label == "MEDICATION":
            canonical = max(
                (name for name in MEDICATION_NAMES if name.casefold() == canonical),
                key=len,
                default=canonical,
            )
        candidates.append(_Match(label, span, canonical))

    selected: list[_Match] = []
    for label in ("DIAGNOSIS", "MEDICATION"):
        group = sorted(
            (match for match in candidates if match.label == label),
            key=lambda match: (match.span.start, -(match.span.end - match.span.start)),
        )
        accepted: list[_Match] = []
        for match in group:
            if any(match.span.start < prior.span.end and prior.span.start < match.span.end for prior in accepted):
                continue
            accepted.append(match)
        selected.extend(accepted)
    return sorted(selected, key=lambda match: match.span.start)


def _match_is_negated(match: _Match) -> bool:
    sentence = match.span.sent
    prefix = sentence.text[: match.span.start_char - sentence.start_char]
    return is_negated(prefix)


def _medication_details(match: _Match) -> dict[str, str | None]:
    sentence = match.span.sent.text
    after_start = match.span.end_char - match.span.sent.start_char
    following_text = sentence[after_start : after_start + 48]
    # Do not parse a dose or frequency from a later clause/sentence.
    # Keep decimal points inside doses such as 2.5 mg; only split on a period
    # that is not between digits.
    following_text = re.split(r"[,;!?\n]|\.(?!\d)", following_text, maxsplit=1)[0]
    dose_match = _DOSE.search(following_text)
    frequency_match = _FREQUENCY.search(following_text)
    return {
        "name": match.canonical,
        "dose": re.sub(r"\s+", "", dose_match.group(0)).casefold() if dose_match else None,
        "frequency": frequency_match.group(0).lower() if frequency_match else None,
    }


def _extract_vitals(text: str) -> dict[str, int]:
    vitals: dict[str, int] = {}
    bp_match = _BLOOD_PRESSURE.search(text)
    if bp_match:
        systolic, diastolic = (int(value) for value in bp_match.groups())
        if 40 <= systolic <= 300 and 20 <= diastolic <= 200:
            vitals["bp_systolic"] = systolic
            vitals["bp_diastolic"] = diastolic

    hr_match = _HEART_RATE.search(text)
    if hr_match:
        heart_rate = int(hr_match.group(1))
        if 20 <= heart_rate <= 300:
            vitals["heart_rate"] = heart_rate
    return vitals


def extract(text: str) -> dict:
    """Extract vocabulary matches, negations, labeled vitals, and medication details."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    doc = _nlp(text)
    diagnoses: list[dict[str, str]] = []
    medications: list[dict[str, str | None]] = []
    negated: list[str] = []
    seen_diagnoses: set[str] = set()
    seen_medications: set[tuple[str, str | None, str | None]] = set()
    seen_negated: set[str] = set()

    for match in _find_matches(doc):
        if match.label == "DIAGNOSIS":
            canonical = match.canonical
            if _match_is_negated(match):
                if canonical not in seen_negated:
                    negated.append(canonical)
                    seen_negated.add(canonical)
                continue
            if canonical not in seen_diagnoses:
                diagnoses.append({"term": canonical, "code": DIAGNOSIS_TERMS[canonical]})
                seen_diagnoses.add(canonical)
        else:
            medication = _medication_details(match)
            identity = (medication["name"], medication["dose"], medication["frequency"])
            if identity not in seen_medications:
                medications.append(medication)
                seen_medications.add(identity)

    return {
        "diagnoses": diagnoses,
        "medications": medications,
        "vitals": _extract_vitals(text),
        "negated": negated,
    }
