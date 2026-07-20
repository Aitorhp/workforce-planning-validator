from __future__ import annotations

import re


def apply_extensions(source: str) -> str:
    helpers = r'''
def prepare_weekend_analysis(shifts, weekly, data_dates):
    if weekly.empty or not data_dates:
        return pd.DataFrame(), pd.DataFrame()
    dates = pd.to_datetime(sorted(data_dates))
    date_set = set(dates)
    employees = weekly[["id_tienda", "personId", "applicableWorkingHours"]].copy()
    employees["applicableWorkingHours"] = pd.to_numeric(employees["applicableWorkingHours"], errors="coerce")
    employees = employees.sort_values("applicableWorkingHours").drop_duplicates(["id_tienda", "personId"], keep="last")
    worked = set()
    if not shifts.empty:
        shift_days = shifts[["id_tienda", "personId", "day"]].copy()
        shift_days["day"] = pd.to_datetime(shift_days["day"])
        worked = set(zip(shift_days["id_tienda"], shift_days["personId"], shift_days["day"]))
    months = sorted({(day.year, day.month) for day in dates})
    monthly_rows, weekend_rows = [], []
    for employee in employees.itertuples(index=False):
        for year, month in months:
            month_dates = [day for day in dates if day.year == year and day.month == month]
            saturdays = [day for day in month_dates if day.weekday() == 5]
            sundays = [day for day in month_dates if day.weekday() == 6]
            complete = [(sat, sat + pd.Timedelta(days=1)) for sat in saturdays if sat + pd.Timedelta(days=1) in date_set]
            free_sat = sum((employee.id_tienda, employee.personId, day) not in worked for day in saturdays)
            free_sun = sum((employee.id_tienda, employee.personId, day) not in worked for day in sundays)
            free_weekends = 0
            for sat, sun in complete:
                sat_free = (employee.id_tienda, employee.personId, sat) not in worked
                sun_free = (employee.id_tienda, employee.personId, sun) not in worked
                free_weekends += int(sat_free and sun_free)
                weekend_rows.append({
                    "id_tienda": employee.id_tienda, "personId": employee.personId,
                    "applicableWorkingHours": employee.applicableWorkingHours,
                    "Mes": f"{year}-{month:02d}", "inicio_fin_semana": sat,
                    "Fin de semana": f"{sat:%d/%m} - {sun:%d/%m}",
                    "sabado_libre": sat_free, "domingo_libre": sun_free,
                    "fin_semana_libre": sat_free and sun_free,
                })
            monthly_rows.append({
                "id_tienda": employee.id_tienda, "personId": employee.personId,
                "applicableWorkingHours": employee.applicableWorkingHours,
                "Mes": f"{year}-{month:02d}",
                "fines_semana_evaluables": len(complete), "fines_semana_libres": free_weekends,
                "sabados_evaluables": len(saturdays), "sabados_libres": free_sat,
                "domingos_evaluables": len(sundays), "domingos_libres": free_sun,
            })
    return pd.DataFrame(monthly_rows), pd.DataFrame(weekend_rows)


def render_rules_panel():
    with st.sidebar.expander("Reglas activas", expanded=True):
        st.caption("Valores vigentes en modo lectura. La interfaz queda preparada para una futura parametrizacion.")
        st.number_input("Maximo de dias consecutivos", value=float(MAX_CONSECUTIVE_DAYS), disabled=True, key="rule_days_display")
        st.number_input("Duracion minima de turno (h)", value=float(MIN_SHIFT_HOURS), disabled=True, key="rule_min_shift_display")
        st.number_input("Duracion maxima de turno (h)", value=float(MAX_SHIFT_HOURS), disabled=True, key="rule_max_shift_display")
        st.number_input("Descanso minimo entre jornadas (h)", value=float(MIN_REST_HOURS), disabled=True, key="rule_rest_display")
        st.caption("Horas semanales: comparacion con applicableWorkingHours y tolerancia de 0,01 h.")


def render_weekends(frames, data_dates):
    st.subheader("Fines de semana y rotacion de descansos")
    help_text("Un fin de semana libre exige no trabajar ni el sabado ni el domingo. Sabados y domingos libres tambien se cuentan por separado, siempre por empleado y mes.")
    monthly, weekends = prepare_weekend_analysis(frames["shifts"], frames["weekly"], data_dates)
    if monthly.empty:
        st.warning("No hay informacion suficiente para calcular fines de semana.")
        return
    max_contract = float(monthly["applicableWorkingHours"].dropna().max()) if monthly["applicableWorkingHours"].notna().any() else 40.0
    minimum = st.number_input("Horas contractuales minimas", min_value=0.0, max_value=max(80.0, max_contract), value=30.0, step=1.0, help="Se aplica a todos los indicadores, graficos y tablas.")
    filtered = monthly.loc[monthly["applicableWorkingHours"].ge(minimum)].copy()
    if filtered.empty:
        st.warning("No hay empleados que cumplan el filtro contractual.")
        return
    employee_keys = filtered[["id_tienda", "personId"]].drop_duplicates()
    weekends = weekends.merge(employee_keys, on=["id_tienda", "personId"], how="inner") if not weekends.empty else weekends
    per_employee = filtered.groupby(["id_tienda", "personId"], as_index=False).agg(
        fines_semana_libres=("fines_semana_libres", "sum"), sabados_libres=("sabados_libres", "sum"), domingos_libres=("domingos_libres", "sum")
    )
    no_weekend = per_employee["fines_semana_libres"].eq(0)
    no_sat = per_employee["sabados_libres"].eq(0)
    no_sun = per_employee["domingos_libres"].eq(0)
    cols = st.columns(5)
    kpi(cols[0], "Empleados analizados", fmt(len(per_employee)), f"Contrato >= {fmt(minimum, 0)} h", "blue")
    kpi(cols[1], "Sin fin de semana libre", fmt(int(no_weekend.sum())), pct_text(pct(no_weekend.sum(), len(per_employee))), "red" if no_weekend.any() else "green")
    kpi(cols[2], "Sin sabado libre", fmt(int(no_sat.sum())), pct_text(pct(no_sat.sum(), len(per_employee))), "red" if no_sat.any() else "green")
    kpi(cols[3], "Sin domingo libre", fmt(int(no_sun.sum())), pct_text(pct(no_sun.sum(), len(per_employee))), "red" if no_sun.any() else "green")
    kpi(cols[4], "Media fines de semana libres", fmt(filtered["fines_semana_libres"].mean(), 2), "Por empleado-mes", "purple")
    if not weekends.empty:
        st.markdown("#### Rotacion de descansos por fin de semana")
        rotation = weekends.groupby(["inicio_fin_semana", "Fin de semana"], as_index=False).agg(
            fin_semana_completo=("fin_semana_libre", "sum"), sabado_libre=("sabado_libre", "sum"), domingo_libre=("domingo_libre", "sum")
        ).sort_values("inicio_fin_semana")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["fin_semana_completo"], mode="lines+markers", name="Fin de semana completo"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["sabado_libre"], mode="lines+markers", name="Sabado libre"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["domingo_libre"], mode="lines+markers", name="Domingo libre"))
        fig.update_layout(height=390, xaxis_title="Fin de semana", yaxis_title="Empleados libres", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Mapa empleado-fin de semana")
        weekends["Empleado"] = weekends["id_tienda"].astype(str) + " · " + weekends["personId"].astype(str)
        weekends["dias_libres"] = weekends["sabado_libre"].astype(int) + weekends["domingo_libre"].astype(int)
        order = weekends[["inicio_fin_semana", "Fin de semana"]].drop_duplicates().sort_values("inicio_fin_semana")["Fin de semana"].tolist()
        matrix = weekends.pivot_table(index="Empleado", columns="Fin de semana", values="dias_libres", aggfunc="first").reindex(columns=order)
        labels = {0: "Trabaja sabado y domingo", 1: "Un dia libre", 2: "Fin de semana completo libre"}
        text = [["" if pd.isna(value) else labels[int(value)] for value in row] for row in matrix.to_numpy()]
        fig = go.Figure(go.Heatmap(z=matrix.to_numpy(), x=matrix.columns, y=matrix.index, zmin=0, zmax=2, colorscale=[[0, "#cbd5e1"], [0.49, "#cbd5e1"], [0.5, "#93c5fd"], [0.74, "#93c5fd"], [0.75, "#1d4ed8"], [1, "#1d4ed8"]], text=text, hovertemplate="%{y}<br>%{x}<br>%{text}<extra></extra>"))
        fig.update_layout(height=min(900, max(340, 130 + 23 * len(matrix))))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Resumen empleado-mes")
    alerts_only = st.checkbox("Mostrar solo empleado-mes con algun contador a cero", value=True, key="weekend_only_alerts")
    view = filtered.copy()
    if alerts_only:
        view = view.loc[view[["fines_semana_libres", "sabados_libres", "domingos_libres"]].eq(0).any(axis=1)]
    view["Alerta"] = view.apply(lambda row: ", ".join(label for condition, label in [(row.fines_semana_libres == 0, "Sin fin de semana libre"), (row.sabados_libres == 0, "Sin sabado libre"), (row.domingos_libres == 0, "Sin domingo libre")] if condition) or "Sin alertas", axis=1)
    view = view.sort_values(["Alerta", "Mes", "personId"]).rename(columns={"applicableWorkingHours": "Horas contrato", "fines_semana_libres": "Fines de semana libres", "fines_semana_evaluables": "Fines de semana evaluables", "sabados_libres": "Sabados libres", "sabados_evaluables": "Sabados evaluables", "domingos_libres": "Domingos libres", "domingos_evaluables": "Domingos evaluables"})
    columns = ["Mes", "id_tienda", "personId", "Horas contrato", "Fines de semana libres", "Fines de semana evaluables", "Sabados libres", "Sabados evaluables", "Domingos libres", "Domingos evaluables", "Alerta"]
    st.dataframe(view[columns], hide_index=True, use_container_width=True)
'''
    source = source.replace("\ndef render_summary(frames):", helpers.rstrip() + "\n\n\ndef render_summary(frames):")
    source = source.replace('st.subheader("Ausencias y fines de semana")', 'st.subheader("Ausencias")')
    source = source.replace(
        'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias y fines de semana", "Metodologia"])',
        'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])',
    )
    source = source.replace("with tabs[5]: render_absences(frames)\nwith tabs[6]:", "with tabs[5]: render_absences(frames)\nwith tabs[6]: render_weekends(frames, filtered_data_dates)\nwith tabs[7]:")
    source = source.replace('st.sidebar.caption(f"Fichero: {uploaded.name}")', 'st.sidebar.caption(f"Fichero: {uploaded.name}")\nrender_rules_panel()')
    return source
