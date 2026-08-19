from datetime import date

import pytest

from workforce_validator.adapters import BundleAdapter, CurrentJsonAdapter
from workforce_validator.engine import run_canonical_validation, run_validation
from workforce_validator.input_sources import (
    combine_planning_inputs,
    detect_input_schedule_sources,
    is_bundle_data,
    run_input_validation,
)


def seg(day, start, end):
    return {
        "hourType": "WORK",
        "startDateTime": f"{day}T{start}:00+01:00",
        "endDateTime": f"{day}T{end}:00+01:00",
    }


def legacy_data():
    return {
        "store": {"id": 3394},
        "storeDayTimes": [
            {
                "operatingDate": "2026-09-14",
                "people": [
                    {
                        "personId": 785,
                        "person": {"personId": 785, "applicableWorkingHours": 37.5},
                        "dayTimes": {
                            "planned": [seg("2026-09-14", "09:00", "17:30")],
                            "plannedDraft": [
                                seg("2026-09-14", "09:00", "13:00"),
                                seg("2026-09-14", "14:00", "17:30"),
                            ],
                            "plannedDraftManuallyEdited": False,
                            "absences": [],
                        },
                    }
                ],
            },
            {
                "operatingDate": "2026-09-15",
                "people": [
                    {
                        "personId": 785,
                        "person": {"personId": 785, "applicableWorkingHours": 37.5},
                        "dayTimes": {
                            "planned": [],
                            "plannedDraft": [],
                            "plannedDraftManuallyEdited": False,
                            "absences": [
                                {
                                    "status": "VALIDATED",
                                    "type": {"name": "Holidays"},
                                }
                            ],
                        },
                    }
                ],
            },
        ],
    }


def bundle_data():
    legacy = legacy_data()
    bundle_days = []
    for day in legacy["storeDayTimes"]:
        bundle_days.append(
            {
                "operatingDate": day["operatingDate"],
                "people": [
                    {
                        "personId": item["personId"],
                        "dayTimes": item["dayTimes"],
                    }
                    for item in day["people"]
                ],
            }
        )
    return {
        "_metadata": {
            "storeId": 3394,
            "startDate": "2026-09-14",
            "endDate": "2026-09-15",
        },
        "config": {"store": {"id": 3394}},
        "people": {
            "data": [
                {
                    "personId": 785,
                    "employmentPeriods": [
                        {
                            "applicableWorkingHours": 37.5,
                            "validFromDate": "2026-09-14",
                            "validToDate": "2026-09-15",
                        }
                    ],
                }
            ]
        },
        "times": {"storeDayTimes": bundle_days},
    }


@pytest.mark.parametrize("source", ["planned", "plannedDraft"])
def test_bundle_matches_current_json_canonical_contract(source):
    current = CurrentJsonAdapter(legacy_data()).build_canonical_dataset(source)
    bundle = BundleAdapter(bundle_data()).build_canonical_dataset(source)
    assert bundle == current


@pytest.mark.parametrize("source", ["planned", "plannedDraft"])
def test_canonical_route_matches_current_engine(source):
    reference = run_validation(legacy_data(), source)
    canonical = CurrentJsonAdapter(legacy_data()).build_canonical_dataset(source)
    candidate = run_canonical_validation(canonical, source_data=reference.source_data)
    assert candidate.shifts == reference.shifts
    assert candidate.absences == reference.absences
    assert candidate.employee_months == reference.employee_months
    assert candidate.employee_presence_dates == reference.employee_presence_dates
    assert candidate.data_dates == reference.data_dates
    assert candidate.incidents == reference.incidents
    assert candidate.summaries == reference.summaries
    assert candidate.weekly_rows == reference.weekly_rows


def test_bundle_is_supported_as_single_consolidated_input():
    bundle = bundle_data()
    assert is_bundle_data(bundle)
    assert combine_planning_inputs([bundle]) is bundle
    sources = detect_input_schedule_sources(bundle)
    assert sources["planned"]["work_segments"] == 1
    assert sources["plannedDraft"]["work_segments"] == 2
    result = run_input_validation(bundle, "plannedDraft")
    assert result.data_dates == {date(2026, 9, 14), date(2026, 9, 15)}
    assert result.source_data["store"]["id"] == 3394
    assert len(result.shifts) == 1
    assert result.shifts[0].worked_hours == 7.5
    assert result.shifts[0].break_hours == 1.0


def test_bundle_cannot_be_mixed_with_legacy_documents():
    with pytest.raises(ValueError, match="unico fichero"):
        combine_planning_inputs([bundle_data(), legacy_data()])
