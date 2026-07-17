from __future__ import annotations

import re
from pathlib import Path

source = Path("app.py").read_text(encoding="utf-8")

PREP = r'''
def prepare_weekly_detail(weekly):
    evaluable = weekly.loc[weekly["estado_planificacion"].isin(["COINCIDE", "FALTAN HORAS", "EXCESO HORAS"])].copy()
    non_evaluable = weekly.loc[~weekly["estado_planificacion"].isin(["COINCIDE", "FALTAN HORAS", "EXCESO HORAS"])].copy()
    if evaluable.empty:
        return evaluable, non_evaluable
    for column in ["applicableWorkingHours", "horas_planificadas", "horas_no_planificadas_hasta_contrato", "horas_planificadas_en_exceso", "dias_ausencia_sin_turno"]:
        evaluable[column] = pd.to_numeric(evaluable[column], errors="coerce").fillna(0.0)
    evaluable["Semana"] = evaluable.apply(lambda row: f"{int(row.ano_iso)}-S{int(row.semana_iso):02d}", axis=1)
    evaluable["Empleado"] = evaluable["id_tienda"].astype(str) + " · " + evaluable["personId"].astype(str)
    evaluable["desviacion_horas"] = evaluable["horas_planificadas"] - evaluable["applicableWorkingHours"]
    evaluable["cobertura_pct"] = evaluable["horas_planificadas"].div(evaluable["applicableWorkingHours"].where(evaluable["applicableWorkingHours"].ne(0))) * 100
    evaluable["contexto_ausencia"] = "No aplica"
    deficit = evaluable["estado_planificacion"].eq("FALTAN HORAS")
    evaluable.loc[deficit & evaluable["dias_ausencia_sin_turno"].gt(0), "contexto_ausencia"] = "Con ausencia registrada"
    evaluable.loc[deficit & evaluable["dias_ausencia_sin_turno"].eq(0), "contexto_ausencia"] = "Sin ausencia registrada"
    evaluable.loc[evaluable["ausente_todo_el_periodo"].eq("SI"), "contexto_ausencia"] = "Ausente todo el periodo"
    return evaluable, non_evaluable


def prepare_weekly_totals(detail):
    return detail.groupby(["ano_iso", "semana_iso", "inicio_semana", "fin_semana", "Semana"], as_index=False).agg(
        horas_contrato=("applicableWorkingHours", "sum"),
        horas_planificadas=("horas_planificadas", "sum"),
        horas_faltantes=("horas_no_planificadas_hasta_contrato", "sum"),
        horas_exceso=("horas_planificadas_en_exceso", "sum"),
    ).sort_values(["ano_iso", "semana_iso"])


def prepare_daily_coverage(shifts, data_dates):
    if data_dates:
        dates = pd.to_datetime(sorted(data_dates))
    elif not shifts.empty:
        dates = pd.date_range(shifts["day"].min(), shifts["day"].max(), freq="D")
    else:
        return pd.DataFrame()
    base = pd.DataFrame({"day": dates})
    if shifts.empty:
        grouped = pd.DataFrame(columns=["day", "horas_planificadas", "empleados_planificados", "turnos", "duracion_media"])
    else:
        grouped = shifts.groupby("day", as_index=False).agg(
            horas_planificadas=("horas_totales", "sum"),
            empleados_planificados=("personId", "nunique"),
            turnos=("personId", "size"),
            duracion_media=("horas_totales", "mean"),
        )
    daily = base.merge(grouped, on="day", how="left").fillna(0.0)
    daily["weekday"] = daily["day"].dt.weekday
    daily["Dia"] = daily["weekday"].map(dict(enumerate(["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])))
    daily["week_start"] = daily["day"] - pd.to_timedelta(daily["weekday"], unit="D")
    daily["week_end"] = daily["week_start"] + pd.Timedelta(days=6)
    daily["Semana calendario"] = daily.apply(lambda row: f"{row.week_start:%d/%m} - {row.week_end:%d/%m}", axis=1)
    return daily.sort_values("day")
'''

