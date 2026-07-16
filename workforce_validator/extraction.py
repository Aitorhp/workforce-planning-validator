from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import month_key
from workforce_validator.io import parse_iso_datetime
from workforce_validator.models import AbsenceDay, ShiftRow
from workforce_validator.schedule_sources import validate_schedule_source


def extract_data(data: dict[str, Any], schedule_source: str, settings: ValidatorSettings = SETTINGS):
    schedule_source = validate_schedule_source(schedule_source)
    store_id = (data.get("store") or {}).get("id")
    store_day_times = data.get("storeDayTimes") or []
    if not isinstance(store_day_times, list):
        raise ValueError("El campo 'storeDayTimes' debe ser una lista.")
    shifts = []
    employee_months = {}
    absences = []
    employee_presence_dates = defaultdict(set)
    max_internal_break = timedelta(hours=settings.calculation.max_internal_break_hours)
    for store_day in store_day_times:
        if not isinstance(store_day, dict) or not store_day.get("operatingDate"):
            continue
        operating_day = date.fromisoformat(str(store_day["operatingDate"])[:10])
        for person_day in store_day.get("people") or []:
            if not isinstance(person_day, dict):
                continue
            person = person_day.get("person") or {}
            person_id = person_day.get("personId", person.get("personId"))
            applicable_hours = person.get("applicableWorkingHours")
            employee_presence_dates[(store_id, person_id)].add(operating_day)
            employee_months[(store_id, person_id, month_key(operating_day))] = applicable_hours
            day_times = person_day.get("dayTimes") or {}
            selected_schedule = day_times.get(schedule_source) or []
            if not isinstance(selected_schedule, list):
                selected_schedule = []
            seen_absences = set()
            for absence in day_times.get("absences") or []:
                if not isinstance(absence, dict):
                    continue
                status = str(absence.get("status") or "").upper()
                if status not in {"VALIDATED", "APPROVED"}:
                    continue
                type_data = absence.get("type") or {}
                absence_type = str(type_data.get("name") or type_data.get("description") or absence.get("id") or "AUSENCIA")
                key = (absence_type, status)
                if key in seen_absences:
                    continue
                seen_absences.add(key)
                absences.append(AbsenceDay(store_id, person_id, operating_day, absence_type, status))
            segments = []
            for segment in selected_schedule:
                if not isinstance(segment, dict) or str(segment.get("hourType", "")).upper() != "WORK":
                    continue
                start_value = segment.get("startDateTime")
                end_value = segment.get("endDateTime")
                if not start_value or not end_value:
                    continue
                start_dt = parse_iso_datetime(start_value)
                end_dt = parse_iso_datetime(end_value)
                if end_dt <= start_dt:
                    raise ValueError(f"Segmento invalido en {schedule_source}: personId={person_id}, inicio={start_value}, fin={end_value}")
                segments.append((start_dt, end_dt))
            if not segments:
                continue
            segments.sort(key=lambda item: item[0])
            shift_start = segments[0][0]
            shift_end = max(end for _, end in segments)
            net_work = sum((end - start for start, end in segments), timedelta())
            break_duration = timedelta()
            previous_end = segments[0][1]
            for current_start, current_end in segments[1:]:
                gap = current_start - previous_end
                if timedelta(0) < gap <= max_internal_break:
                    break_duration += gap
                if current_end > previous_end:
                    previous_end = current_end
            shifts.append(ShiftRow(store_id, person_id, applicable_hours, operating_day, shift_start, shift_end, round(net_work.total_seconds() / 3600, 4), round(break_duration.total_seconds() / 3600, 4)))
    shifts.sort(key=lambda row: (str(row.store_id), str(row.person_id), row.work_day))
    absences.sort(key=lambda row: (str(row.store_id), str(row.person_id), row.absence_day))
    return shifts, employee_months, absences, employee_presence_dates
