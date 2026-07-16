from workforce_validator.config import ValidatorSettings
from workforce_validator.dates import month_key
from workforce_validator.models import Incident, ShiftRow
from workforce_validator.rules.base import number_text

def validate(shifts: list[ShiftRow], settings: ValidatorSettings) -> list[Incident]:
    rule = settings.max_shift_hours
    if not rule.enabled:
        return []
    incidents = []
    for shift in shifts:
        if shift.worked_hours <= rule.limit:
            continue
        incidents.append(Incident(shift.store_id, shift.person_id, month_key(shift.work_day), rule.incident_type, shift.work_day, shift.work_day, shift.worked_hours, f"<= {number_text(rule.limit)} horas", f"{shift.work_day:%d/%m/%Y}: {shift.worked_hours:.2f} h ({shift.shift_start:%H:%M}-{shift.shift_end:%H:%M})"))
    return incidents
