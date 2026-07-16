from validator_engine import detect_schedule_sources, run_validation


def seg(day, start, end):
    return {"hourType":"WORK", "startDateTime":f"{day}T{start}:00", "endDateTime":f"{day}T{end}:00"}


def data_fixture():
    return {
        "store":{"id":14947},
        "storeDayTimes":[{
            "operatingDate":"2026-08-03",
            "people":[{
                "personId":"E1",
                "person":{"personId":"E1", "applicableWorkingHours":8},
                "dayTimes":{
                    "planned":[seg("2026-08-03","09:00","17:00")],
                    "plannedDraft":[seg("2026-08-03","09:00","12:00")],
                    "plannedDraftManuallyEdited":[seg("2026-08-03","09:00","15:00")],
                    "absences":[],
                },
            }],
        }],
    }


def test_detects_all_sources():
    stats = detect_schedule_sources(data_fixture())
    assert stats["planned"]["work_segments"] == 1
    assert stats["plannedDraft"]["work_segments"] == 1
    assert stats["plannedDraftManuallyEdited"]["work_segments"] == 1


def test_sources_are_isolated():
    data = data_fixture()
    assert run_validation(data, "planned").shifts[0].worked_hours == 8
    assert run_validation(data, "plannedDraft").shifts[0].worked_hours == 3
    assert run_validation(data, "plannedDraftManuallyEdited").shifts[0].worked_hours == 6


def test_invalid_source_fails():
    try:
        run_validation(data_fixture(), "other")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
