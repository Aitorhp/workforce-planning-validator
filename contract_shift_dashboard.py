from __future__ import annotations

import re


def apply_contract_and_shift_band_support(source: str) -> str:
    """Añade revisión contractual y franjas parametrizables a Streamlit y HTML."""
    source = source.replace(
        "from datetime import datetime\n",
        "from datetime import datetime, time\n",
        1,
    )
    import_anchor = "import streamlit as st\n"
    extra_import = (
        "import streamlit as st\n\n"
        "from workforce_validator.reporting import "
        "build_html_report, build_shift_balance_dataframe\n"
    )
    if import_anchor not in source:
        raise RuntimeError("No se encontró el bloque de imports de Streamlit.")
    source = source.replace(import_anchor, extra_import, 1)

    selector_anchor = '''st.sidebar.markdown("**Fuentes detectadas**")
for source, stats in source_stats.items():
    symbol = "✅" if stats["work_segments"] else "—"
    st.sidebar.caption(f"{symbol} {source}: {stats['work_segments']} segmentos WORK")
'''
    selectors = selector_anchor + '''
st.sidebar.markdown("**Clasificación de turnos**")
morning_cutoff = st.sidebar.time_input(
    "Mañana: turnos que empiezan antes de",
    value=time(11, 0),
    step=900,
    key="shift_morning_cutoff",
)
afternoon_cutoff = st.sidebar.time_input(
    "Tarde: turnos que empiezan después de",
    value=time(14, 0),
    step=900,
    key="shift_afternoon_cutoff",
)
if morning_cutoff >= afternoon_cutoff:
    st.sidebar.error("El límite de mañana debe ser anterior al límite de tarde.")
    st.stop()
st.sidebar.caption(
    f"Central: de {morning_cutoff:%H:%M} a {afternoon_cutoff:%H:%M}, ambos incluidos."
)
'''
    if selector_anchor not in source:
        raise RuntimeError("No se encontró el bloque de fuentes para añadir los selectores.")
    source = source.replace(selector_anchor, selectors, 1)

    replacement = r'''
def render_shift_balance(frames, morning_cutoff, afternoon_cutoff):
    shifts = frames.get("shifts", pd.DataFrame()).copy()
    date_scope = frames.get("absence_daily", pd.DataFrame()).copy()
    st.subheader("Balance de turnos de mañana, centrales y tarde")
    help_text(
        f"Mañana: inicio antes de {morning_cutoff:%H:%M}. "
        f"Central: inicio entre {morning_cutoff:%H:%M} y {afternoon_cutoff:%H:%M}, ambos incluidos. "
        f"Tarde: inicio después de {afternoon_cutoff:%H:%M}. Los selectores de la barra lateral recalculan toda esta pestaña."
    )
    if shifts.empty:
        st.warning("No hay turnos disponibles para calcular el balance de franjas.")
        return

    if not date_scope.empty:
        weeks_in_scope = date_scope["fecha"].dt.to_period("W-SUN").nunique()
    else:
        weeks_in_scope = shifts["day"].dt.to_period("W-SUN").nunique()
    weeks_in_scope = max(int(weeks_in_scope), 1)
    balance = build_shift_balance_dataframe(
        shifts, morning_cutoff, afternoon_cutoff, weeks_in_scope
    )

    total = len(balance)
    all_three = int(balance["cubre_tres_franjas"].eq("SI").sum())
    only_morning = int(balance["estado_rotacion"].eq("Solo mañanas").sum())
    only_central = int(balance["estado_rotacion"].eq("Solo centrales").sum())
    only_afternoon = int(balance["estado_rotacion"].eq("Solo tardes").sum())
    cols = st.columns(5)
    kpi(cols[0], "Empleados", fmt(total), "Con al menos un turno", "blue")
    kpi(cols[1], "Cubren las 3 franjas", fmt(all_three), pct_text(pct(all_three,total)), "green" if all_three == total else "purple")
    kpi(cols[2], "Solo mañanas", fmt(only_morning), pct_text(pct(only_morning,total)), "red" if only_morning else "green")
    kpi(cols[3], "Solo centrales", fmt(only_central), pct_text(pct(only_central,total)), "amber" if only_central else "green")
    kpi(cols[4], "Solo tardes", fmt(only_afternoon), pct_text(pct(only_afternoon,total)), "red" if only_afternoon else "green")

    left, right = st.columns([.85, 1.5])
    with left:
        st.markdown("#### Combinación de franjas por empleado")
        counts = balance["estado_rotacion"].value_counts().rename_axis("Estado").reset_index(name="Empleados")
        fig = px.pie(
            counts, names="Estado", values="Empleados", hole=.55,
            color="Estado",
            color_discrete_map={
                "Mañana, central y tarde":"#22a447",
                "Solo mañanas":"#2563eb",
                "Solo centrales":"#f59e0b",
                "Solo tardes":"#7c3aed",
            },
            height=420,
        )
        fig.update_traces(textinfo="value+percent")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### Promedio semanal por empleado")
        help_text("La tabla incorpora las tres franjas y se recalcula al modificar los límites horarios.")
        chart = balance.assign(
            Empleado=balance["id_tienda"].astype(str)+" · "+balance["personId"].astype(str)
        ).sort_values(
            ["cubre_tres_franjas", "promedio_mananas_semana", "promedio_centrales_semana", "promedio_tardes_semana", "Empleado"],
            ascending=[True, True, True, True, True],
        )
        st.dataframe(
            chart[[
                "Empleado", "promedio_mananas_semana", "promedio_centrales_semana",
                "promedio_tardes_semana", "turnos_manana", "turnos_central",
                "turnos_tarde", "estado_rotacion",
            ]],
            hide_index=True,
            use_container_width=True,
            height=min(620, 38 * (len(chart) + 1)),
            column_config={
                "promedio_mananas_semana": st.column_config.NumberColumn("Mañanas medias/semana", format="%.2f"),
                "promedio_centrales_semana": st.column_config.NumberColumn("Centrales medias/semana", format="%.2f"),
                "promedio_tardes_semana": st.column_config.NumberColumn("Tardes medias/semana", format="%.2f"),
                "turnos_manana": st.column_config.NumberColumn("Mañanas totales", format="%d"),
                "turnos_central": st.column_config.NumberColumn("Centrales totales", format="%d"),
                "turnos_tarde": st.column_config.NumberColumn("Tardes totales", format="%d"),
                "estado_rotacion": st.column_config.TextColumn("Rotación"),
            },
        )
        st.caption(f"Promedio calculado sobre {weeks_in_scope} semana(s) del periodo seleccionado.")

    st.markdown("#### Detalle por empleado")
    only_incomplete = st.checkbox(
        "Mostrar solo empleados que no cubren las tres franjas",
        value=True,
        key="shift_balance_only_incomplete",
    )
    view = balance.loc[balance["cubre_tres_franjas"].eq("NO")].copy() if only_incomplete else balance.copy()
    st.dataframe(
        view[[
            "id_tienda", "personId", "estado_rotacion", "turnos_manana",
            "turnos_central", "turnos_tarde", "turnos_totales", "horas_manana",
            "horas_central", "horas_tarde", "porcentaje_manana",
            "porcentaje_central", "porcentaje_tarde", "indice_equilibrio_pct",
        ]],
        hide_index=True,
        use_container_width=True,
    )


def render_absences'''
    pattern = r"\ndef render_shift_balance\(frames\):.*?\n\ndef render_absences"
    source, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("No se encontró la función de balance para sustituirla.")

    source = source.replace(
        "with tabs[4]: render_shift_balance(frames)",
        "with tabs[4]: render_shift_balance(frames, morning_cutoff, afternoon_cutoff)",
        1,
    )
    source = source.replace(
        '"Balance mañana/tarde"',
        '"Balance mañana/central/tarde"',
        1,
    )

    contract_section = '''
    st.markdown("#### Cambios de horas contractuales entre meses")
    help_text(
        "Esta tabla identifica empleados cuyo applicableWorkingHours cambia entre los meses cargados. "
        "Se considera una señal de revisión. Las semanas que contienen dos valores contractuales distintos "
        "quedan marcadas como CAMBIO CONTRATO y no se evalúan contra un valor arbitrario."
    )
    contract_changes = frames.get("contract_changes", pd.DataFrame()).copy()
    if contract_changes.empty:
        st.success("No se han detectado cambios de horas contractuales entre meses.")
    else:
        st.warning(f"Se han detectado {len(contract_changes)} empleado(s) con cambio contractual.")
        view_contracts = contract_changes.rename(columns={
            "id_tienda":"Tienda", "personId":"Empleado", "mes_anterior":"Mes anterior",
            "horas_mes_anterior":"Horas anteriores", "mes_posterior":"Mes posterior",
            "horas_mes_posterior":"Horas posteriores", "variacion_horas":"Variación (h)",
            "detalle_contrato":"Detalle", "requiere_revision":"Revisar",
        })
        st.dataframe(
            view_contracts[["Tienda","Empleado","Mes anterior","Horas anteriores","Mes posterior","Horas posteriores","Variación (h)","Detalle","Revisar"]],
            hide_index=True,
            use_container_width=True,
        )
'''
    coverage_anchor = "\n\ndef render_coverage(frames, data_dates):"
    if coverage_anchor not in source:
        raise RuntimeError("No se encontró el final de la pestaña contractual.")
    source = source.replace(
        coverage_anchor,
        contract_section + coverage_anchor,
        1,
    )

    html_block = '''
period_start = min(result.data_dates) if result.data_dates else None
period_end = max(result.data_dates) if result.data_dates else None
html_report = build_html_report(
    frames,
    store_id,
    selected_source,
    morning_cutoff,
    afternoon_cutoff,
    period_start,
    period_end,
)
st.sidebar.download_button(
    "Descargar informe HTML",
    data=html_report,
    file_name=f"validacion_{store_id}_{selected_source}.html",
    mime="text/html",
    use_container_width=True,
)

'''
    title_anchor = 'st.title("Validador de planificaciones")'
    if title_anchor not in source:
        raise RuntimeError("No se encontró el título para insertar la descarga HTML.")
    source = source.replace(title_anchor, html_block + title_anchor, 1)

    methodology_anchor = "- El control semanal compara las horas del origen seleccionado con `applicableWorkingHours`."
    methodology_new = methodology_anchor + "\n    - Si una semana cruza un cambio de contrato, se marca como `CAMBIO CONTRATO` y no se evalúa contra uno de los dos valores.\n    - Las franjas mañana, central y tarde usan los límites configurados en la barra lateral y el mismo cálculo se aplica al HTML."
    source = source.replace(methodology_anchor, methodology_new, 1)
    return source