WEEKLY = r'''
def render_weekly(frames):
    weekly = frames["weekly"]
    st.subheader("Horas contractuales vs. horas planificadas")
    help_text("La unidad de analisis es empleado-semana. Los excesos no compensan deficits de otras semanas o personas. Las ausencias solo aportan contexto y nunca se convierten en horas planificadas.")
    if weekly.empty:
        st.warning("No hay registros semanales.")
        return
    detail, non_evaluable = prepare_weekly_detail(weekly)
    if detail.empty:
        st.warning("No hay empleado-semanas evaluables: se necesitan siete dias cubiertos y horas contractuales numericas.")
        return
    summary = prepare_weekly_totals(detail)
    exact = detail["estado_planificacion"].eq("COINCIDE")
    deficit = detail["estado_planificacion"].eq("FALTAN HORAS")
    excess = detail["estado_planificacion"].eq("EXCESO HORAS")
    with_absence = deficit & detail["dias_ausencia_sin_turno"].gt(0)
    cols = st.columns(6)
    kpi(cols[0], "Empleado-semanas evaluables", fmt(len(detail)), f"{len(non_evaluable)} no evaluables", "blue")
    kpi(cols[1], "Coinciden con contrato", fmt(int(exact.sum())), pct_text(pct(exact.sum(), len(detail))), "green")
    kpi(cols[2], "Semanas con deficit", fmt(int(deficit.sum())), f"{detail.loc[deficit, 'Empleado'].nunique()} empleados", "red")
    kpi(cols[3], "Horas no planificadas", f"{fmt(detail.loc[deficit, 'horas_no_planificadas_hasta_contrato'].sum(), 1)} h", "Suma de deficits semanales", "red")
    kpi(cols[4], "Semanas con exceso", fmt(int(excess.sum())), f"{fmt(detail.loc[excess, 'horas_planificadas_en_exceso'].sum(), 1)} h", "amber")
    kpi(cols[5], "Deficits con ausencia", fmt(int(with_absence.sum())), pct_text(pct(with_absence.sum(), deficit.sum())), "purple")
    if deficit.any():
        top = detail.loc[deficit].sort_values("horas_no_planificadas_hasta_contrato", ascending=False).iloc[0]
        week = summary.sort_values("horas_faltantes", ascending=False).iloc[0]
        st.warning(f"Prioridad: {top.personId} en {top.Semana} tiene el mayor deficit individual ({fmt(top.horas_no_planificadas_hasta_contrato, 1)} h). La semana mas critica es {week.Semana} ({fmt(week.horas_faltantes, 1)} h).")
    else:
        st.success("Todas las empleado-semanas evaluables alcanzan o superan el contrato.")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("#### Contrato y planificacion por semana")
        help_text("Vista de capacidad total. Puede ocultar compensaciones entre personas, por eso el control principal sigue siendo individual.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=summary["Semana"], y=summary["horas_contrato"], mode="lines+markers", name="Horas de contrato", line={"color": "#475569", "width": 3}))
        fig.add_trace(go.Scatter(x=summary["Semana"], y=summary["horas_planificadas"], mode="lines+markers", name="Horas planificadas", line={"color": "#2563eb", "width": 3}))
        fig.update_layout(height=390, yaxis_title="Horas", xaxis_title="Semana", hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### Magnitud de los desajustes")
        help_text("Deficit y exceso aparecen en barras separadas, sin apilar ni compensar.")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary["Semana"], y=summary["horas_faltantes"], name="Horas faltantes", marker_color="#dc3545"))
        fig.add_trace(go.Bar(x=summary["Semana"], y=summary["horas_exceso"], name="Horas en exceso", marker_color="#f59e0b"))
        fig.update_layout(barmode="group", height=390, yaxis_title="Horas", xaxis_title="Semana", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Mapa de desviacion empleado-semana")
    help_text("Rojo significa deficit, blanco coincidencia y ambar exceso. Cada celda son horas planificadas menos horas de contrato.")
    only_deviations = st.checkbox("Mostrar solo empleados con alguna desviacion", value=True, key="weekly_heatmap_deviations")
    pivot = detail.pivot_table(index="Empleado", columns="Semana", values="desviacion_horas", aggfunc="first").reindex(columns=summary["Semana"].tolist())
    if only_deviations:
        pivot = pivot.loc[pivot.abs().max(axis=1).gt(0.01)]
    if pivot.empty:
        st.success("No hay desviaciones con el filtro actual.")
    else:
        pivot = pivot.loc[pivot.min(axis=1).sort_values().index]
        max_abs = max(float(pivot.abs().max().max()), 1.0)
        text = [["" if pd.isna(value) else f"{value:+.1f}" for value in row] for row in pivot.to_numpy()]
        fig = go.Figure(go.Heatmap(z=pivot.to_numpy(), x=pivot.columns, y=pivot.index, zmin=-max_abs, zmax=max_abs, zmid=0, colorscale=[[0, "#b91c1c"], [0.5, "#f8fafc"], [1, "#d97706"]], text=text, texttemplate="%{text}", colorbar={"title": "Desviacion h"}, hovertemplate="%{y}<br>%{x}<br>%{z:+.1f} h<extra></extra>"))
        fig.update_layout(height=min(850, max(320, 130 + 24 * len(pivot))), margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Detalle empleado-semana")
    help_text("Tabla operativa al nivel correcto. La ausencia es una pista contextual, no una imputacion de horas.")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    available = [status for status in ["COINCIDE", "FALTAN HORAS", "EXCESO HORAS"] if status in detail["estado_planificacion"].unique()]
    default = [status for status in ["FALTAN HORAS", "EXCESO HORAS"] if status in available] or available
    statuses = c1.multiselect("Estado", available, default, key="weekly_status_filter")
    selected_week = c2.selectbox("Semana", ["Todas"] + summary["Semana"].tolist(), key="weekly_week_filter")
    employee = c3.text_input("Buscar empleado", placeholder="personId", key="weekly_employee_filter")
    view = detail.loc[detail["estado_planificacion"].isin(statuses)].copy() if statuses else detail.iloc[0:0].copy()
    if selected_week != "Todas":
        view = view.loc[view["Semana"].eq(selected_week)]
    if employee.strip():
        view = view.loc[view["personId"].astype(str).str.contains(employee.strip(), case=False, na=False)]
    priority = {"FALTAN HORAS": 0, "EXCESO HORAS": 1, "COINCIDE": 2}
    view["_priority"] = view["estado_planificacion"].map(priority)
    view = view.sort_values(["_priority", "horas_no_planificadas_hasta_contrato", "horas_planificadas_en_exceso"], ascending=[True, False, False])
    view = view.rename(columns={"applicableWorkingHours": "Horas contrato", "horas_planificadas": "Horas planificadas", "desviacion_horas": "Desviacion (h)", "cobertura_pct": "Cobertura (%)", "estado_planificacion": "Estado", "horas_no_planificadas_hasta_contrato": "Horas faltantes", "horas_planificadas_en_exceso": "Horas en exceso", "dias_ausencia_sin_turno": "Dias ausencia sin turno", "tipos_ausencia": "Tipos ausencia", "contexto_ausencia": "Contexto ausencia"})
    columns = ["Semana", "id_tienda", "personId", "Horas contrato", "Horas planificadas", "Desviacion (h)", "Cobertura (%)", "Estado", "Horas faltantes", "Horas en exceso", "Dias ausencia sin turno", "Tipos ausencia", "Contexto ausencia"]
    st.dataframe(view[columns], hide_index=True, use_container_width=True, column_config={"Horas contrato": st.column_config.NumberColumn(format="%.1f h"), "Horas planificadas": st.column_config.NumberColumn(format="%.1f h"), "Desviacion (h)": st.column_config.NumberColumn(format="%+.1f h"), "Cobertura (%)": st.column_config.NumberColumn(format="%.1f %%"), "Horas faltantes": st.column_config.NumberColumn(format="%.1f h"), "Horas en exceso": st.column_config.NumberColumn(format="%.1f h")})
    if not non_evaluable.empty:
        with st.expander(f"Ver {len(non_evaluable)} registros no evaluables"):
            st.caption("Semanas parciales o contratos no numericos.")
            st.dataframe(non_evaluable[["inicio_semana", "fin_semana", "id_tienda", "personId", "dias_cubiertos_fichero", "applicableWorkingHours", "horas_planificadas", "estado_planificacion"]], hide_index=True, use_container_width=True)
'''

