from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

import pandas as pd


def _normalise_dates(values: Iterable[Any]) -> list[pd.Timestamp]:
    dates = pd.to_datetime(list(values), errors="coerce")
    return sorted({pd.Timestamp(value).normalize() for value in dates if pd.notna(value)})


def _worked_days(shifts: pd.DataFrame) -> set[tuple[str, str, pd.Timestamp]]:
    required = {"id_tienda", "personId", "day"}
    if shifts is None or shifts.empty or not required.issubset(shifts.columns):
        return set()
    data = shifts[["id_tienda", "personId", "day"]].copy()
    data["day"] = pd.to_datetime(data["day"], errors="coerce").dt.normalize()
    data = data.dropna(subset=["day"])
    return {
        (str(row.id_tienda), str(row.personId), pd.Timestamp(row.day).normalize())
        for row in data.itertuples(index=False)
    }


def _weekend_start(day: pd.Timestamp) -> pd.Timestamp:
    day = pd.Timestamp(day).normalize()
    if day.weekday() == 5:
        return day
    if day.weekday() == 6:
        return day - pd.Timedelta(days=1)
    raise ValueError("Weekend resources must be Saturday or Sunday")


def _build_weekend_states(
    shifts: pd.DataFrame,
    store_id: Any,
    person_id: Any,
    scope_dates: Iterable[Any],
    all_dates: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Build exact free-day resources grouped by weekend.

    ``scope_dates`` controls which individual Saturdays/Sundays can satisfy the
    Saturday, Sunday and flexible-day rules. ``all_dates`` is additionally used
    to decide whether a Saturday has an evaluable following Sunday for the full
    weekend rule. This preserves the existing convention that a full weekend is
    anchored on its Saturday.
    """
    scope = _normalise_dates(scope_dates)
    all_days = _normalise_dates(all_dates if all_dates is not None else scope)
    all_set = set(all_days)
    worked = _worked_days(shifts)
    employee_key = (str(store_id), str(person_id))

    states: dict[pd.Timestamp, dict[str, Any]] = {}

    def state_for(start: pd.Timestamp) -> dict[str, Any]:
        if start not in states:
            states[start] = {
                "weekend_start": start,
                "sat_free": False,
                "sun_free": False,
                "full_free": False,
            }
        return states[start]

    for day in scope:
        if day.weekday() not in (5, 6):
            continue
        start = _weekend_start(day)
        state = state_for(start)
        is_free = (employee_key[0], employee_key[1], day) not in worked
        if day.weekday() == 5:
            state["sat_free"] = is_free
        else:
            state["sun_free"] = is_free

    # A full weekend is anchored on a Saturday in scope and requires the next
    # day to exist in the complete evaluable date set and both days to be free.
    for saturday in (day for day in scope if day.weekday() == 5):
        sunday = saturday + pd.Timedelta(days=1)
        if sunday not in all_set:
            continue
        sat_free = (employee_key[0], employee_key[1], saturday) not in worked
        sun_free = (employee_key[0], employee_key[1], sunday) not in worked
        state_for(saturday)["full_free"] = bool(sat_free and sun_free)

    return [states[key] for key in sorted(states)]


def _weekend_options(
    state: dict[str, Any], distinct_flexible_weekends: bool
) -> set[tuple[int, int, int, int]]:
    """Return feasible (full, Saturday, Sunday, flexible) allocations for one weekend."""
    options: set[tuple[int, int, int, int]] = {(0, 0, 0, 0)}

    sat_actions = [(0, 0)]
    if state["sat_free"]:
        sat_actions += [(1, 0), (0, 1)]  # specific Saturday, flexible day
    sun_actions = [(0, 0)]
    if state["sun_free"]:
        sun_actions += [(1, 0), (0, 1)]  # specific Sunday, flexible day

    for sat_specific, sat_flex in sat_actions:
        for sun_specific, sun_flex in sun_actions:
            flex = sat_flex + sun_flex
            if distinct_flexible_weekends and flex > 1:
                continue
            options.add((0, sat_specific, sun_specific, flex))

    if state["full_free"]:
        # A full-weekend allocation consumes both days, so neither day may also
        # satisfy another rule.
        options.add((1, 0, 0, 0))

    return options


def evaluate_weekend_assignment(
    states: list[dict[str, Any]],
    minimum_full_weekends: int = 0,
    minimum_saturdays: int = 0,
    minimum_sundays: int = 0,
    minimum_flexible_days: int = 0,
    distinct_flexible_weekends: bool = False,
) -> dict[str, Any]:
    """Evaluate weekend-rest rules without reusing a calendar day.

    The flexible rule accepts any mix of Saturdays and Sundays. When
    ``distinct_flexible_weekends`` is true, at most one flexible day can be
    allocated from each weekend. Different rules may use different days from
    the same weekend; only the same calendar day is prohibited from reuse.
    """
    required = tuple(
        max(int(value), 0)
        for value in (
            minimum_full_weekends,
            minimum_saturdays,
            minimum_sundays,
            minimum_flexible_days,
        )
    )
    req_full, req_sat, req_sun, req_flex = required

    full_available = sum(bool(state["full_free"]) for state in states)
    sat_available = sum(bool(state["sat_free"]) for state in states)
    sun_available = sum(bool(state["sun_free"]) for state in states)
    if distinct_flexible_weekends:
        flex_available = sum(bool(state["sat_free"] or state["sun_free"]) for state in states)
    else:
        flex_available = sat_available + sun_available

    fail_full = full_available < req_full
    fail_sat = sat_available < req_sat
    fail_sun = sun_available < req_sun
    fail_flex = flex_available < req_flex
    direct_failure = fail_full or fail_sat or fail_sun or fail_flex

    target = required
    combinable = False
    if not direct_failure:
        states_dp: set[tuple[int, int, int, int]] = {(0, 0, 0, 0)}
        for weekend in states:
            next_states: set[tuple[int, int, int, int]] = set()
            for current in states_dp:
                for increment in _weekend_options(weekend, distinct_flexible_weekends):
                    next_states.add(
                        tuple(
                            min(target[index], current[index] + increment[index])
                            for index in range(4)
                        )
                    )
            states_dp = next_states
            if target in states_dp:
                combinable = True
                break
        else:
            combinable = target in states_dp

    fail_combination = (not direct_failure) and (not combinable)
    return {
        "fines_semana_disponibles": int(full_available),
        "sabados_disponibles": int(sat_available),
        "domingos_disponibles": int(sun_available),
        "dias_flexibles_disponibles": int(flex_available),
        "incumple_fin_semana": bool(fail_full),
        "incumple_sabado": bool(fail_sat),
        "incumple_domingo": bool(fail_sun),
        "incumple_sabado_o_domingo": bool(fail_flex),
        "incumple_combinacion": bool(fail_combination),
        "incumple_alguna_regla": bool(direct_failure or fail_combination),
        "reglas_combinables": bool(not direct_failure and combinable),
    }


def evaluate_weekend_rule_table(
    rows: pd.DataFrame,
    shifts: pd.DataFrame,
    data_dates: Iterable[Any],
    minimum_full_weekends: int = 0,
    minimum_saturdays: int = 0,
    minimum_sundays: int = 0,
    minimum_flexible_days: int = 0,
    distinct_flexible_weekends: bool = False,
    period_column: str | None = None,
) -> pd.DataFrame:
    """Attach exact weekend-rule evaluation to employee or employee-period rows."""
    result = rows.copy()
    if result.empty:
        for column in (
            "dias_flexibles_disponibles",
            "incumple_fin_semana",
            "incumple_sabado",
            "incumple_domingo",
            "incumple_sabado_o_domingo",
            "incumple_combinacion",
            "incumple_alguna_regla",
            "reglas_combinables",
        ):
            result[column] = pd.Series(
                dtype=(
                    "bool"
                    if column.startswith("incumple_") or column == "reglas_combinables"
                    else "int64"
                )
            )
        return result

    required = {"id_tienda", "personId"}
    if not required.issubset(result.columns):
        raise ValueError("Weekend rule evaluation requires id_tienda and personId")

    all_dates = _normalise_dates(data_dates)
    evaluations: list[dict[str, Any]] = []
    for row in result.itertuples(index=False):
        scope_dates = all_dates
        if period_column:
            period_value = getattr(row, period_column)
            period = pd.Period(str(period_value), freq="M")
            scope_dates = [
                day
                for day in all_dates
                if day.year == period.year and day.month == period.month
            ]
        states = _build_weekend_states(
            shifts,
            getattr(row, "id_tienda"),
            getattr(row, "personId"),
            scope_dates,
            all_dates,
        )
        evaluations.append(
            evaluate_weekend_assignment(
                states,
                minimum_full_weekends,
                minimum_saturdays,
                minimum_sundays,
                minimum_flexible_days,
                distinct_flexible_weekends,
            )
        )

    evaluation_frame = pd.DataFrame(evaluations, index=result.index)
    for column in evaluation_frame.columns:
        result[column] = evaluation_frame[column]
    return result


DASHBOARD_WEEKEND_OVERRIDE = r'''
def render_weekends(frames, data_dates):
    st.subheader("Fines de semana y rotación de descansos")
    help_text(
        "Las reglas se evalúan sobre días concretos de descanso. Un mismo sábado o domingo no puede "
        "utilizarse para cumplir dos reglas distintas. Si existe alguna asignación válida de los descansos, "
        "el empleado se considera conforme."
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
    help_text(
        "Introduce el mínimo exigido. Un valor 0 desactiva la regla. “Sábados o domingos” admite cualquier "
        "combinación de ambos días; por defecto un fin de semana completo aporta 2 días a esa regla."
    )
    rule_cols = st.columns(4)
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
    required_flexible = int(rule_cols[3].number_input(
        "Mínimo de sábados o domingos libres", min_value=0, value=0, step=1,
        key="weekend_required_flexible",
    ))
    distinct_flexible = st.checkbox(
        "Los días de la regla «sábados o domingos» no pueden pertenecer al mismo fin de semana",
        value=False,
        key="weekend_flexible_distinct_weekends",
    )
    flexible_note = "en fines de semana distintos" if distinct_flexible else "pudiendo coincidir en el mismo fin de semana"
    st.caption(
        f"Reglas activas: ≥ {required_weekends} fin(es) completo(s), ≥ {required_saturdays} sábado(s), "
        f"≥ {required_sundays} domingo(s) y ≥ {required_flexible} sábado(s) o domingo(s), {flexible_note}. "
        "Los días no se reutilizan entre reglas."
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
    employees = evaluate_weekend_rule_table(
        employees, frames["shifts"], data_dates,
        required_weekends, required_saturdays, required_sundays, required_flexible, distinct_flexible,
    )
    fail_any = employees["incumple_alguna_regla"]
    fail_weekend = employees["incumple_fin_semana"]
    fail_sat = employees["incumple_sabado"]
    fail_sun = employees["incumple_domingo"]
    fail_flexible = employees["incumple_sabado_o_domingo"]
    fail_combination = employees["incumple_combinacion"]

    cols = st.columns(6)
    kpi(cols[0], "Empleados analizados", fmt(len(employees)), f"Contrato entre {fmt(minimum, 0)} y {fmt(maximum, 0)} h", "blue")
    kpi(cols[1], "Con alguna incidencia", fmt(int(fail_any.sum())), pct_text(pct(fail_any.sum(), len(employees))), "red" if fail_any.any() else "green")
    kpi(cols[2], "Incumplen fines completos", fmt(int(fail_weekend.sum())), f"Mínimo activo: {required_weekends}", "red" if fail_weekend.any() else "green")
    kpi(cols[3], "Incumplen sábados", fmt(int(fail_sat.sum())), f"Mínimo activo: {required_saturdays}", "red" if fail_sat.any() else "green")
    kpi(cols[4], "Incumplen domingos", fmt(int(fail_sun.sum())), f"Mínimo activo: {required_sundays}", "red" if fail_sun.any() else "green")
    kpi(cols[5], "Incumplen sábado o domingo", fmt(int(fail_flexible.sum())), f"Mínimo activo: {required_flexible}", "red" if fail_flexible.any() else "green")

    if fail_combination.any():
        st.warning(
            f"Hay {int(fail_combination.sum())} empleado(s) cuyos contadores por separado alcanzan los mínimos, "
            "pero no existe una asignación que cumpla todas las reglas sin reutilizar días."
        )

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
    help_text(
        "Las incidencias directas indican que no hay suficientes descansos del tipo requerido. “Combinación” "
        "indica que los contadores aislados alcanzan los mínimos, pero los días disponibles no pueden repartirse "
        "entre todas las reglas sin reutilización."
    )
    diagnostic_tabs = st.tabs([
        f"Todas ({int(fail_any.sum())})",
        f"Fines completos ({int(fail_weekend.sum())})",
        f"Sábados ({int(fail_sat.sum())})",
        f"Domingos ({int(fail_sun.sum())})",
        f"Sáb. o dom. ({int(fail_flexible.sum())})",
        f"Combinación ({int(fail_combination.sum())})",
    ])

    def incident_text(row):
        labels = []
        if row.incumple_fin_semana:
            labels.append(f"Fines completos < {required_weekends}")
        if row.incumple_sabado:
            labels.append(f"Sábados < {required_saturdays}")
        if row.incumple_domingo:
            labels.append(f"Domingos < {required_sundays}")
        if row.incumple_sabado_o_domingo:
            suffix = " en fines distintos" if distinct_flexible else ""
            labels.append(f"Sábados o domingos < {required_flexible}{suffix}")
        if row.incumple_combinacion:
            labels.append("No combinable sin reutilizar días")
        return ", ".join(labels) if labels else "Sin alertas"

    def show_rule_table(mask, empty_message):
        data = employees.loc[mask].copy()
        if data.empty:
            st.info(empty_message)
            return
        data["Incumplimientos"] = data.apply(incident_text, axis=1)
        view = data.rename(columns={
            "id_tienda":"Tienda", "personId":"Empleado", "applicableWorkingHours":"Horas contrato",
            "fines_semana_libres":"Fines completos libres", "sabados_libres":"Sábados libres",
            "domingos_libres":"Domingos libres", "dias_flexibles_disponibles":"Días S/D disponibles",
        })
        wfv_dataframe(
            view[["Tienda", "Empleado", "Horas contrato", "Fines completos libres", "Sábados libres", "Domingos libres", "Días S/D disponibles", "Incumplimientos"]],
            hide_index=True, use_container_width=True,
        )

    with diagnostic_tabs[0]:
        show_rule_table(fail_any, "Todos los empleados cumplen las reglas activas.")
    with diagnostic_tabs[1]:
        show_rule_table(fail_weekend, "Todos los empleados cumplen el mínimo de fines de semana completos.")
    with diagnostic_tabs[2]:
        show_rule_table(fail_sat, "Todos los empleados cumplen el mínimo de sábados libres.")
    with diagnostic_tabs[3]:
        show_rule_table(fail_sun, "Todos los empleados cumplen el mínimo de domingos libres.")
    with diagnostic_tabs[4]:
        show_rule_table(fail_flexible, "Todos los empleados cumplen el mínimo de sábados o domingos libres.")
    with diagnostic_tabs[5]:
        show_rule_table(fail_combination, "No hay conflictos de asignación entre las reglas activas.")

    st.markdown("#### Resumen empleado-mes")
    alerts_only = st.checkbox("Mostrar solo empleado-mes con alguna incidencia", value=True, key="weekend_only_alerts")
    view = evaluate_weekend_rule_table(
        filtered, frames["shifts"], data_dates,
        required_weekends, required_saturdays, required_sundays, required_flexible, distinct_flexible,
        period_column="Mes",
    )
    if alerts_only:
        view = view.loc[view["incumple_alguna_regla"]]
    view["Alerta"] = view.apply(incident_text, axis=1)
    view = view.rename(columns={
        "applicableWorkingHours":"Horas contrato", "fines_semana_libres":"Fines de semana libres",
        "fines_semana_evaluables":"Fines de semana evaluables", "sabados_libres":"Sábados libres",
        "sabados_evaluables":"Sábados evaluables", "domingos_libres":"Domingos libres",
        "domingos_evaluables":"Domingos evaluables", "dias_flexibles_disponibles":"Días S/D disponibles",
    })
    columns = ["Mes", "id_tienda", "personId", "Horas contrato", "Fines de semana libres", "Fines de semana evaluables", "Sábados libres", "Sábados evaluables", "Domingos libres", "Domingos evaluables", "Días S/D disponibles", "Alerta"]
    wfv_dataframe(view[columns], hide_index=True, use_container_width=True)
'''


def apply_weekend_assignment_support(source: str) -> str:
    """Replace only the Streamlit weekend presentation with assignment-aware rules."""
    import_marker = "from validator_engine import ("
    if import_marker not in source:
        raise RuntimeError("No se encontró el bloque de importaciones del dashboard.")
    source = source.replace(
        import_marker,
        "from weekend_assignment_dashboard import evaluate_weekend_rule_table\n\n" + import_marker,
        1,
    )

    tabs_marker = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])'
    pattern = re.compile(
        r"\ndef render_weekends\(frames, data_dates\):.*?(?=\n"
        + re.escape(tabs_marker)
        + r")",
        re.S,
    )
    matches = pattern.findall(source)
    if len(matches) != 1:
        raise RuntimeError(
            f"Se esperaba un único render_weekends configurable y se encontraron {len(matches)}."
        )
    return pattern.sub("\n" + DASHBOARD_WEEKEND_OVERRIDE.rstrip() + "\n\n", source, count=1)
