from __future__ import annotations

from datetime import time
from typing import Any

import pandas as pd

CONTRACT_TOLERANCE_HOURS = 0.01
DEFAULT_MORNING_CUTOFF = time(11, 0)
DEFAULT_AFTERNOON_CUTOFF = time(14, 0)


def _month_ordinal(value: Any) -> int:
    period = pd.Period(str(value), freq="M")
    return period.year * 12 + period.month


def build_contract_change_table(summaries: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "id_tienda", "personId", "mes_anterior", "horas_mes_anterior",
        "mes_siguiente", "horas_mes_siguiente", "diferencia_horas", "estado_revision",
    ]
    required = {"id_tienda", "personId", "mes", "applicableWorkingHours"}
    if summaries.empty or not required.issubset(summaries.columns):
        return pd.DataFrame(columns=columns)

    monthly = summaries[list(required)].copy()
    monthly["mes"] = monthly["mes"].astype(str)
    monthly["applicableWorkingHours"] = pd.to_numeric(monthly["applicableWorkingHours"], errors="coerce")
    monthly = monthly.dropna(subset=["applicableWorkingHours"])
    monthly = monthly.sort_values(["id_tienda", "personId", "mes"]).drop_duplicates(
        ["id_tienda", "personId", "mes"], keep="last"
    )

    rows: list[dict[str, Any]] = []
    for (store_id, person_id), employee in monthly.groupby(["id_tienda", "personId"], sort=True):
        records = employee.sort_values("mes").to_dict("records")
        for previous, current in zip(records, records[1:]):
            if _month_ordinal(current["mes"]) - _month_ordinal(previous["mes"]) != 1:
                continue
            difference = float(current["applicableWorkingHours"]) - float(previous["applicableWorkingHours"])
            if abs(difference) <= CONTRACT_TOLERANCE_HOURS:
                continue
            rows.append({
                "id_tienda": store_id,
                "personId": person_id,
                "mes_anterior": previous["mes"],
                "horas_mes_anterior": float(previous["applicableWorkingHours"]),
                "mes_siguiente": current["mes"],
                "horas_mes_siguiente": float(current["applicableWorkingHours"]),
                "diferencia_horas": round(difference, 4),
                "estado_revision": "REVISAR CAMBIO DE CONTRATO",
            })

    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["id_tienda", "personId", "mes_anterior"], ignore_index=True
    )


def _cutoff_minutes(value: time | str) -> int:
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    parsed = pd.Timestamp(f"2000-01-01 {value}")
    return parsed.hour * 60 + parsed.minute


