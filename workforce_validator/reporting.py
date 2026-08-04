from __future__ import annotations

from datetime import date, datetime, time
from html import escape
from typing import Any, Mapping

import pandas as pd

from workforce_validator.analytics import (
    SHIFT_PERIOD_AFTERNOON,
    SHIFT_PERIOD_CENTRAL,
    SHIFT_PERIOD_MORNING,
    classify_shift_period,
)


def build_shift_balance_dataframe(
    shifts: pd.DataFrame,
    morning_cutoff: time,
    afternoon_cutoff: time,
    weeks_in_scope: int = 1,
) -> pd.DataFrame:
    columns = [
        "id_tienda", "personId", "turnos_manana", "turnos_central", "turnos_tarde",
        "turnos_totales", "horas_manana", "horas_central", "horas_tarde",
        "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana",
        "porcentaje_manana", "porcentaje_central", "porcentaje_tarde",
        "indice_equilibrio_pct", "cubre_tres_franjas", "estado_rotacion",
    ]
    if shifts.empty:
        return pd.DataFrame(columns=columns)
    if morning_cutoff >= afternoon_cutoff:
        raise ValueError("El límite de mañana debe ser anterior al límite de tarde.")

    frame = shifts.copy()
    frame["franja_parametrizada"] = frame["hora_inicio"].map(
        lambda value: classify_shift_period(
            pd.Timestamp(value).to_pydatetime(), morning_cutoff, afternoon_cutoff
        )
    )
    for label, key in [
        (SHIFT_PERIOD_MORNING, "manana"),
        (SHIFT_PERIOD_CENTRAL, "central"),
        (SHIFT_PERIOD_AFTERNOON, "tarde"),
    ]:
        frame[f"es_{key}"] = frame["franja_parametrizada"].eq(label).astype(int)
        frame[f"horas_{key}_fila"] = frame["horas_totales"].where(
            frame[f"es_{key}"].eq(1), 0.0
        )

    balance = frame.groupby(["id_tienda", "personId"], as_index=False).agg(
        turnos_manana=("es_manana", "sum"),
        turnos_central=("es_central", "sum"),
        turnos_tarde=("es_tarde", "sum"),
        turnos_totales=("personId", "size"),
        horas_manana=("horas_manana_fila", "sum"),
        horas_central=("horas_central_fila", "sum"),
        horas_tarde=("horas_tarde_fila", "sum"),
    )
    weeks = max(int(weeks_in_scope), 1)
    balance["promedio_mananas_semana"] = balance["turnos_manana"] / weeks
    balance["promedio_centrales_semana"] = balance["turnos_central"] / weeks
    balance["promedio_tardes_semana"] = balance["turnos_tarde"] / weeks
    for key in ("manana", "central", "tarde"):
        balance[f"porcentaje_{key}"] = (
            balance[f"turnos_{key}"] / balance["turnos_totales"] * 100
        )
    balance["indice_equilibrio_pct"] = (
        3 * balance[["turnos_manana", "turnos_central", "turnos_tarde"]].min(axis=1)
        / balance["turnos_totales"] * 100
    )
    balance["cubre_tres_franjas"] = (
        balance[["turnos_manana", "turnos_central", "turnos_tarde"]].gt(0).all(axis=1)
    ).map({True: "SI", False: "NO"})

    def status(row: pd.Series) -> str:
        active = []
        if row.turnos_manana:
            active.append("Mañana")
        if row.turnos_central:
            active.append("central")
        if row.turnos_tarde:
            active.append("tarde")
        if len(active) == 3:
            return "Mañana, central y tarde"
        if len(active) == 1:
            return {"Mañana": "Solo mañanas", "central": "Solo centrales", "tarde": "Solo tardes"}[active[0]]
        return " y ".join(active)

    balance["estado_rotacion"] = balance.apply(status, axis=1)
    return balance[columns]


def _table_html(frame: pd.DataFrame, empty_text: str) -> str:
    if frame.empty:
        return f'<p class="empty">{escape(empty_text)}</p>'
    return frame.to_html(index=False, border=0, classes="data-table", escape=True)


