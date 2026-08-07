from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


def _week_start(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("W-SUN").start_time.normalize()


def active_planning_week_starts(shifts: pd.DataFrame) -> list[pd.Timestamp]:
    """Return only weeks where at least one employee has positive planned hours."""
    required = {"day", "horas_totales"}
    if shifts.empty or not required.issubset(shifts.columns):
        return []
    data = shifts[["day", "horas_totales"]].copy()
    data["day"] = pd.to_datetime(data["day"], errors="coerce")
    data["horas_totales"] = pd.to_numeric(data["horas_totales"], errors="coerce").fillna(0.0)
    data = data.loc[data["day"].notna() & data["horas_totales"].gt(0)]
    if data.empty:
        return []
    starts = data["day"].dt.to_period("W-SUN").dt.start_time.dt.normalize()
    return sorted(starts.drop_duplicates().tolist())


def restrict_to_active_planning_weeks(
    frames: dict[str, pd.DataFrame], data_dates: Iterable[Any]
) -> tuple[dict[str, pd.DataFrame], set[Any]]:
    """Remove fully empty planning weeks from all date/week-level presentation frames.

    Monthly summaries remain untouched because their calculation grain is employee-month.
    The business engine output is not mutated; this is strictly a presentation filter.
    """
    output = {name: frame.copy() for name, frame in frames.items()}
    active_starts = set(active_planning_week_starts(output.get("shifts", pd.DataFrame())))
    if not active_starts:
        return output, set(data_dates)

    def is_active(value: Any) -> bool:
        if pd.isna(value):
            return False
        return _week_start(value) in active_starts

    weekly = output.get("weekly")
    if weekly is not None and not weekly.empty and "inicio_semana" in weekly.columns:
        output["weekly"] = weekly.loc[weekly["inicio_semana"].map(is_active)].copy()

    for name, column in (("absences", "fecha"), ("absence_daily", "fecha")):
        frame = output.get(name)
        if frame is not None and not frame.empty and column in frame.columns:
            output[name] = frame.loc[frame[column].map(is_active)].copy()

    active_dates = {day for day in data_dates if is_active(day)}
    return output, active_dates


def build_contract_lookup(frames: dict[str, pd.DataFrame]) -> dict[tuple[str, str], float]:
    """Latest applicableWorkingHours per store/employee for table enrichment."""
    lookup: dict[tuple[str, str], float] = {}

    def consume(frame: pd.DataFrame, order_column: str | None = None) -> None:
        if frame is None or frame.empty:
            return
        required = {"id_tienda", "personId", "applicableWorkingHours"}
        if not required.issubset(frame.columns):
            return
        data = frame.copy()
        data["applicableWorkingHours"] = pd.to_numeric(data["applicableWorkingHours"], errors="coerce")
        data = data.dropna(subset=["applicableWorkingHours"])
        if order_column and order_column in data.columns:
            data[order_column] = pd.to_datetime(data[order_column], errors="coerce")
            data = data.sort_values(order_column)
        for row in data.itertuples(index=False):
            lookup[(str(getattr(row, "id_tienda")), str(getattr(row, "personId")))] = float(
                getattr(row, "applicableWorkingHours")
            )

    consume(frames.get("summaries", pd.DataFrame()), "mes")
    consume(frames.get("shifts", pd.DataFrame()), "day")
    consume(frames.get("weekly", pd.DataFrame()), "inicio_semana")
    return lookup


def apply_weekend_rule_thresholds(
    employees: pd.DataFrame,
    minimum_full_weekends: int = 1,
    minimum_saturdays: int = 1,
    minimum_sundays: int = 1,
) -> pd.DataFrame:
    """Add independent weekend-rule breach flags to an employee aggregate."""
    result = employees.copy()
    for column in ("fines_semana_libres", "sabados_libres", "domingos_libres"):
        if column not in result.columns:
            result[column] = 0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)
    result["incumple_fin_semana"] = result["fines_semana_libres"].lt(max(int(minimum_full_weekends), 0))
    result["incumple_sabado"] = result["sabados_libres"].lt(max(int(minimum_saturdays), 0))
    result["incumple_domingo"] = result["domingos_libres"].lt(max(int(minimum_sundays), 0))
    result["incumple_alguna_regla"] = result[
        ["incumple_fin_semana", "incumple_sabado", "incumple_domingo"]
    ].any(axis=1)
    return result


