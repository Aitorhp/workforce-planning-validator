from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.models import Incident, ShiftRow
from workforce_validator.rules import max_consecutive_days, max_shift_duration, min_rest_between_shifts, min_shift_duration

RULES = (max_shift_duration.validate, min_shift_duration.validate, min_rest_between_shifts.validate, max_consecutive_days.validate)

def run_rules(shifts: list[ShiftRow], settings: ValidatorSettings = SETTINGS) -> list[Incident]:
    incidents = []
    for rule in RULES:
        incidents.extend(rule(shifts, settings))
    incidents.sort(key=lambda item: (str(item.store_id), str(item.person_id), item.month, item.start_date, item.incident_type))
    return incidents
