from __future__ import annotations

import pickle

from workforce_validator.schedule_sources import SourceDetection, detect_schedule_sources


def _segment(day: str, start: str, end: str) -> dict[str, str]:
    return {
        "hourType": "WORK",
        "startDateTime": f"{day}T{start}:00",
        "endDateTime": f"{day}T{end}:00",
    }


def _fixture() -> dict:
    return {
        "store": {"id": 14947},
        "storeDayTimes": [
            {
                "operatingDate": "2026-08-03",
                "people": [
                    {
                        "personId": "E1",
                        "person": {"personId": "E1", "applicableWorkingHours": 8},
                        "dayTimes": {
                            "planned": [_segment("2026-08-03", "09:00", "17:00")],
                            "plannedDraft": [_segment("2026-08-03", "09:00", "12:00")],
                            "plannedDraftManuallyEdited": True,
                            "absences": [],
                        },
                    }
                ],
            }
        ],
    }


def test_source_detection_items_is_safe_during_empty_reconstruction():
    detection = SourceDetection()
    assert list(detection.items()) == []


def test_source_detection_survives_streamlit_style_cache_roundtrip():
    original = detect_schedule_sources(_fixture())
    restored = pickle.loads(pickle.dumps(original))

    available = [
        source
        for source, stats in restored.items()
        if stats["work_segments"] > 0
    ]

    assert available == ["planned", "plannedDraft"]
    assert restored["manual_edit"]["true_person_days"] == 1


def test_source_detection_can_be_iterated_repeatedly_when_state_changes():
    detection = detect_schedule_sources(_fixture())

    first_pass = dict(detection.items())
    second_pass = dict(detection.items())

    assert first_pass == second_pass
    assert first_pass["planned"]["work_segments"] == 1
    assert first_pass["plannedDraft"]["work_segments"] == 1
