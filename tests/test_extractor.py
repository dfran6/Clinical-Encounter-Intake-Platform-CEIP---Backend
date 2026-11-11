import pytest

from src.extraction.extractor import extract


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        (
            "Patient presents with hypertension and type 2 diabetes. Denies chest pain. Started lisinopril 10mg daily. BP 150/95, HR 88.",
            {
                "diagnoses": [
                    {"term": "hypertension", "code": "38341003"},
                    {"term": "type 2 diabetes", "code": "44054006"},
                ],
                "medications": [{"name": "lisinopril", "dose": "10mg", "frequency": "daily"}],
                "vitals": {"bp_systolic": 150, "bp_diastolic": 95, "heart_rate": 88},
                "negated": ["chest pain"],
            },
        ),
        (
            "HYPERTENSION noted.",
            {"diagnoses": [{"term": "hypertension", "code": "38341003"}], "medications": [], "vitals": {}, "negated": []},
        ),
        (
            "Type II diabetes is stable.",
            {"diagnoses": [{"term": "type ii diabetes", "code": "44054006"}], "medications": [], "vitals": {}, "negated": []},
        ),
        (
            "High blood pressure on problem list.",
            {"diagnoses": [{"term": "high blood pressure", "code": "38341003"}], "medications": [], "vitals": {}, "negated": []},
        ),
        (
            "Patient denies chest pain.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["chest pain"]},
        ),
        (
            "No history of chest pain today.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["chest pain"]},
        ),
        (
            "Without high blood pressure symptoms.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["high blood pressure"]},
        ),
        (
            "No chest pain. Hypertension is treated.",
            {"diagnoses": [{"term": "hypertension", "code": "38341003"}], "medications": [], "vitals": {}, "negated": ["chest pain"]},
        ),
        (
            "Started lisinopril 10 mg daily.",
            {"diagnoses": [], "medications": [{"name": "lisinopril", "dose": "10mg", "frequency": "daily"}], "vitals": {}, "negated": []},
        ),
        (
            "Started lisinopril 2.5 MG once daily.",
            {"diagnoses": [], "medications": [{"name": "lisinopril", "dose": "2.5mg", "frequency": "once daily"}], "vitals": {}, "negated": []},
        ),
        (
            "No evidence of essential hypertension.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["essential hypertension"]},
        ),
        (
            "Denies any type 2 diabetes mellitus.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["type 2 diabetes mellitus"]},
        ),
        (
            "Taking metformin 500mg twice daily.",
            {"diagnoses": [], "medications": [{"name": "metformin", "dose": "500mg", "frequency": "twice daily"}], "vitals": {}, "negated": []},
        ),
        (
            "Atorvastatin 20 mg nightly.",
            {"diagnoses": [], "medications": [{"name": "atorvastatin", "dose": "20mg", "frequency": "nightly"}], "vitals": {}, "negated": []},
        ),
        (
            "Medication: amlodipine every 8 hours.",
            {"diagnoses": [], "medications": [{"name": "amlodipine", "dose": None, "frequency": "every 8 hours"}], "vitals": {}, "negated": []},
        ),
        (
            "Lisinopril and metformin continued.",
            {
                "diagnoses": [],
                "medications": [
                    {"name": "lisinopril", "dose": None, "frequency": None},
                    {"name": "metformin", "dose": None, "frequency": None},
                ],
                "vitals": {},
                "negated": [],
            },
        ),
        (
            "Blood pressure: 120/80; heart rate 72.",
            {"diagnoses": [], "medications": [], "vitals": {"bp_systolic": 120, "bp_diastolic": 80, "heart_rate": 72}, "negated": []},
        ),
        (
            "BP=110/70, pulse: 65.",
            {"diagnoses": [], "medications": [], "vitals": {"bp_systolic": 110, "bp_diastolic": 70, "heart_rate": 65}, "negated": []},
        ),
        (
            "BP 999/999 HR 999; 130/85.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": []},
        ),
        (
            "Routine follow-up; no new concerns.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": []},
        ),
        (
            "Hypertension, hypertension; lisinopril 5mg daily and lisinopril 5mg daily.",
            {
                "diagnoses": [{"term": "hypertension", "code": "38341003"}],
                "medications": [{"name": "lisinopril", "dose": "5mg", "frequency": "daily"}],
                "vitals": {},
                "negated": [],
            },
        ),
        (
            "Negative for chest pain and denies type 2 diabetes.",
            {"diagnoses": [], "medications": [], "vitals": {}, "negated": ["chest pain", "type 2 diabetes"]},
        ),
        (
            "No hypertension, but chest pain is present.",
            {"diagnoses": [{"term": "chest pain", "code": "29857009"}], "medications": [], "vitals": {}, "negated": ["hypertension"]},
        ),
    ],
)
def test_extract_returns_expected_structured_fields(note, expected):
    assert extract(note) == expected


def test_extract_rejects_non_string_input():
    with pytest.raises(TypeError, match="text must be a string"):
        extract(None)