def build_html_report(
    frames: Mapping[str, pd.DataFrame],
    store_id: Any,
    schedule_source: str,
    morning_cutoff: time,
    afternoon_cutoff: time,
    period_start: date | None,
    period_end: date | None,
) -> bytes:
    shifts = frames.get("shifts", pd.DataFrame()).copy()
    absence_daily = frames.get("absence_daily", pd.DataFrame()).copy()
    if not absence_daily.empty and "fecha" in absence_daily:
        weeks = max(int(absence_daily["fecha"].dt.to_period("W-SUN").nunique()), 1)
    elif not shifts.empty:
        weeks = max(int(shifts["day"].dt.to_period("W-SUN").nunique()), 1)
    else:
        weeks = 1
    balance = build_shift_balance_dataframe(shifts, morning_cutoff, afternoon_cutoff, weeks)
    changes = frames.get("contract_changes", pd.DataFrame()).copy()
    period = "Sin fechas" if not period_start or not period_end else f"{period_start:%d/%m/%Y} - {period_end:%d/%m/%Y}"
    balance_view = balance.rename(columns={
        "id_tienda":"Tienda", "personId":"Empleado", "estado_rotacion":"Rotación",
        "turnos_manana":"Mañanas", "turnos_central":"Centrales", "turnos_tarde":"Tardes",
        "promedio_mananas_semana":"Mañanas/semana", "promedio_centrales_semana":"Centrales/semana",
        "promedio_tardes_semana":"Tardes/semana", "indice_equilibrio_pct":"Equilibrio (%)",
    })
    if not balance_view.empty:
        balance_view = balance_view[["Tienda","Empleado","Rotación","Mañanas","Centrales","Tardes","Mañanas/semana","Centrales/semana","Tardes/semana","Equilibrio (%)"]]
    changes_view = changes.rename(columns={
        "id_tienda":"Tienda", "personId":"Empleado", "mes_anterior":"Mes anterior",
        "horas_mes_anterior":"Horas anteriores", "mes_posterior":"Mes posterior",
        "horas_mes_posterior":"Horas posteriores", "variacion_horas":"Variación",
        "detalle_contrato":"Detalle",
    })
    if not changes_view.empty:
        changes_view = changes_view[["Tienda","Empleado","Mes anterior","Horas anteriores","Mes posterior","Horas posteriores","Variación","Detalle"]]
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Validación tienda {escape(str(store_id))}</title><style>body{{font-family:Arial,sans-serif;background:#f8fafc;color:#172033;margin:0}}main{{max-width:1500px;margin:auto;padding:28px}}section{{background:white;border:1px solid #dbe3ee;border-radius:12px;padding:20px;margin:18px 0;overflow:auto}}.note{{background:#eff6ff;border-left:4px solid #2563eb;padding:10px 12px}}.data-table{{border-collapse:collapse;width:100%;font-size:13px}}.data-table th,.data-table td{{border-bottom:1px solid #e2e8f0;padding:9px;text-align:left;white-space:nowrap}}.data-table th{{background:#eef4fb}}.meta{{color:#526079}}</style></head><body><main><h1>Validador de planificaciones</h1><p class="meta">Tienda {escape(str(store_id))} · {escape(period)} · {escape(schedule_source)} · generado {generated}</p><section><h2>Criterios de mañana, central y tarde</h2><p class="note">Mañana: antes de {morning_cutoff:%H:%M}. Central: desde {morning_cutoff:%H:%M} hasta {afternoon_cutoff:%H:%M}, ambos incluidos. Tarde: después de {afternoon_cutoff:%H:%M}.</p></section><section><h2>Cambios de horas contractuales entre meses</h2>{_table_html(changes_view, "No se han detectado cambios de applicableWorkingHours entre meses.")}</section><section><h2>Balance mañana / central / tarde</h2>{_table_html(balance_view, "No hay turnos para calcular el balance.")}</section></main></body></html>'''
    return html.encode("utf-8")
