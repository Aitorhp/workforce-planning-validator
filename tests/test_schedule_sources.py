import pytest

from schedule_adapter import detect_schedule_sources, run_validation


def seg(day, start, end):
    return {
        "hourType": "WORK",
        "startDateTime": f"{day}T{start}:00",
        "endDateTime": f"{day}T{end}:00",
    }


def data_fixture():
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
                            "planned": [seg("2026-08-03", "09:00", "17:00")],
                            "plannedDraft": [seg("2026-08-03", "09:00", "12:00")],
                            "plannedDraftManuallyEdited": True,
                            "absences": [],
                        },
                    },
                    {
                        "personId": "E2",
                        "person": {"personId": "E2", "applicableWorkingHours": 6},
                        "dayTimes": {
                            "planned": [seg("2026-08-03", "10:00", "16:00")],
                            "plannedDraft": [seg("2026-08-03", "10:00", "16:00")],
                            "plannedDraftManuallyEdited": False,
                            "absences": [],
                        },
                    },
                ],
            }
        ],
    }


def test_detects_two_real_sources_and_boolean_flag():
    stats = detect_schedule_sources(data_fixture())
    assert set(stats["sources"]) == {"planned", "plannedDraft"}
    assert stats["sources"]["planned"]["work_segments"] == 2
    assert stats["sources"]["plannedDraft"]["work_segments"] == 2
    assert stats["manual_edit"]["true_person_days"] == 1
    assert stats["manual_edit"]["false_person_days"] == 1


def test_manual_filter_is_applied_to_planned_draft():
    data = data_fixture()
    all_result = run_validation(data, "plannedDraft", "all")
    edited_result = run_validation(data, "plannedDraft", "edited")
    not_edited_result = run_validation(data, "plannedDraft", "not_edited")

    assert {shift.person_id for shift in all_result.shifts} == {"E1", "E2"}
    assert [shift.person_id for shift in edited_result.shifts] == ["E1"]
    assert [shift.person_id for shift in not_edited_result.shifts] == ["E2"]


def test_manual_filter_is_ignored_for_published_plan():
    result = run_validation(data_fixture(), "planned", "edited")
    assert result.manual_edit_filter == "all"
    assert {shift.person_id for shift in result.shifts} == {"E1", "E2"}


def test_boolean_is_never_treated_as_schedule_segments():
    with pytest.raises(ValueError):
        run_validation(data_fixture(), "plannedDraftManuallyEdited")