DASHBOARD_OVERRIDES = r'''
_RAW_DATAFRAME = st.dataframe
WFV_CONTRACT_LOOKUP = {}


def wfv_dataframe(data=None, *args, **kwargs):
    """Enrich employee tables with contract hours and sort them descending by contract."""
    if isinstance(data, pd.DataFrame):
        view = data.copy()
        store_col = next((name for name in ("id_tienda", "Tienda") if name in view.columns), None)
        person_col = next((name for name in ("personId", "Empleado") if name in view.columns), None)
        if store_col and person_col:
            contract_col = next(
                (name for name in ("Horas contrato", "applicableWorkingHours") if name in view.columns),
                None,
            )
            if contract_col is None:
                values = []
                for store, person in zip(view[store_col], view[person_col]):
                    person_key = str(person)
                    if " · " in person_key:
                        person_key = person_key.split(" · ")[-1].strip()
                    values.append(WFV_CONTRACT_LOOKUP.get((str(store), person_key)))
                insert_at = min(view.columns.get_loc(person_col) + 1, len(view.columns))
                view.insert(insert_at, "Horas contrato", values)
                contract_col = "Horas contrato"
            numeric_contract = pd.to_numeric(view[contract_col], errors="coerce")
            view = view.assign(_wfv_contract_sort=numeric_contract).sort_values(
                ["_wfv_contract_sort", store_col, person_col],
                ascending=[False, True, True],
                na_position="last",
            ).drop(columns="_wfv_contract_sort")
        data = view
    return _RAW_DATAFRAME(data, *args, **kwargs)


def render_weekends(frames, data_dates):
    st.subheader("Fines de semana y rotación de descansos")
    help_text(
        "Las tres reglas son independientes y editables. El cálculo se actualiza al cambiar los mínimos: "
        "fines de semana completos libres, sábados libres y domingos libres."
    )
    monthly, weekends = prepare_weekend_analysis(frames["shifts"], frames["weekly"], data_dates)
    if monthly.empty:
        st.warning("No hay información suficiente para calcular fines de semana.")
        return

    available_hours = monthly["applicableWorkingHours"].dropna()
    observed_maximum = float(available_hours.max()) if not available_hours.empty else 40.0
    filter_limit = max(80.0, observed_maximum)
    filter_cols = st.columns(2)
    minimum = filter_cols[0].number_input(
        "Horas contractuales mínimas", min_value=0.0, max_value=filter_limit,
        value=min(30.0, filter_limit), step=1.0, key="weekend_min_contract_hours",
    )
    maximum = filter_cols[1].number_input(
        "Horas contractuales máximas", min_value=0.0, max_value=filter_limit,
        value=filter_limit, step=1.0, key="weekend_max_contract_hours",
    )
    if minimum > maximum:
        st.warning("Las horas mínimas no pueden ser superiores a las horas máximas.")
        return

    st.markdown("#### Reglas de descanso de fin de semana")
    help_text("Introduce por teclado el número mínimo exigido en el periodo analizado. Un valor 0 desactiva esa regla.")
    rule_cols = st.columns(3)
    required_weekends = int(rule_cols[0].number_input(
        "Mínimo de fines de semana completos libres", min_value=0, value=1, step=1,
        key="weekend_required_full",
    ))
    required_saturdays = int(rule_cols[1].number_input(
        "Mínimo de sábados libres", min_value=0, value=1, step=1,
        key="weekend_required_saturday",
    ))
    required_sundays = int(rule_cols[2].number_input(
        "Mínimo de domingos libres", min_value=0, value=1, step=1,
        key="weekend_required_sunday",
    ))
    st.caption(
        f"Regla activa: ≥ {required_weekends} fin(es) de semana completo(s), "
        f"≥ {required_saturdays} sábado(s) y ≥ {required_sundays} domingo(s) libres."
    )

    filtered = monthly.loc[
        monthly["applicableWorkingHours"].between(minimum, maximum, inclusive="both")
    ].copy()
    if filtered.empty:
        st.warning("No hay empleados que cumplan el rango contractual seleccionado.")
        return

    keys = filtered[["id_tienda", "personId", "applicableWorkingHours"]].drop_duplicates(
        ["id_tienda", "personId"]
    )
    weekends = weekends.merge(keys, on=["id_tienda", "personId"], how="inner") if not weekends.empty else weekends
    employees = filtered.groupby(["id_tienda", "personId"], as_index=False).agg(
        applicableWorkingHours=("applicableWorkingHours", "max"),
        fines_semana_libres=("fines_semana_libres", "sum"),
        sabados_libres=("sabados_libres", "sum"),
        domingos_libres=("domingos_libres", "sum"),
    )
    employees = apply_weekend_rule_thresholds(
        employees, required_weekends, required_saturdays, required_sundays
    )
    fail_any = employees["incumple_alguna_regla"]
    fail_weekend = employees["incumple_fin_semana"]
    fail_sat = employees["incumple_sabado"]
    fail_sun = employees["incumple_domingo"]

    cols = st.columns(5)
    kpi(cols[0], "Empleados analizados", fmt(len(employees)), f"Contrato entre {fmt(minimum, 0)} y {fmt(maximum, 0)} h", "blue")
    kpi(cols[1], "Con alguna incidencia", fmt(int(fail_any.sum())), pct_text(pct(fail_any.sum(), len(employees))), "red" if fail_any.any() else "green")
    kpi(cols[2], "Incumplen fines completos", fmt(int(fail_weekend.sum())), f"Mínimo activo: {required_weekends}", "red" if fail_weekend.any() else "green")
    kpi(cols[3], "Incumplen sábados", fmt(int(fail_sat.sum())), f"Mínimo activo: {required_saturdays}", "red" if fail_sat.any() else "green")
    kpi(cols[4], "Incumplen domingos", fmt(int(fail_sun.sum())), f"Mínimo activo: {required_sundays}", "red" if fail_sun.any() else "green")

    if not weekends.empty:
        st.markdown("#### Rotación por fin de semana")
        rotation = weekends.groupby(["inicio_fin_semana", "Fin de semana"], as_index=False).agg(
            fin_semana_completo=("fin_semana_libre", "sum"),
            sabado_libre=("sabado_libre", "sum"),
            domingo_libre=("domingo_libre", "sum"),
        ).sort_values("inicio_fin_semana")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["fin_semana_completo"], mode="lines+markers", name="Fin de semana completo"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["sabado_libre"], mode="lines+markers", name="Sábado libre"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["domingo_libre"], mode="lines+markers", name="Domingo libre"))
        fig.update_layout(height=390, xaxis_title="Fin de semana", yaxis_title="Empleados libres", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Mapa empleado-fin de semana")
        contract_text = weekends["applicableWorkingHours"].map(lambda value: f"{value:g}" if pd.notna(value) else "—")
        weekends["Empleado"] = weekends["id_tienda"].astype(str) + " · " + weekends["personId"].astype(str) + " · " + contract_text + " h"
        weekends["dias_libres"] = weekends["sabado_libre"].astype(int) + weekends["domingo_libre"].astype(int)
        order = weekends[["inicio_fin_semana", "Fin de semana"]].drop_duplicates().sort_values("inicio_fin_semana")["Fin de semana"].tolist()
        matrix = weekends.pivot_table(index="Empleado", columns="Fin de semana", values="dias_libres", aggfunc="first").reindex(columns=order)
        fig = go.Figure(go.Heatmap(
            z=matrix.to_numpy(), x=matrix.columns, y=matrix.index, zmin=0, zmax=2, ygap=1,
            colorscale=[[0,"#cbd5e1"],[0.49,"#cbd5e1"],[0.5,"#93c5fd"],[0.74,"#93c5fd"],[0.75,"#1d4ed8"],[1,"#1d4ed8"]],
            colorbar={"tickvals":[0,1,2],"ticktext":["0 días","1 día","2 días"]},
        ))
        fig.update_layout(height=min(900, max(340, 130 + 23 * len(matrix))), plot_bgcolor="#000000")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Incidencias según las reglas introducidas")
    help_text("Las cuatro pestañas se recalculan inmediatamente al cambiar cualquiera de los tres mínimos.")
    diagnostic_tabs = st.tabs([
        f"Todas ({int(fail_any.sum())})",
        f"Fines completos ({int(fail_weekend.sum())})",
        f"Sábados ({int(fail_sat.sum())})",
        f"Domingos ({int(fail_sun.sum())})",
    ])

    def show_rule_table(mask, empty_message):
        data = employees.loc[mask].copy()
        if data.empty:
            st.info(empty_message)
            return
        data["Incumplimientos"] = data.apply(
            lambda row: ", ".join(label for condition, label in [
                (row.incumple_fin_semana, f"Fines completos < {required_weekends}"),
                (row.incumple_sabado, f"Sábados < {required_saturdays}"),
                (row.incumple_domingo, f"Domingos < {required_sundays}"),
            ] if condition), axis=1,
        )
        view = data.rename(columns={
            "id_tienda":"Tienda", "personId":"Empleado", "applicableWorkingHours":"Horas contrato",
            "fines_semana_libres":"Fines completos libres", "sabados_libres":"Sábados libres",
            "domingos_libres":"Domingos libres",
        })
        wfv_dataframe(
            view[["Tienda", "Empleado", "Horas contrato", "Fines completos libres", "Sábados libres", "Domingos libres", "Incumplimientos"]],
            hide_index=True, use_container_width=True,
        )

    with diagnostic_tabs[0]:
        show_rule_table(fail_any, "Todos los empleados cumplen las tres reglas activas.")
    with diagnostic_tabs[1]:
        show_rule_table(fail_weekend, "Todos los empleados cumplen el mínimo de fines de semana completos.")
    with diagnostic_tabs[2]:
        show_rule_table(fail_sat, "Todos los empleados cumplen el mínimo de sábados libres.")
    with diagnostic_tabs[3]:
        show_rule_table(fail_sun, "Todos los empleados cumplen el mínimo de domingos libres.")

    st.markdown("#### Resumen empleado-mes")
    alerts_only = st.checkbox("Mostrar solo empleado-mes con alguna incidencia", value=True, key="weekend_only_alerts")
    view = filtered.copy()
    view["incumple_fin_semana"] = view["fines_semana_libres"].lt(required_weekends)
    view["incumple_sabado"] = view["sabados_libres"].lt(required_saturdays)
    view["incumple_domingo"] = view["domingos_libres"].lt(required_sundays)
    if alerts_only:
        view = view.loc[view[["incumple_fin_semana", "incumple_sabado", "incumple_domingo"]].any(axis=1)]
    view["Alerta"] = view.apply(
        lambda row: ", ".join(label for condition, label in [
            (row.incumple_fin_semana, f"Fines completos < {required_weekends}"),
            (row.incumple_sabado, f"Sábados < {required_saturdays}"),
            (row.incumple_domingo, f"Domingos < {required_sundays}"),
        ] if condition) or "Sin alertas", axis=1,
    )
    view = view.rename(columns={
        "applicableWorkingHours":"Horas contrato", "fines_semana_libres":"Fines de semana libres",
        "fines_semana_evaluables":"Fines de semana evaluables", "sabados_libres":"Sábados libres",
        "sabados_evaluables":"Sábados evaluables", "domingos_libres":"Domingos libres",
        "domingos_evaluables":"Domingos evaluables",
    })
    columns = ["Mes", "id_tienda", "personId", "Horas contrato", "Fines de semana libres", "Fines de semana evaluables", "Sábados libres", "Sábados evaluables", "Domingos libres", "Domingos evaluables", "Alerta"]
    wfv_dataframe(view[columns], hide_index=True, use_container_width=True)
'''


