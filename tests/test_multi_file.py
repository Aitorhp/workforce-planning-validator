from __future__ import annotations

import pytest

from workforce_validator.multi_file import combine_planning_documents


def planning(store_id, dates):
    return {
        "store": {"id": store_id},
        "storeDayTimes": [
            {"operatingDate": day, "people": []}
            for day in dates
        ],
    }


def test_single_document_is_supported():
    source = planning(14947, ["2026-08-01", "2026-08-02"])

    combined = combine_planning_documents([source])

    assert combined["store"]["id"] == 14947
    assert [item["operatingDate"] for item in combined["storeDayTimes"]] == [
        "2026-08-01",
        "2026-08-02",
    ]
    assert combined is not source


def test_two_consecutive_months_are_combined_chronologically():
    september = planning(14947, ["2026-09-02", "2026-09-01"])
    august = planning(14947, ["2026-08-31", "2026-08-30"])

    combined = combine_planning_documents([september, august])

    assert [item["operatingDate"] for item in combined["storeDayTimes"]] == [
        "2026-08-30",
        "2026-08-31",
        "2026-09-01",
        "2026-09-02",
    ]


def test_different_stores_are_rejected():
    august = planning(14947, ["2026-08-31"])
    september = planning(99999, ["2026-09-01"])

    with pytest.raises(ValueError, match="tiendas distintas"):
        combine_planning_documents([august, september])


def test_overlapping_dates_are_rejected():
    first = planning(14947, ["2026-08-31"])
    second = planning(14947, ["2026-08-31"])

    with pytest.raises(ValueError, match="solapan"):
        combine_planning_documents([first, second])


def test_non_consecutive_months_are_rejected():
    august = planning(14947, ["2026-08-31"])
    october = planning(14947, ["2026-10-01"])

    with pytest.raises(ValueError, match="meses consecutivos"):
        combine_planning_documents([august, october])


def test_each_file_must_contain_a_single_calendar_month():
    mixed = planning(14947, ["2026-08-31", "2026-09-01"])

    with pytest.raises(ValueError, match="único mes calendario"):
        combine_planning_documents([mixed])
