from __future__ import annotations


def apply_html_report_support(source: str) -> str:
    """Añade exportación HTML bilingüe y mejora el mapa empleado-fin de semana."""
    source = source.replace(
        "import streamlit as st\n",
        "import streamlit as st\nimport streamlit.components.v1 as components\n",
        1,
    )
    source = source.replace(
        "    build_excel_bytes,\n",
        "    build_excel_bytes,\n    build_html_report,\n    build_weekend_map_component,\n",
        1,
    )

    old_download = '''st.sidebar.download_button(
    "Descargar Excel de detalle",
    data=build_excel_bytes(result),
    file_name=f"validacion_{selected_source}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
'''
    new_download = old_download + '''html_report_bytes = build_html_report(
    result,
    frames,
    SCHEDULE_SOURCES[selected_source],
    file_names=file_names,
    data_dates=filtered_data_dates,
)
st.sidebar.download_button(
    "Descargar informe HTML / Download HTML",
    data=html_report_bytes,
    file_name=f"validacion_{store_id}_{selected_source}.html",
    mime="text/html",
    use_container_width=True,
    help="Genera un único HTML autónomo con selector Castellano/English para compartir sin instalar Streamlit.",
)
'''
    if old_download not in source:
        raise RuntimeError("No se encontró el botón de descarga Excel esperado.")
    source = source.replace(old_download, new_download, 1)

    old_map = '''        st.markdown("#### Mapa empleado-fin de semana")
        contract_text = weekends["applicableWorkingHours"].map(lambda value: f"{value:g}" if pd.notna(value) else "—")
        weekends["Empleado"] = weekends["id_tienda"].astype(str) + " · " + weekends["personId"].astype(str) + " · " + contract_text + " h"
        weekends["dias_libres"] = weekends["sabado_libre"].astype(int) + weekends["domingo_libre"].astype(int)
        order = weekends[["inicio_fin_semana", "Fin de semana"]].drop_duplicates().sort_values("inicio_fin_semana")["Fin de semana"].tolist()
        matrix = weekends.pivot_table(index="Empleado", columns="Fin de semana", values="dias_libres", aggfunc="first").reindex(columns=order)
        fig = go.Figure(go.Heatmap(z=matrix.to_numpy(), x=matrix.columns, y=matrix.index, zmin=0, zmax=2, ygap=1, colorscale=[[0,"#cbd5e1"],[0.49,"#cbd5e1"],[0.5,"#93c5fd"],[0.74,"#93c5fd"],[0.75,"#1d4ed8"],[1,"#1d4ed8"]], colorbar={"tickvals":[0,1,2],"ticktext":["0 días","1 día","2 días"]}))
        fig.update_layout(height=min(900, max(340, 130 + 23 * len(matrix))), plot_bgcolor="#000000")
        st.plotly_chart(fig, use_container_width=True)
'''
    new_map = '''        st.markdown("#### Mapa empleado-fin de semana")
        help_text("La primera columna permanece fija al desplazarse, las filas están separadas visualmente y los empleados con menos fines de semana completos aparecen primero. Puede buscar por empleado o mostrar únicamente alertas.")
        weekends["dias_libres"] = weekends["sabado_libre"].astype(int) + weekends["domingo_libre"].astype(int)
        employee_count = weekends[["id_tienda", "personId"]].drop_duplicates().shape[0]
        component_height = min(920, max(430, 170 + 40 * employee_count))
        components.html(
            build_weekend_map_component(weekends, language="es"),
            height=component_height,
            scrolling=True,
        )
'''
    if old_map not in source:
        raise RuntimeError("No se encontró el mapa de fines de semana esperado.")
    source = source.replace(old_map, new_map, 1)
    return source