COVERAGE = r'''
def render_coverage(frames, data_dates):
    shifts = frames["shifts"]
    st.subheader("Cobertura diaria de la planificacion")
    help_text("Cobertura son las horas WORK planificadas cada fecha. Los dias presentes en el JSON sin trabajo se conservan con cero horas.")
    daily = prepare_daily_coverage(shifts, data_dates)
    if daily.empty:
        st.warning("No hay fechas disponibles para analizar la cobertura.")
        return
    peak = daily.loc[daily["horas_planificadas"].idxmax()]
    active = int(daily["horas_planificadas"].gt(0).sum())
    zero = int(daily["horas_planificadas"].eq(0).sum())
    cols = st.columns(6)
    kpi(cols[0], "Horas planificadas", f"{fmt(daily['horas_planificadas'].sum(), 1)} h", "Total del periodo", "purple")
    kpi(cols[1], "Cobertura media diaria", f"{fmt(daily['horas_planificadas'].mean(), 1)} h", f"Sobre {len(daily)} dias", "blue")
    kpi(cols[2], "Dia de maxima cobertura", f"{fmt(peak.horas_planificadas, 1)} h", f"{peak.day:%d/%m/%Y}", "green")
    kpi(cols[3], "Dias con cobertura", fmt(active), pct_text(pct(active, len(daily))), "green")
    kpi(cols[4], "Dias sin horas", fmt(zero), "Fechas con 0 h", "red" if zero else "green")
    kpi(cols[5], "Empleados por dia", fmt(daily["empleados_planificados"].mean(), 1), "Media diaria", "blue")
    st.markdown("#### Calendario de horas planificadas")
    help_text("Cada celda muestra las horas totales de la tienda. Cero identifica un hueco total de planificacion.")
    order = daily[["week_start", "Semana calendario"]].drop_duplicates().sort_values("week_start")["Semana calendario"].tolist()
    calendar = daily.pivot(index="Semana calendario", columns="weekday", values="horas_planificadas").reindex(index=order, columns=range(7)).fillna(0.0)
    calendar.columns = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    fig = go.Figure(go.Heatmap(z=calendar.to_numpy(), x=calendar.columns, y=calendar.index, zmin=0, zmax=max(float(calendar.max().max()), 1.0), colorscale=[[0, "#f1f5f9"], [0.01, "#dbeafe"], [0.55, "#60a5fa"], [1, "#1d4ed8"]], text=[[f"{value:.1f} h" for value in row] for row in calendar.to_numpy()], texttemplate="%{text}", colorbar={"title": "Horas"}, hovertemplate="%{y}<br>%{x}<br>%{z:.1f} h<extra></extra>"))
    fig.update_layout(height=max(300, 120 + 48 * len(calendar)), yaxis_autorange="reversed", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Evolucion diaria de la cobertura")
    help_text("Permite detectar picos, caidas y dias con cero horas.")
    fig = go.Figure(go.Scatter(x=daily["day"], y=daily["horas_planificadas"], mode="lines+markers", line={"color": "#2563eb", "width": 3}, marker={"size": 7}, customdata=daily[["empleados_planificados", "turnos"]].to_numpy(), hovertemplate="%{x|%d/%m/%Y}<br>Horas: %{y:.1f}<br>Empleados: %{customdata[0]:.0f}<br>Turnos: %{customdata[1]:.0f}<extra></extra>"))
    fig.update_layout(height=380, xaxis_title="Fecha", yaxis_title="Horas planificadas", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    left, right = st.columns([1.35, 0.85])
    with left:
        st.markdown("#### Patron medio por dia de la semana")
        help_text("Ayuda a comprobar si la estructura semanal es coherente con la operativa retail esperada.")
        weekday = daily.groupby(["weekday", "Dia"], as_index=False).agg(Horas=("horas_planificadas", "mean"), Empleados=("empleados_planificados", "mean")).sort_values("weekday")
        fig = px.bar(weekday, x="Dia", y="Horas", text_auto=".1f", category_orders={"Dia": ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]}, height=330)
        fig.update_layout(xaxis_title="", yaxis_title="Horas medias", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### Duraciones de turno")
        help_text("Tabla compacta que sustituye al histograma.")
        if shifts.empty:
            st.info("No hay turnos.")
        else:
            table = shifts.assign(**{"Duracion (h)": pd.to_numeric(shifts["horas_totales"], errors="coerce").round(2)}).groupby("Duracion (h)", as_index=False).size().rename(columns={"size": "Turnos"}).sort_values("Duracion (h)")
            table["Peso (%)"] = table["Turnos"] / table["Turnos"].sum() * 100
            st.dataframe(table, hide_index=True, use_container_width=True, height=min(360, 38 * (len(table) + 1)), column_config={"Duracion (h)": st.column_config.NumberColumn(format="%.2f h"), "Peso (%)": st.column_config.NumberColumn(format="%.1f %%")})
            st.caption(f"Fuera de limites: {int(shifts.horas_totales.lt(MIN_SHIFT_HOURS).sum())} por debajo de {MIN_SHIFT_HOURS:g} h y {int(shifts.horas_totales.gt(MAX_SHIFT_HOURS).sum())} por encima de {MAX_SHIFT_HOURS:g} h.")
    with st.expander("Ver detalle diario"):
        view = daily[["day", "Dia", "horas_planificadas", "empleados_planificados", "turnos", "duracion_media"]].rename(columns={"day": "Fecha", "horas_planificadas": "Horas planificadas", "empleados_planificados": "Empleados planificados", "turnos": "Turnos", "duracion_media": "Duracion media"})
        st.dataframe(view, hide_index=True, use_container_width=True, column_config={"Fecha": st.column_config.DateColumn(format="DD/MM/YYYY"), "Horas planificadas": st.column_config.NumberColumn(format="%.1f h"), "Duracion media": st.column_config.NumberColumn(format="%.2f h")})
'''

source = re.sub(r"def prepare_weekly_analysis\(weekly\):.*?(?=\ndef render_summary)", PREP.rstrip(), source, flags=re.S)
source = re.sub(r"def render_weekly\(frames\):.*?(?=\ndef render_shifts)", WEEKLY.rstrip(), source, flags=re.S)
source = re.sub(r"def render_shifts\(frames\):.*?(?=\ndef render_absences)", COVERAGE.rstrip(), source, flags=re.S)
source = source.replace('tabs = st.tabs(["Resumen", "Restricciones", "Horas semanales", "Turnos", "Ausencias y fines de semana", "Metodologia"])', 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Ausencias y fines de semana", "Metodologia"])')
source = source.replace('with tabs[3]: render_shifts(frames)', 'with tabs[3]: render_coverage(frames, result.data_dates)')
exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})
