import json
import pytest
from workforce_validator.config import load_settings
from workforce_validator.schedule_sources import detect_schedule_sources
from workforce_validator.engine import run_validation


def seg(day,start,end):
    return {"hourType":"WORK","startDateTime":f"{day}T{start}:00","endDateTime":f"{day}T{end}:00"}

def fixture():
    return {"store":{"id":14947},"storeDayTimes":[{"operatingDate":"2026-08-03","people":[
        {"personId":"E1","person":{"personId":"E1","applicableWorkingHours":8},"dayTimes":{"planned":[seg("2026-08-03","09:00","17:00")],"plannedDraft":[seg("2026-08-03","09:00","12:00")],"plannedDraftManuallyEdited":True,"absences":[]}},
        {"personId":"E2","person":{"personId":"E2","applicableWorkingHours":6},"dayTimes":{"planned":[seg("2026-08-03","10:00","16:00")],"plannedDraft":[seg("2026-08-03","10:00","16:00")],"plannedDraftManuallyEdited":False,"absences":[]}}
    ]}]}

def test_sources_and_boolean_flag():
    stats=detect_schedule_sources(fixture())
    assert set(stats["sources"]) == {"planned","plannedDraft"}
    assert stats["manual_edit"]["true_person_days"] == 1

def test_manual_filters_isolate_draft_rows():
    assert [s.person_id for s in run_validation(fixture(),"plannedDraft","edited").shifts] == ["E1"]
    assert [s.person_id for s in run_validation(fixture(),"plannedDraft","not_edited").shifts] == ["E2"]

def test_manual_filter_is_ignored_for_published():
    result=run_validation(fixture(),"planned","edited")
    assert result.manual_edit_filter == "all" and {s.person_id for s in result.shifts} == {"E1","E2"}

def test_boolean_is_not_a_schedule_source():
    with pytest.raises(ValueError):
        run_validation(fixture(),"plannedDraftManuallyEdited")

def test_external_configuration_can_disable_rule(tmp_path):
    config={"calculation":{"max_internal_break_hours":1,"weekly_hours_tolerance":0.01},"rules":{
        "max_consecutive_days":{"enabled":True,"limit":5,"incident_type":"A"},
        "max_shift_hours":{"enabled":True,"limit":8,"incident_type":"B"},
        "min_shift_hours":{"enabled":False,"limit":4,"incident_type":"C"},
        "min_rest_hours":{"enabled":True,"limit":11,"incident_type":"D"}}}
    path=tmp_path/"rules.json"; path.write_text(json.dumps(config),encoding="utf-8")
    assert load_settings(path).min_shift_hours.enabled is False