def build_configurable_shift_balance(
    shifts: pd.DataFrame,
    morning_cutoff: time | str = DEFAULT_MORNING_CUTOFF,
    afternoon_cutoff: time | str = DEFAULT_AFTERNOON_CUTOFF,
    weeks_in_scope: int = 1,
) -> pd.DataFrame:
    columns = [
        "id_tienda", "personId", "turnos_manana", "turnos_central", "turnos_tarde",
        "turnos_totales", "horas_manana", "horas_central", "horas_tarde",
        "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana",
        "porcentaje_manana", "porcentaje_central", "porcentaje_tarde",
        "indice_equilibrio_pct", "franjas_cubiertas", "estado_rotacion", "faltan_franjas",
    ]
    required = {"id_tienda", "personId", "hora_inicio", "horas_totales"}
    if shifts.empty or not required.issubset(shifts.columns):
        return pd.DataFrame(columns=columns)

    morning_minutes = _cutoff_minutes(morning_cutoff)
    afternoon_minutes = _cutoff_minutes(afternoon_cutoff)
    if morning_minutes >= afternoon_minutes:
        raise ValueError("El corte de mañana debe ser anterior al corte de tarde.")

    data = shifts.copy()
    data["hora_inicio"] = pd.to_datetime(data["hora_inicio"], errors="coerce")
    data["horas_totales"] = pd.to_numeric(data["horas_totales"], errors="coerce").fillna(0.0)
    data = data.dropna(subset=["hora_inicio"])
    if data.empty:
        return pd.DataFrame(columns=columns)

    start_minutes = data["hora_inicio"].dt.hour * 60 + data["hora_inicio"].dt.minute
    data["franja_configurada"] = "CENTRAL"
    data.loc[start_minutes.lt(morning_minutes), "franja_configurada"] = "MAÑANA"
    data.loc[start_minutes.gt(afternoon_minutes), "franja_configurada"] = "TARDE"

    for period, suffix in (("MAÑANA", "manana"), ("CENTRAL", "central"), ("TARDE", "tarde")):
        flag = data["franja_configurada"].eq(period)
        data[f"es_{suffix}"] = flag.astype(int)
        data[f"horas_{suffix}_fila"] = data["horas_totales"].where(flag, 0.0)

    balance = data.groupby(["id_tienda", "personId"], as_index=False).agg(
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

    count_columns = ["turnos_manana", "turnos_central", "turnos_tarde"]
    for source, target in zip(count_columns, ["porcentaje_manana", "porcentaje_central", "porcentaje_tarde"]):
        balance[target] = balance[source] / balance["turnos_totales"] * 100

    shares = balance[count_columns].div(balance["turnos_totales"], axis=0)
    balance["indice_equilibrio_pct"] = (
        (1.0 - shares.pow(2).sum(axis=1)) / (1.0 - 1.0 / 3.0) * 100
    ).clip(lower=0.0, upper=100.0)
    balance["franjas_cubiertas"] = balance[count_columns].gt(0).sum(axis=1)
    balance["estado_rotacion"] = balance["franjas_cubiertas"].map({3: "Tres franjas", 2: "Dos franjas", 1: "Una franja"})

    def missing_periods(row: pd.Series) -> str:
        labels = []
        if row["turnos_manana"] == 0:
            labels.append("Mañana")
        if row["turnos_central"] == 0:
            labels.append("Central")
        if row["turnos_tarde"] == 0:
            labels.append("Tarde")
        return ", ".join(labels) if labels else "Ninguna"

    balance["faltan_franjas"] = balance.apply(missing_periods, axis=1)
    numeric_columns = [
        "horas_manana", "horas_central", "horas_tarde",
        "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana",
        "porcentaje_manana", "porcentaje_central", "porcentaje_tarde", "indice_equilibrio_pct",
    ]
    balance[numeric_columns] = balance[numeric_columns].round(4)
    return balance[columns].sort_values(["id_tienda", "personId"], ignore_index=True)


DASHBOARD_OVERRIDES = r'''
_render_weekly_base = render_weekly


def render_weekly(frames):
    _render_weekly_base(frames)
    st.markdown("#### Cambios de horas contractuales entre meses consecutivos")
    help_text(
        "Esta tabla muestra únicamente empleados cuyo applicableWorkingHours cambia entre dos meses consecutivos. "
        "El cambio se considera una alerta de calidad del dato y no modifica los cálculos del motor."
    )
    changes = build_contract_change_table(frames.get("summaries", pd.DataFrame()))
    if changes.empty:
        st.success("No se han detectado cambios de horas contractuales entre meses consecutivos.")
        return
    view = changes.rename(columns={
        "id_tienda": "Tienda", "personId": "Empleado", "mes_anterior": "Mes anterior",
        "horas_mes_anterior": "Horas mes anterior", "mes_siguiente": "Mes siguiente",
        "horas_mes_siguiente": "Horas mes siguiente", "diferencia_horas": "Diferencia",
        "estado_revision": "Estado",
    })
    st.warning(f"Hay {len(view)} cambio(s) contractual(es) que requieren revisión.")
    st.dataframe(
        view, hide_index=True, use_container_width=True,
        column_config={
            "Horas mes anterior": st.column_config.NumberColumn(format="%.2f h"),
            "Horas mes siguiente": st.column_config.NumberColumn(format="%.2f h"),
            "Diferencia": st.column_config.NumberColumn(format="%+.2f h"),
        },
    )


def render_shift_balance(frames):
    shifts = frames.get("shifts", pd.DataFrame()).copy()
    date_scope = frames.get("absence_daily", pd.DataFrame()).copy()
    st.subheader("Balance de turnos de mañana, central y tarde")
    help_text(
        "La clasificación usa la hora de inicio del turno. Mañana es estrictamente anterior al primer corte, "
        "tarde es estrictamente posterior al segundo y los límites, junto con las horas intermedias, son centrales."
    )
    controls = st.columns(2)
    morning_cutoff = controls[0].time_input(
        "Los turnos de mañana empiezan antes de", value=pd.Timestamp("11:00").time(),
        step=900, key="shift_balance_morning_cutoff",
    )
    afternoon_cutoff = controls[1].time_input(
        "Los turnos de tarde empiezan después de", value=pd.Timestamp("14:00").time(),
        step=900, key="shift_balance_afternoon_cutoff",
    )
    if morning_cutoff >= afternoon_cutoff:
        st.warning("El corte de mañana debe ser anterior al corte de tarde.")
        return
    st.caption(
        f"Regla activa: mañana < {morning_cutoff:%H:%M}; central entre {morning_cutoff:%H:%M} y "
        f"{afternoon_cutoff:%H:%M}, incluidos ambos límites; tarde > {afternoon_cutoff:%H:%M}."
    )
    if shifts.empty:
        st.warning("No hay turnos disponibles para calcular el balance de franjas.")
        return

    if not date_scope.empty:
        weeks_in_scope = date_scope["fecha"].dt.to_period("W-SUN").nunique()
    else:
        weeks_in_scope = shifts["day"].dt.to_period("W-SUN").nunique()
    weeks_in_scope = max(int(weeks_in_scope), 1)
    balance = build_configurable_shift_balance(shifts, morning_cutoff, afternoon_cutoff, weeks_in_scope)
    if balance.empty:
        st.warning("No hay turnos con una hora de inicio válida.")
        return

    total = len(balance)
    all_three = int(balance["franjas_cubiertas"].eq(3).sum())
    no_morning = int(balance["turnos_manana"].eq(0).sum())
    no_central = int(balance["turnos_central"].eq(0).sum())
    no_afternoon = int(balance["turnos_tarde"].eq(0).sum())
    cols = st.columns(6)
    kpi(cols[0], "Empleados", fmt(total), "Con al menos un turno", "blue")
    kpi(cols[1], "Cubren las 3 franjas", fmt(all_three), pct_text(pct(all_three, total)), "green" if all_three == total else "purple")
    kpi(cols[2], "Sin mañanas", fmt(no_morning), pct_text(pct(no_morning, total)), "red" if no_morning else "green")
    kpi(cols[3], "Sin centrales", fmt(no_central), pct_text(pct(no_central, total)), "red" if no_central else "green")
    kpi(cols[4], "Sin tardes", fmt(no_afternoon), pct_text(pct(no_afternoon, total)), "red" if no_afternoon else "green")
    kpi(cols[5], "Índice de equilibrio", pct_text(balance["indice_equilibrio_pct"].mean()), "0 = una franja; 100 = reparto uniforme", "blue")

    if all_three < total:
        st.warning(f"Hay {total - all_three} empleado(s) sin presencia en alguna de las tres franjas.")
    else:
        st.success("Todos los empleados tienen al menos un turno de mañana, central y tarde.")

    left, right = st.columns([.85, 1.5])
    with left:
        counts = balance["estado_rotacion"].value_counts().reindex(
            ["Tres franjas", "Dos franjas", "Una franja"], fill_value=0
        ).rename_axis("Estado").reset_index(name="Empleados")
        fig = px.pie(
            counts, names="Estado", values="Empleados", hole=.55, color="Estado",
            color_discrete_map={"Tres franjas": "#22a447", "Dos franjas": "#2563eb", "Una franja": "#dc3545"},
            height=410,
        )
        fig.update_traces(textinfo="value+percent")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Promedio semanal por empleado")
        help_text(
            "La tabla permite localizar rápidamente empleados sin mañanas, centrales o tardes. "
            "Los promedios se recalculan al cambiar cualquiera de los dos cortes."
        )
        chart = balance.assign(Empleado=balance["id_tienda"].astype(str) + " · " + balance["personId"].astype(str)).sort_values(
            ["franjas_cubiertas", "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana", "Empleado"],
            ascending=[True, True, True, True, True],
        )
        st.dataframe(
            chart[[
                "Empleado", "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana",
                "turnos_manana", "turnos_central", "turnos_tarde", "estado_rotacion", "faltan_franjas",
            ]], hide_index=True, use_container_width=True, height=min(620, 38 * (len(chart) + 1)),
            column_config={
                "promedio_mananas_semana": st.column_config.NumberColumn("Mañanas medias/semana", format="%.2f"),
                "promedio_centrales_semana": st.column_config.NumberColumn("Centrales medios/semana", format="%.2f"),
                "promedio_tardes_semana": st.column_config.NumberColumn("Tardes medias/semana", format="%.2f"),
                "turnos_manana": st.column_config.NumberColumn("Mañanas totales", format="%d"),
                "turnos_central": st.column_config.NumberColumn("Centrales totales", format="%d"),
                "turnos_tarde": st.column_config.NumberColumn("Tardes totales", format="%d"),
                "estado_rotacion": st.column_config.TextColumn("Cobertura de franjas"),
                "faltan_franjas": st.column_config.TextColumn("Franjas ausentes"),
            },
        )
        st.caption(f"Promedio calculado sobre {weeks_in_scope} semana(s) del periodo seleccionado.")

    st.markdown("#### Detalle por empleado")
    only_incomplete = st.checkbox(
        "Mostrar solo empleados sin las tres franjas", value=True, key="shift_balance_only_non_rotating"
    )
    view = balance.loc[balance["franjas_cubiertas"].lt(3)].copy() if only_incomplete else balance.copy()
    st.dataframe(
        view[[
            "id_tienda", "personId", "estado_rotacion", "faltan_franjas", "turnos_manana", "turnos_central",
            "turnos_tarde", "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana",
            "turnos_totales", "horas_manana", "horas_central", "horas_tarde", "porcentaje_manana",
            "porcentaje_central", "porcentaje_tarde", "indice_equilibrio_pct",
        ]], hide_index=True, use_container_width=True,
        column_config={
            "promedio_mananas_semana": st.column_config.NumberColumn("Mañanas medias/semana", format="%.2f"),
            "promedio_centrales_semana": st.column_config.NumberColumn("Centrales medios/semana", format="%.2f"),
            "promedio_tardes_semana": st.column_config.NumberColumn("Tardes medias/semana", format="%.2f"),
        },
    )
'''


def apply_contract_shift_support(source: str) -> str:
    import_marker = "from validator_engine import ("
    if import_marker not in source:
        raise RuntimeError("No se encontró el bloque de importaciones del dashboard.")
    source = source.replace(
        import_marker,
        "from contract_shift_dashboard import (\n"
        "    build_configurable_shift_balance,\n"
        "    build_contract_change_table,\n"
        ")\n\n" + import_marker,
        1,
    )

    tabs_marker = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])'
    if tabs_marker not in source:
        raise RuntimeError("No se encontró el bloque de pestañas esperado.")
    return source.replace(tabs_marker, DASHBOARD_OVERRIDES.rstrip() + "\n\n" + tabs_marker, 1)
