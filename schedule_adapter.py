from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

import validator_engine as legacy

MAX_CONSECUTIVE_DAYS = legacy.MAX_CONSECUTIVE_DAYS
MAX_SHIFT_HOURS = legacy.MAX_SHIFT_HOURS
MIN_REST_HOURS = legacy.MIN_REST_HOURS
MIN_SHIFT_HOURS = legacy.MIN_SHIFT_HOURS
load_json_bytes = legacy.load_json_bytes
result_dataframes = legacy.result_dataframes
build_excel_bytes = legacy.build_excel_bytes

SCHEDULE_SOURCES: dict[str, str] = {
    "planned": "Plan publicado",
    "plannedDraft": "Borrador del planificador",
}

MANUAL_EDIT_FILTERS: dict[str, str] = {
    "all": "Todos los borradores",
    "edited": "Solo borradores editados manualmente",
    "not_edited": "Solo borradores no editados manualmente",
}


def _is_work(segment: Any) -> bool:
    return isinstance(segment, dict) and str(segment.get("hourType", "")).upper() == "WORK"


def _matches(day_times: dict[str, Any], manual_filter: str) -> bool:
    flag = day_times.get("plannedDraftManuallyEdited")
    if manual_filter == "edited":
        return flag is True
    if manual_filter == "not_edited":
        return flag is False
    return True


def detect_schedule_sources(data: dict[str, Any]) -> dict[str, Any]:
    sources = {
        key: {
            "person_days": 0,
            "segments": 0,
            "work_segments": 0,
            "dates": set(),
        }
        for key in SCHEDULE_SOURCES
    }
    manual = {"true_person_days": 0, "false_person_days": 0, "missing_person_days": 0}

    for store_day in data.get("storeDayTimes") or []:
        if not isinstance(store_day, dict):
            continue
        operating_value = store_day.get("operatingDate")
        operating_day = date.fromisoformat(str(operating_value)[:10]) if operating_value else None
        for person_day in store_day.get("people") or []:
            if not isinstance(person_day, dict):
                continue
            day_times = person_day.get("dayTimes") or {}
            if not isinstance(day_times, dict):
                continue

            flag = day_times.get("plannedDraftManuallyEdited")
            if flag is True:
                manual["true_person_days"] += 1
            elif flag is False:
                manual["false_person_days"] += 1
            else:
                manual["missing_person_days"] += 1

            for source in SCHEDULE_SOURCES:
                segments = day_times.get(source)
                if not isinstance(segments, list) or not segments:
                    continue
                work_count = sum(_is_work(segment) for segment in segments)
                sources[source]["person_days"] += 1
                sources[source]["segments"] += len(segments)
                sources[source]["work_segments"] += work_count
                if operating_day and work_count:
                    sources[source]["dates"].add(operating_day)

    for stats in sources.values():
        dates = sorted(stats.pop("dates"))
        stats["date_count"] = len(dates)
        stats["first_date"] = dates[0] if dates else None
        stats["last_date"] = dates[-1] if dates else None

    return {"sources": sources, "manual_edit": manual}


def _filtered_copy(data: dict[str, Any], source: str, manual_filter: str) -> dict[str, Any]:
    filtered = deepcopy(data)
    if source != "plannedDraft" or manual_filter == "all":
        return filtered

    for store_day in filtered.get("storeDayTimes") or []:
        if not isinstance(store_day, dict):
            continue
        for person_day in store_day.get("people") or []:
            if not isinstance(person_day, dict):
                continue
            day_times = person_day.get("dayTimes") or {}
            if not isinstance(day_times, dict):
                continue
            if not _matches(day_times, manual_filter):
                day_times["plannedDraft"] = []
    return filtered


def run_validation(
    data: dict[str, Any],
    schedule_source: str = "plannedDraft",
    manual_edit_filter: str = "all",
):
    if schedule_source not in SCHEDULE_SOURCES:
        raise ValueError(f"Origen no valido: {schedule_source}")
    if manual_edit_filter not in MANUAL_EDIT_FILTERS:
        raise ValueError(f"Filtro manual no valido: {manual_edit_filter}")
    if schedule_source != "plannedDraft":
        manual_edit_filter = "all"

    filtered = _filtered_copy(data, schedule_source, manual_edit_filter)
    result = legacy.run_validation(filtered, schedule_source)
    result.manual_edit_filter = manual_edit_filter
    return result
