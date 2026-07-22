from __future__ import annotations

import re
from pathlib import Path

# Reutiliza la iteración anterior y aplica solo cambios de presentación.
patch_source = Path("dashboard_patch_v2.py").read_text(encoding="utf-8")
patch_source = re.sub(
    r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$',
    "",
    patch_source,
    flags=re.S,
)
namespace = {"__name__": "dashboard_patch_v2_base", "__file__": "dashboard_patch_v2.py"}
exec(compile(patch_source, "dashboard_patch_v2.py", "exec"), namespace)
source = namespace["source"]

# Sustituye la gráfica por una tabla operativa de promedios semanales por empleado.
old_balance_chart = '''    with right:
        chart = balance.assign(Empleado=balance["id_tienda"].astype(str)+" · "+balance["personId"].astype(str)).sort_values(["promedio_mananas_semana", "promedio_tardes_semana"], ascending=False)
        long = chart.melt(id_vars=["Empleado", "estado_rotacion"], value_vars=["promedio_mananas_semana", "promedio_tardes_semana"], var_name="Franja", value_name="Turnos medios por semana")
        long["Franja"] = long["Franja"].map({"promedio_mananas_semana":"Mañanas", "promedio_tardes_semana":"Tardes"})
        fig = px.bar(long, x="Empleado", y="Turnos medios por semana", color="Franja", barmode="group", text_auto=".2f", color_discrete_map={"Mañanas":"#2563eb", "Tardes":"#7c3aed"}, height=430)
        fig.update_layout(xaxis_title="Empleado", yaxis_title="Turnos medios por semana", legend_title_text="Franja", margin=dict(l=20, r=20, t=20, b=90))
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Promedio calculado sobre {weeks_in_scope} semana(s) del periodo seleccionado.")
'''
new_balance_table = '''    with right:
        st.markdown("#### Promedio semanal por empleado")
        help_text("La tabla permite localizar rápidamente empleados sin mañanas o sin tardes. Cero identifica ausencia total de esa franja en el periodo seleccionado.")
        chart = balance.assign(Empleado=balance["id_tienda"].astype(str)+" · "+balance["personId"].astype(str)).copy()
        chart["Sin mañanas"] = chart["turnos_manana"].eq(0)
        chart["Sin tardes"] = chart["turnos_tarde"].eq(0)
        chart = chart.sort_values(
            ["Sin mañanas", "Sin tardes", "promedio_mananas_semana", "promedio_tardes_semana", "Empleado"],
            ascending=[False, False, True, True, True],
        )
        st.dataframe(
            chart[["Empleado", "promedio_mananas_semana", "promedio_tardes_semana", "turnos_manana", "turnos_tarde", "estado_rotacion"]],
            hide_index=True,
            use_container_width=True,
            height=min(620, 38 * (len(chart) + 1)),
            column_config={
                "Empleado": st.column_config.TextColumn("Empleado"),
                "promedio_mananas_semana": st.column_config.NumberColumn("Mañanas medias/semana", format="%.2f"),
                "promedio_tardes_semana": st.column_config.NumberColumn("Tardes medias/semana", format="%.2f"),
                "turnos_manana": st.column_config.NumberColumn("Mañanas totales", format="%d"),
                "turnos_tarde": st.column_config.NumberColumn("Tardes totales", format="%d"),
                "estado_rotacion": st.column_config.TextColumn("Rotación"),
            },
        )
        st.caption(f"Promedio calculado sobre {weeks_in_scope} semana(s) del periodo seleccionado.")
'''
if old_balance_chart not in source:
    raise RuntimeError("No se encontró el bloque de balance esperado para sustituir.")
source = source.replace(old_balance_chart, new_balance_table)

# Usa una escala más clara y progresiva en el calendario de cobertura.
old_colorscale = 'colorscale=[[0, "#f1f5f9"], [0.01, "#dbeafe"], [0.55, "#60a5fa"], [1, "#1d4ed8"]]'
new_colorscale = 'colorscale=[[0, "#ffffff"], [0.01, "#f0f7ff"], [0.35, "#dbeafe"], [0.70, "#bfdbfe"], [1, "#60a5fa"]]'
if old_colorscale not in source:
    raise RuntimeError("No se encontró la escala de color de cobertura esperada.")
source = source.replace(old_colorscale, new_colorscale)

# Añade las iniciales del día de la semana al eje X de la evolución diaria.
old_evolution_layout = '    fig.update_layout(height=380, xaxis_title="Fecha", yaxis_title="Horas planificadas", margin=dict(l=20, r=20, t=20, b=20))\n    st.plotly_chart(fig, use_container_width=True)'
new_evolution_layout = '''    weekday_initials = daily["weekday"].map({0:"L", 1:"M", 2:"X", 3:"J", 4:"V", 5:"S", 6:"D"})
    fig.update_layout(height=380, xaxis_title="Día de la semana", yaxis_title="Horas planificadas", margin=dict(l=20, r=20, t=20, b=20))
    fig.update_xaxes(tickmode="array", tickvals=daily["day"], ticktext=weekday_initials, tickangle=0)
    st.plotly_chart(fig, use_container_width=True)'''
if old_evolution_layout not in source:
    raise RuntimeError("No se encontró el bloque de evolución diaria esperado.")
source = source.replace(old_evolution_layout, new_evolution_layout)

exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})
