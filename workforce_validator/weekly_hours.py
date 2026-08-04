from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import daterange, month_key, week_start
from workforce_validator.models import AbsenceDay, ShiftRow


def _contract_for_week(
    employee_months: dict[tuple[Any, Any, str], Any],
    store_id: Any,
    person_id: Any,
    week_days: set[date],
    data_dates: set[date],
) -> tuple[float | None, str, str]:
    months = sorted({month_key(day) for day in week_days & data_dates})
    raw = [(month, employee_months.get((store_id, person_id, month))) for month in months]
    informed = [(month, value) for month, value in raw if value not in (None, "")]
    normalized = {str(value).strip() for _, value in informed}
    detail = "; ".join(f"{month}: {value}" for month, value in raw)
    if len(normalized) > 1:
        return None, "CAMBIO CONTRATO", detail
    if not informed:
        return None, "SIN HORAS CONTRATO", detail
    try:
        return float(informed[-1][1]), "OK", detail
    except (TypeError, ValueError):
        return None, "SIN HORAS CONTRATO", detail


def analyze_weekly_hours(shifts: list[ShiftRow], employee_months: dict[tuple[Any, Any, str], Any], data_dates: set[date], absences: list[AbsenceDay], employee_presence_dates: dict[tuple[Any, Any], set[date]], settings: ValidatorSettings = SETTINGS) -> list[dict[str, Any]]:
    tolerance = settings.calculation.weekly_hours_tolerance
    hours_by_week = defaultdict(float)
    hours_by_employee = defaultdict(list)
    worked_days = defaultdict(set)
    employees = {(store_id, person_id) for store_id, person_id, _ in employee_months}
    absences_by_day = defaultdict(set)
    for shift in shifts:
        employee = (shift.store_id, shift.person_id)
        employees.add(employee)
        hours_by_week[(shift.store_id, shift.person_id, week_start(shift.work_day))] += shift.worked_hours
        hours_by_employee[employee].append(shift.worked_hours)
        worked_days[employee].add(shift.work_day)
    for absence in absences:
        employees.add((absence.store_id, absence.person_id))
        absences_by_day[(absence.store_id, absence.person_id, absence.absence_day)].add(absence.absence_type)
    if not data_dates:
        return []
    first_week = week_start(min(data_dates))
    last_week = week_start(max(data_dates))
    week_starts = [day for day in daterange(first_week, last_week) if day.weekday() == 0]
    rows = []
    for store_id, person_id in sorted(employees, key=lambda item: (str(item[0]), str(item[1]))):
        employee = (store_id, person_id)
        values = hours_by_employee.get(employee, [])
        average_daily = round(sum(values) / len(values), 4) if values else None
        presence_dates = employee_presence_dates.get(employee, set())
        all_absence_dates = {day for (sid, pid, day), types in absences_by_day.items() if sid == store_id and pid == person_id and types}
        absent_entire_period = bool(presence_dates and presence_dates.issubset(all_absence_dates) and not worked_days.get(employee))
        for monday in week_starts:
            sunday = monday + timedelta(days=6)
            week_days = {monday + timedelta(days=index) for index in range(7)}
            covered = len(week_days & data_dates)
            complete = covered == 7
            planned = round(hours_by_week.get((store_id, person_id, monday), 0.0), 4)
            contracted, contract_state, contract_detail = _contract_for_week(
                employee_months, store_id, person_id, week_days, data_dates
            )
            difference = round(planned - contracted, 4) if contracted is not None else None
            missing = round(max(contracted - planned, 0.0), 4) if contracted is not None else None
            excess = round(max(planned - contracted, 0.0), 4) if contracted is not None else None
            absence_days = sorted(day for day in week_days if (store_id, person_id, day) in absences_by_day and day not in worked_days.get(employee, set()) and day in data_dates)
            absence_types = sorted({absence_type for day in absence_days for absence_type in absences_by_day[(store_id, person_id, day)]})
            potential = round(len(absence_days) * average_daily, 4) if average_daily is not None else None
            if not complete:
                status = "NO EVALUABLE"
            elif contract_state == "CAMBIO CONTRATO":
                status = "CAMBIO CONTRATO"
            elif contracted is None:
                status = "SIN HORAS CONTRATO"
            elif abs(difference) <= tolerance:
                status = "COINCIDE"
            elif difference < 0:
                status = "FALTAN HORAS"
            else:
                status = "EXCESO HORAS"
            missing_and_absence = bool(complete and missing is not None and missing > tolerance and absence_days)
            if absent_entire_period:
                explanation = "AUSENTE TODO EL PERIODO"
            elif not missing_and_absence:
                explanation = "NO"
            elif potential is None:
                explanation = "AUSENCIA SIN MEDIA CALCULABLE"
            elif potential + tolerance >= missing:
                explanation = "PODRIA EXPLICAR TODAS LAS HORAS FALTANTES"
            else:
                explanation = "PODRIA EXPLICAR PARTE DE LAS HORAS FALTANTES"
            rows.append({
                "id_tienda": store_id,
                "personId": person_id,
                "ano_iso": monday.isocalendar().year,
                "semana_iso": monday.isocalendar().week,
                "inicio_semana": monday,
                "fin_semana": sunday,
                "dias_cubiertos_fichero": covered,
                "semana_completa_en_fichero": "SI" if complete else "NO",
                "applicableWorkingHours": contracted,
                "estado_contrato_semana": contract_state,
                "detalle_contrato_semana": contract_detail,
                "horas_planificadas": planned,
                "diferencia_planificadas_menos_contrato": difference,
                "horas_no_planificadas_hasta_contrato": missing,
                "horas_planificadas_en_exceso": excess,
                "estado_planificacion": status,
                "cumple_horas_contrato": "SI" if status == "COINCIDE" else "NO" if status in {"FALTAN HORAS", "EXCESO HORAS"} else "NO EVALUABLE",
                "media_horas_dia_planificado": average_daily,
                "dias_ausencia_sin_turno": len(absence_days),
                "fechas_ausencia_sin_turno": ", ".join(day.isoformat() for day in absence_days),
                "tipos_ausencia": ", ".join(absence_types),
                "horas_potenciales_asociadas_ausencia": potential,
                "faltan_horas_y_hay_ausencia": "SI" if missing_and_absence else "NO",
                "posible_explicacion_por_ausencia": explanation,
                "ausente_todo_el_periodo": "SI" if absent_entire_period else "NO",
            })
    return rows
