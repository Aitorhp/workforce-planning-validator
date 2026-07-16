from collections import defaultdict
from workforce_validator.config import ValidatorSettings
from workforce_validator.dates import month_key
from workforce_validator.models import Incident, ShiftRow
from workforce_validator.rules.base import number_text

def validate(shifts: list[ShiftRow], settings: ValidatorSettings) -> list[Incident]:
    rule = settings.min_rest_hours
    if not rule.enabled:
        return []
    by_employee = defaultdict(list)
    for shift in shifts:
        by_employee[(shift.store_id, shift.person_id)].append(shift)
    incidents = []
    for (store_id, person_id), person_shifts in by_employee.items():
        person_shifts.sort(key=lambda row: (row.shift_start, row.shift_end))
        for previous, current in zip(person_shifts, person_shifts[1:]):
            rest = (current.shift_start - previous.shift_end).total_seconds() / 3600
            if rest >= rule.limit:
                continue
            incidents.append(Incident(store_id, person_id, month_key(current.work_day), rule.incident_type, previous.work_day, current.work_day, round(rest, 4), f">= {number_text(rule.limit)} horas", f"{previous.work_day:%d/%m/%Y} {previous.shift_end:%H:%M} -> {current.work_day:%d/%m/%Y} {current.shift_start:%H:%M}: {rest:.2f} h"))
    return incidents