def apply_review_iteration_support(source: str) -> str:
    import_marker = "from validator_engine import ("
    if import_marker not in source:
        raise RuntimeError("No se encontró el bloque de importaciones del dashboard.")
    source = source.replace(
        import_marker,
        "from review_iteration_dashboard import (\n"
        "    apply_weekend_rule_thresholds,\n"
        "    build_contract_lookup,\n"
        "    restrict_to_active_planning_weeks,\n"
        ")\n\n" + import_marker,
        1,
    )

    normalise_marker = "        frames = normalise_frames(frames)"
    if normalise_marker not in source:
        raise RuntimeError("No se encontró la normalización de frames esperada.")
    source = source.replace(
        normalise_marker,
        normalise_marker + "\n        frames, active_data_dates = restrict_to_active_planning_weeks(frames, result.data_dates)",
        1,
    )

    source = source.replace(
        'week_starts = sorted({pd.Timestamp(day).to_period("W-SUN").start_time.normalize() for day in result.data_dates})',
        'week_starts = sorted({pd.Timestamp(day).to_period("W-SUN").start_time.normalize() for day in active_data_dates})',
        1,
    )
    source = source.replace(
        'filtered_data_dates = set(result.data_dates)',
        'filtered_data_dates = set(active_data_dates)',
        1,
    )

    store_marker = 'store_id = (result.source_data.get("store") or {}).get("id", "Sin identificar")'
    if store_marker not in source:
        raise RuntimeError("No se encontró el punto de configuración de tablas.")
    source = source.replace(
        store_marker,
        'WFV_CONTRACT_LOOKUP = build_contract_lookup(frames)\n' + store_marker,
        1,
    )

    tabs_marker = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])'
    if tabs_marker not in source:
        raise RuntimeError("No se encontró el bloque de pestañas esperado.")
    source = source.replace(tabs_marker, DASHBOARD_OVERRIDES.rstrip() + "\n\n" + tabs_marker, 1)

    # Route every dataframe through the presentation helper. This preserves existing
    # tables while adding contract hours and the requested default sorting.
    source = source.replace("st.dataframe(", "wfv_dataframe(")
    return source
