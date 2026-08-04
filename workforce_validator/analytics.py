from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any, Iterable

from workforce_validator.models import AbsenceDay, ShiftRow


MORNING_CUTOFF = time(11, 0)
AFTERNOON_CUTOFF = time(14, 0)
SHIFT_PERIOD_MORNING = "MAÑANA"
SHIFT_PERIOD_CENTRAL = "CENTRAL"
SHIFT_PERIOD_AFTERNOON = "TARDE"


def _validate_cutoffs(morning_cutoff: time, afternoon_cutoff: time) -> None:
    if morning_cutoff >= afternoon_cutoff:
        raise ValueError("El límite de mañana debe ser anterior al límite de tarde.")


def classify_shift_period(
    shift_start: datetime,
    morning_cutoff: time = MORNING_CUTOFF,
    afternoon_cutoff: time = AFTERNOON_CUTOFF,
) -> str:
    """Clasifica el turno por hora de inicio usando tres franjas.

    - Mañana: inicio estrictamente anterior al límite de mañana.
    - Tarde: inicio estrictamente posterior al límite de tarde.
    - Central: cualquier inicio comprendido entre ambos límites, incluidos.
    """
    _validate_cutoffs(morning_cutoff, afternoon_cutoff)
    local_time = shift_start.timetz().replace(tzinfo=None)
    if local_time < morning_cutoff:
        return SHIFT_PERIOD_MORNING
    if local_time > afternoon_cutoff:
        return SHIFT_PERIOD_AFTERNOON
    return SHIFT_PERIOD_CENTRAL


def _rotation_status(morning: int, central: int, afternoon: int) -> str:
    active = []
    if morning:
        active.append("Mañana")
    if central:
        active.append("central")
    if afternoon:
        active.append("tarde")
    if not active:
        return "Sin turnos"
    if len(active) == 1:
        return {
            "Mañana": "Solo mañanas",
            "central": "Solo centrales",
            "tarde": "Solo tardes",
        }[active[0]]
    if len(active) == 3:
        return "Mañana, central y tarde"
    return " y ".join(active)


def analyze_shift_balance(
    shifts: Iterable[ShiftRow],
    morning_cutoff: time = MORNING_CUTOFF,
    afternoon_cutoff: time = AFTERNOON_CUTOFF,
) -> list[dict[str, Any]]:
    """Agrega el reparto de turnos de mañana, centrales y tarde por empleado."""
    _validate_cutoffs(morning_cutoff, afternoon_cutoff)
    grouped: dict[tuple[Any, Any], dict[str, float]] = defaultdict(
        lambda: {
            "turnos_manana": 0,
            "turnos_central": 0,
            "turnos_tarde": 0,
            "horas_manana": 0.0,
            "horas_central": 0.0,
            "horas_tarde": 0.0,
        }
    )

    for shift in shifts:
        key = (shift.store_id, shift.person_id)
        period = classify_shift_period(shift.shift_start, morning_cutoff, afternoon_cutoff)
        if period == SHIFT_PERIOD_MORNING:
            grouped[key]["turnos_manana"] += 1
            grouped[key]["horas_manana"] += shift.worked_hours
        elif period == SHIFT_PERIOD_AFTERNOON:
            grouped[key]["turnos_tarde"] += 1
            grouped[key]["horas_tarde"] += shift.worked_hours
        else:
            grouped[key]["turnos_central"] += 1
            grouped[key]["horas_central"] += shift.worked_hours

    rows: list[dict[str, Any]] = []
    for (store_id, person_id), values in sorted(grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        morning = int(values["turnos_manana"])
        central = int(values["turnos_central"])
        afternoon = int(values["turnos_tarde"])
        total = morning + central + afternoon
        morning_pct = morning / total * 100 if total else 0.0
        central_pct = central / total * 100 if total else 0.0
        afternoon_pct = afternoon / total * 100 if total else 0.0
        balance_index = 3 * min(morning, central, afternoon) / total * 100 if total else 0.0
        covers_all = bool(morning and central and afternoon)

        rows.append(
            {
                "id_tienda": store_id,
                "personId": person_id,
                "turnos_manana": morning,
                "turnos_central": central,
                "turnos_tarde": afternoon,
                "turnos_totales": total,
                "horas_manana": round(values["horas_manana"], 4),
                "horas_central": round(values["horas_central"], 4),
                "horas_tarde": round(values["horas_tarde"], 4),
                "porcentaje_manana": round(morning_pct, 2),
                "porcentaje_central": round(central_pct, 2),
                "porcentaje_tarde": round(afternoon_pct, 2),
                "sesgo_tarde_pct": round(afternoon_pct - morning_pct, 2),
                "indice_equilibrio_pct": round(balance_index, 2),
                "rota_manana_tarde": "SI" if morning and afternoon else "NO",
                "cubre_tres_franjas": "SI" if covers_all else "NO",
                "estado_rotacion": _rotation_status(morning, central, afternoon),
            }
        )
    return rows


def analyze_daily_absences(absences: Iterable[AbsenceDay], data_dates: set[date]) -> list[dict[str, Any]]:
    """Calcula ausencias por fecha conservando también los días con cero."""
    absences_by_date: dict[date, list[AbsenceDay]] = defaultdict(list)
    for absence in absences:
        absences_by_date[absence.absence_day].append(absence)

    dates = sorted(data_dates or set(absences_by_date))
    rows: list[dict[str, Any]] = []
    for current_date in dates:
        daily = absences_by_date.get(current_date, [])
        employees = {(absence.store_id, absence.person_id) for absence in daily}
        types = sorted({absence.absence_type for absence in daily})
        rows.append(
            {
                "fecha": current_date,
                "empleados_ausentes": len(employees),
                "registros_ausencia": len(daily),
                "tipos_ausencia": ", ".join(types),
            }
        )
    return rows
