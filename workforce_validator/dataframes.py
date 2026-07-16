from __future__ import annotations

import pandas as pd
from workforce_validator.models import ValidationResult


def result_dataframes(result: ValidationResult) -> dict[str, pd.DataFrame]:
    shifts = pd.DataFrame([{
        "id_tienda": s.store_id, "personId": s.person_id,
        "applicableWorkingHours": s.applicable_working_hours,
        "day": s.work_day, "hora_inicio": s.shift_start, "hora_fin": s.shift_end,
        "horas_totales": s.worked_hours, "duracion_descanso": s.break_hours,
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
    return {
        "shifts": shifts,
        "summaries": pd.DataFrame(result.summaries),
        "incidents": incidents,
        "weekly": pd.DataFrame(result.weekly_rows),
        "absences": absences,
    }
