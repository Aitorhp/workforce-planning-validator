from __future__ import annotations

import pandas as pd

from workforce_validator.analytics import (
    analyze_daily_absences,
    analyze_shift_balance,
    classify_shift_period,
)
from workforce_validator.contracts import analyze_contract_changes
from workforce_validator.models import ValidationResult


SHIFT_BALANCE_COLUMNS = [
    "id_tienda", "personId", "turnos_manana", "turnos_central", "turnos_tarde",
    "turnos_totales", "horas_manana", "horas_central", "horas_tarde",
    "porcentaje_manana", "porcentaje_central", "porcentaje_tarde",
    "sesgo_tarde_pct", "indice_equilibrio_pct", "rota_manana_tarde",
    "cubre_tres_franjas", "estado_rotacion",
]

CONTRACT_CHANGE_COLUMNS = [
    "id_tienda", "personId", "mes_anterior", "horas_mes_anterior",
    "mes_posterior", "horas_mes_posterior", "variacion_horas",
    "detalle_contrato", "requiere_revision",
]

ABSENCE_DAILY_COLUMNS = [
    "fecha", "empleados_ausentes", "registros_ausencia", "tipos_ausencia",
]


def result_dataframes(result: ValidationResult) -> dict[str, pd.DataFrame]:
    shifts = pd.DataFrame([{
        "id_tienda": s.store_id, "personId": s.person_id,
        "applicableWorkingHours": s.applicable_working_hours,
        "day": s.work_day, "hora_inicio": s.shift_start, "hora_fin": s.shift_end,
        "horas_totales": s.worked_hours, "duracion_descanso": s.break_hours,
        "franja_turno": classify_shift_period(s.shift_start),
    } for s in result.shifts])
    incidents = pd.DataFrame([{
        "id_tienda": i.store_id, "personId": i.person_id, "mes": i.month,
        "tipo_incidencia": i.incident_type, "fecha_inicio": i.start_date,
        "fecha_fin": i.end_date, "valor_observado": i.observed_value,
        "limite": i.limit_text, "detalle": i.detail,
    } for i in result.incidents])
    absences = pd.DataFrame([{
        "id_tienda": a.store_id, "personId": a.person_id, "fecha": a.absence_day,
        "tipo_ausencia": a.absence_type, "estado": a.absence_status,
    } for a in result.absences])
    shift_balance = pd.DataFrame(
        analyze_shift_balance(result.shifts), columns=SHIFT_BALANCE_COLUMNS,
    )
    contract_changes = pd.DataFrame(
        analyze_contract_changes(result.employee_months), columns=CONTRACT_CHANGE_COLUMNS,
    )
    absence_daily = pd.DataFrame(
        analyze_daily_absences(result.absences, result.data_dates),
        columns=ABSENCE_DAILY_COLUMNS,
    )
    return {
        "shifts": shifts,
        "summaries": pd.DataFrame(result.summaries),
        "incidents": incidents,
        "weekly": pd.DataFrame(result.weekly_rows),
        "absences": absences,
        "shift_balance": shift_balance,
        "contract_changes": contract_changes,
        "absence_daily": absence_daily,
    }
