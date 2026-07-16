from collections import defaultdict
from workforce_validator.config import ValidatorSettings
from workforce_validator.dates import find_consecutive_streaks, month_key
from workforce_validator.models import Incident, ShiftRow
from workforce_validator.rules.base import number_text

def validate(shifts: list[ShiftRow], settings: ValidatorSettings) -> list[Incident]:
    rule = settings.max_consecutive_days
    if not rule.enabled:
        return []
    by_employee = defaultdict(list)
    for shift in shifts:
        by_employee[(shift.store_id, shift.person_id)].append(shift)
    incidents = []
    for (store_id, person_id), person_shifts in by_employee.items():
        for streak in find_consecutive_streaks([shift.work_day for shift in person_shifts]):
            if len(streak) <= rule.limit:
                continue
            for month in sorted({month_key(day) for day in streak}):
                incidents.append(Incident(store_id, person_id, month, rule.incident_type, streak[0], streak[-1], float(len(streak)), f"<= {number_text(rule.limit)} dias", f"{streak[0]:%d/%m/%Y}-{streak[-1]:%d/%m/%Y}: {len(streak)} dias consecutivos"))
    return incidents
