from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any, Iterable

from workforce_validator.models import AbsenceDay, ShiftRow


MORNING_CUTOFF = time(13, 0)
SHIFT_PERIOD_MORNING = "MAÑANA"
SHIFT_PERIOD_AFTERNOON = "TARDE"


def classify_shift_period(shift_start: datetime) -> str:
    """Clasifica un turno por su hora real de inicio.

    Los turnos que comienzan antes de las 13:00 son de mañana. Los que
    comienzan a las 13:00 o después son de tarde.
    """
    local_time = shift_start.timetz().replace(tzinfo=None)
    return SHIFT_PERIOD_MORNING if local_time < MORNING_CUTOFF else SHIFT_PERIOD_AFTERNOON


def analyze_shift_balance(shifts: Iterable[ShiftRow]) -> list[dict[str, Any]]:
    """Agrega el reparto de turnos de mañana y tarde por empleado.

    El índice de equilibrio vale 0 cuando todos los turnos están en una única
    franja y 100 cuando el reparto es exactamente 50/50. No evalúa si el
    reparto es correcto; únicamente facilita la comparación entre empleados.
    """
    grouped: dict[tuple[Any, Any], dict[str, float]] = defaultdict(
        lambda: {
            "turnos_manana": 0,
            "turnos_tarde": 0,
            "horas_manana": 0.0,
            "horas_tarde": 0.0,
        }
    )

    for shift in shifts:
        key = (shift.store_id, shift.person_id)
        period = classify_shift_period(shift.shift_start)
        if period == SHIFT_PERIOD_MORNING:
            grouped[key]["turnos_manana"] += 1
            grouped[key]["horas_manana"] += shift.worked_hours
        else:
            grouped[key]["turnos_tarde"] += 1
            grouped[key]["horas_tarde"] += shift.worked_hours

    rows: list[dict[str, Any]] = []
    for (store_id, person_id), values in sorted(grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        morning = int(values["turnos_manana"])
        afternoon = int(values["turnos_tarde"])
        total = morning + afternoon
        morning_pct = morning / total * 100 if total else 0.0
        afternoon_pct = afternoon / total * 100 if total else 0.0
        balance_index = 2 * min(morning, afternoon) / total * 100 if total else 0.0

        if morning and afternoon:
            rotation_status = "Mañana y tarde"
        elif morning:
            rotation_status = "Solo mañanas"
        else:
            rotation_status = "Solo tardes"

        rows.append(
            {
                "id_tienda": store_id,
                "personId": person_id,
                "turnos_manana": morning,
                "turnos_tarde": afternoon,
                "turnos_totales": total,
                "horas_manana": round(values["horas_manana"], 4),
                "horas_tarde": round(values["horas_tarde"], 4),
                "porcentaje_manana": round(morning_pct, 2),
                "porcentaje_tarde": round(afternoon_pct, 2),
                "sesgo_tarde_pct": round(afternoon_pct - morning_pct, 2),
                "indice_equilibrio_pct": round(balance_index, 2),
                "rota_manana_tarde": "SI" if morning and afternoon else "NO",
                "estado_rotacion": rotation_status,
            }
        )
    return rows


def analyze_daily_absences(absences: Iterable[AbsenceDay], data_dates: set[date]) -> list[dict[str, Any]]:
    """Calcula ausencias por fecha conservando también los días con cero.

    ``empleados_ausentes`` cuenta personas únicas; ``registros_ausencia``
    conserva el número de tipos/estados de ausencia extraídos por el motor.
    """
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
