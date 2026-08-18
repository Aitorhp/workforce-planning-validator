from __future__ import annotations

from typing import Any

import pandas as pd


def prepare_workforce_mix(
    weekly: pd.DataFrame | None,
    store_id: Any | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return one contract row per employee and an aggregated contract mix.

    This helper is presentation-only: it consumes the already calculated
    ``applicableWorkingHours`` from the weekly output and does not recalculate
    contract values.
    """
    required = {"id_tienda", "personId", "applicableWorkingHours"}
    if weekly is None or weekly.empty or not required.issubset(weekly.columns):
        return pd.DataFrame(), pd.DataFrame()

    data = weekly.copy()
    data["applicableWorkingHours"] = pd.to_numeric(
        data["applicableWorkingHours"], errors="coerce"
    )
    data = data.dropna(subset=["applicableWorkingHours"])
    if store_id is not None:
        data = data.loc[data["id_tienda"].astype(str).eq(str(store_id))]
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    if "inicio_semana" in data.columns:
        data["inicio_semana"] = pd.to_datetime(data["inicio_semana"], errors="coerce")
        data = data.sort_values(["id_tienda", "personId", "inicio_semana"])
    else:
        data = data.sort_values(["id_tienda", "personId"])

    employees = data.drop_duplicates(["id_tienda", "personId"], keep="last")[
        ["id_tienda", "personId", "applicableWorkingHours"]
    ].reset_index(drop=True)

    mix = (
        employees.groupby("applicableWorkingHours", as_index=False)
        .size()
        .rename(columns={"size": "Empleados"})
        .sort_values("applicableWorkingHours")
        .reset_index(drop=True)
    )
    total_employees = int(mix["Empleados"].sum())
    mix["Porcentaje plantilla"] = (
        mix["Empleados"] / total_employees * 100.0 if total_employees else 0.0
    )
    mix["Horas contratadas"] = mix["applicableWorkingHours"] * mix["Empleados"]
    total_hours = float(mix["Horas contratadas"].sum())
    mix["Porcentaje horas"] = (
        mix["Horas contratadas"] / total_hours * 100.0 if total_hours else 0.0
    )
    return employees, mix


OLD_WEEKEND_ROTATION = r'''        st.markdown("#### Rotación por fin de semana")
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
'''


NEW_WEEKEND_ROTATION = r'''        st.markdown("#### Rotación por fin de semana")
        rotation = weekends.groupby(["inicio_fin_semana", "Fin de semana"], as_index=False).agg(
            fin_semana_completo=("fin_semana_libre", "sum"),
            sabado_libre=("sabado_libre", "sum"),
            domingo_libre=("domingo_libre", "sum"),
        ).sort_values("inicio_fin_semana")
        total_employees = max(int(len(employees)), 1)
        rotation["porcentaje_plantilla"] = rotation["fin_semana_completo"] / total_employees * 100.0
        rotation["etiqueta_descanso"] = rotation.apply(
            lambda row: f'{int(row["fin_semana_completo"])} empleados · {row["porcentaje_plantilla"]:.0f}%',
            axis=1,
        )

        st.caption("Evolución de descansos por tipo")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["fin_semana_completo"], mode="lines+markers", name="Fin de semana completo"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["sabado_libre"], mode="lines+markers", name="Sábado libre"))
        fig.add_trace(go.Scatter(x=rotation["inicio_fin_semana"], y=rotation["domingo_libre"], mode="lines+markers", name="Domingo libre"))
        fig.update_layout(
            height=255,
            xaxis_title=None,
            yaxis_title="Empleados libres",
            hovermode="x unified",
            margin=dict(l=15, r=15, t=10, b=25),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Magnitud del descanso por fin de semana")
        st.caption(
            "Empleados con sábado y domingo libres en cada fin de semana y peso que representan sobre la plantilla analizada."
        )
        fig_pct = go.Figure(go.Bar(
            x=rotation["Fin de semana"],
            y=rotation["porcentaje_plantilla"],
            text=rotation["etiqueta_descanso"],
            textposition="auto",
            customdata=rotation[["fin_semana_completo"]].to_numpy(),
            hovertemplate="%{x}<br>%{customdata[0]} empleados con fin de semana completo libre<br>%{y:.1f}% de la plantilla<extra></extra>",
        ))
        fig_pct.update_layout(
            height=310,
            xaxis_title="Fin de semana",
            yaxis_title="% de plantilla con fin de semana completo libre",
            yaxis=dict(range=[0, 100], ticksuffix="%"),
            margin=dict(l=15, r=15, t=10, b=35),
            showlegend=False,
        )
        st.plotly_chart(fig_pct, use_container_width=True)
        st.caption(
            f"Base del porcentaje: {len(employees)} empleado(s) incluidos en el rango contractual seleccionado."
        )
'''


MIX_RENDERER = r'''
def render_workforce_mix(frames):
    st.subheader("Mix de plantilla")
    help_text(
        "Distribución informativa de la plantilla según sus horas contractuales. "
        "Se utilizan las horas de contrato ya calculadas en el análisis semanal; esta pestaña no aplica reglas ni genera incidencias."
    )

    all_employees, _ = prepare_workforce_mix(frames.get("weekly"))
    if all_employees.empty:
        st.warning("No hay información contractual suficiente para construir el mix de plantilla.")
        return

    stores = sorted(all_employees["id_tienda"].dropna().astype(str).unique().tolist())
    selected_store = None
    if len(stores) > 1:
        selected_label = st.selectbox(
            "Tienda",
            ["Todas las tiendas"] + stores,
            key="workforce_mix_store",
        )
        if selected_label != "Todas las tiendas":
            selected_store = selected_label

    employees, mix = prepare_workforce_mix(frames.get("weekly"), selected_store)
    if employees.empty or mix.empty:
        st.warning("No hay empleados con horas contractuales válidas para la selección actual.")
        return

    total_employees = len(employees)
    total_contract_hours = float(employees["applicableWorkingHours"].sum())
    average_contract = float(employees["applicableWorkingHours"].mean())

    cols = st.columns(4)
    kpi(cols[0], "Empleados", fmt(total_employees), "Con horas contractuales válidas", "blue")
    kpi(cols[1], "Tipos de contrato", fmt(len(mix)), "Horas contractuales distintas", "blue")
    kpi(cols[2], "Horas contratadas/semana", fmt(total_contract_hours, 1), "Suma de horas de contrato", "blue")
    kpi(cols[3], "Jornada media", f"{average_contract:.1f} h", "Media por empleado", "blue")

    st.markdown("#### Distribución por horas de contrato")
    chart = mix.copy()
    chart["Contrato"] = chart["applicableWorkingHours"].map(lambda value: f"{value:g} h")
    chart["Etiqueta"] = chart.apply(
        lambda row: f'{int(row["Empleados"])} empleados · {row["Porcentaje plantilla"]:.1f}%',
        axis=1,
    )
    fig = go.Figure(go.Bar(
        x=chart["Empleados"],
        y=chart["Contrato"],
        orientation="h",
        text=chart["Etiqueta"],
        textposition="auto",
        customdata=chart[["Porcentaje plantilla", "Horas contratadas", "Porcentaje horas"]].to_numpy(),
        hovertemplate=(
            "%{y}<br>%{x} empleados (%{customdata[0]:.1f}%)"
            "<br>%{customdata[1]:.1f} h contratadas/semana (%{customdata[2]:.1f}% del total)<extra></extra>"
        ),
    ))
    fig.update_layout(
        height=min(520, max(300, 145 + 42 * len(chart))),
        xaxis_title="Número de empleados",
        yaxis_title="Horas de contrato",
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Detalle del mix")
    table = mix.rename(columns={
        "applicableWorkingHours": "Horas contrato",
        "Porcentaje plantilla": "% plantilla",
        "Horas contratadas": "Horas contratadas/semana",
        "Porcentaje horas": "% horas contratadas",
    }).copy()
    st.dataframe(
        table[["Horas contrato", "Empleados", "% plantilla", "Horas contratadas/semana", "% horas contratadas"]],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Horas contrato": st.column_config.NumberColumn("Horas contrato", format="%.1f h"),
            "Empleados": st.column_config.NumberColumn("Empleados", format="%d"),
            "% plantilla": st.column_config.NumberColumn("% plantilla", format="%.1f%%"),
            "Horas contratadas/semana": st.column_config.NumberColumn("Horas contratadas/semana", format="%.1f h"),
            "% horas contratadas": st.column_config.NumberColumn("% horas contratadas", format="%.1f%%"),
        },
    )
    st.caption(
        "El porcentaje de plantilla se calcula sobre empleados con horas contractuales válidas. "
        "El porcentaje de horas muestra el peso de cada tipo de contrato sobre la capacidad contractual semanal total."
    )
'''


def apply_workforce_insights_support(source: str) -> str:
    """Add workforce-mix presentation and explicit weekend magnitude visual."""
    if NEW_WEEKEND_ROTATION not in source:
        if OLD_WEEKEND_ROTATION not in source:
            raise RuntimeError("No se encontró la gráfica de rotación de fin de semana esperada.")
        source = source.replace(OLD_WEEKEND_ROTATION, NEW_WEEKEND_ROTATION, 1)

    import_marker = "from validator_engine import ("
    import_line = "from workforce_insights_dashboard import prepare_workforce_mix\n\n"
    if import_line not in source:
        if import_marker not in source:
            raise RuntimeError("No se encontró el bloque de importaciones del dashboard.")
        source = source.replace(import_marker, import_line + import_marker, 1)

    renderer_marker = "\ndef render_weekends(frames, data_dates):"
    if "\ndef render_workforce_mix(frames):" not in source:
        if renderer_marker not in source:
            raise RuntimeError("No se encontró render_weekends para insertar Mix de plantilla.")
        source = source.replace(
            renderer_marker,
            "\n" + MIX_RENDERER.rstrip() + "\n\n" + renderer_marker,
            1,
        )

    old_tabs = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])'
    new_tabs = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Mix de plantilla", "Metodologia"])'
    if new_tabs not in source:
        if old_tabs not in source:
            raise RuntimeError("No se encontró la declaración de pestañas esperada.")
        source = source.replace(old_tabs, new_tabs, 1)

    old_dispatch = "with tabs[6]: render_weekends(frames, filtered_data_dates)\nwith tabs[7]:"
    new_dispatch = (
        "with tabs[6]: render_weekends(frames, filtered_data_dates)\n"
        "with tabs[7]: render_workforce_mix(frames)\n"
        "with tabs[8]:"
    )
    if new_dispatch not in source:
        if old_dispatch not in source:
            raise RuntimeError("No se encontró el enrutado de pestañas esperado.")
        source = source.replace(old_dispatch, new_dispatch, 1)
    return source
