from __future__ import annotations

from collections import defaultdict
from typing import Any

from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import find_consecutive_streaks, month_key, weekend_counts
from workforce_validator.models import Incident, ShiftRow
from workforce_validator.rules.registry import run_rules


def build_monthly_summaries(shifts: list[ShiftRow], employee_months: dict[tuple[Any, Any, str], Any], incidents: list[Incident], settings: ValidatorSettings = SETTINGS) -> list[dict[str, Any]]:
    by_employee = defaultdict(list)
    for shift in shifts:
        by_employee[(shift.store_id, shift.person_id)].append(shift)
    groups = defaultdict(list)
    for incident in incidents:
        groups[(incident.store_id, incident.person_id, incident.month, incident.incident_type)].append(incident)
    summaries = []
    for (store_id, person_id, month), applicable in sorted(employee_months.items(), key=lambda item: (str(item[0][0]), str(item[0][1]), item[0][2])):
        year, month_number = map(int, month.split("-"))
        all_person_shifts = by_employee.get((store_id, person_id), [])
        month_shifts = [row for row in all_person_shifts if month_key(row.work_day) == month]
        worked = {row.work_day for row in month_shifts}
        complete_weekends, free_saturdays, free_sundays = weekend_counts(year, month_number, worked)
        touching = [streak for streak in find_consecutive_streaks([row.work_day for row in all_person_shifts]) if any(month_key(day) == month for day in streak)]
        max_streak = max((len(streak) for streak in touching), default=0)
        count_consecutive = len(groups.get((store_id, person_id, month, settings.max_consecutive_days.incident_type), []))
        count_long = len(groups.get((store_id, person_id, month, settings.max_shift_hours.incident_type), []))
        count_short = len(groups.get((store_id, person_id, month, settings.min_shift_hours.incident_type), []))
        count_rest = len(groups.get((store_id, person_id, month, settings.min_rest_hours.incident_type), []))
        summaries.append({
            "id_tienda": store_id,
            "personId": person_id,
            "applicableWorkingHours": applicable,
            "mes": month,
            "dias_trabajados": len(worked),
            "max_dias_consecutivos": max_streak,
            "incidencias_dias_consecutivos": count_consecutive,
            "cumple_max_5_dias": "SI" if count_consecutive == 0 else "NO",
            "turnos_superiores_7_5h": count_long,
            "cumple_duracion_maxima": "SI" if count_long == 0 else "NO",
            "turnos_inferiores_4h": count_short,
            "cumple_duracion_minima": "SI" if count_short == 0 else "NO",
            "descansos_inferiores_11h": count_rest,
            "cumple_descanso_entre_jornadas": "SI" if count_rest == 0 else "NO",
            "cumple_todas_las_reglas": "SI" if count_consecutive + count_long + count_short + count_rest == 0 else "NO",
            "fines_semana_completos_libres": complete_weekends,
            "sabados_libres": free_saturdays,
            "domingos_libres": free_sundays,
        })
    return summaries


def analyze_shifts(shifts: list[ShiftRow], employee_months: dict[tuple[Any, Any, str], Any], settings: ValidatorSettings = SETTINGS):
    incidents = run_rules(shifts, settings)
    return build_monthly_summaries(shifts, employee_months, incidents, settings), incidents
