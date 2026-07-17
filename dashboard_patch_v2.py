from __future__ import annotations

import re
from pathlib import Path

# Reutiliza íntegramente la capa visual anterior y aplica únicamente esta iteración.
patch_source = Path("dashboard_patch.py").read_text(encoding="utf-8")
patch_source = re.sub(r"\nexec\(compile\(source, \"app.py\", \"exec\"\), \{.*$", "", patch_source, flags=re.S)
namespace = {"__name__": "dashboard_patch_base", "__file__": "dashboard_patch.py"}
exec(compile(patch_source, "dashboard_patch.py", "exec"), namespace)
source = namespace["source"]

# Añade al detalle semanal una lectura directa de cuánto déficit puede cubrirse
# con las horas teóricas asociadas a ausencias, sin imputarlas como trabajadas.
source = source.replace(
    '    evaluable["contexto_ausencia"] = "No aplica"',
    '    evaluable["horas_potenciales_asociadas_ausencia"] = pd.to_numeric(evaluable["horas_potenciales_asociadas_ausencia"], errors="coerce").fillna(0.0)\n'
    '    evaluable["horas_ausencia_aplicables"] = evaluable[["horas_no_planificadas_hasta_contrato", "horas_potenciales_asociadas_ausencia"]].min(axis=1)\n'
    '    evaluable["planificadas_mas_ausencia"] = evaluable["horas_planificadas"] + evaluable["horas_ausencia_aplicables"]\n'
    '    evaluable["deficit_explicable_ausencia"] = evaluable["posible_explicacion_por_ausencia"].eq("PODRIA EXPLICAR TODAS LAS HORAS FALTANTES")\n'
    '    labels = {"PODRIA EXPLICAR TODAS LAS HORAS FALTANTES": "Sí, explica todo el déficit", "PODRIA EXPLICAR PARTE DE LAS HORAS FALTANTES": "Explica parte del déficit", "AUSENCIA SIN MEDIA CALCULABLE": "Sin estimación disponible", "AUSENTE TODO EL PERIODO": "Ausente todo el periodo", "NO": "No explicado por ausencias"}\n'
    '    evaluable["explicacion_ausencia"] = evaluable["posible_explicacion_por_ausencia"].map(labels).fillna("No explicado por ausencias")\n'
    '    evaluable.loc[~evaluable["estado_planificacion"].eq("FALTAN HORAS"), "explicacion_ausencia"] = "Contrato cubierto o con exceso"\n'
    '    evaluable["contexto_ausencia"] = "No aplica"'
)

source = source.replace(
    '    if deficit.any():\n        top = detail.loc[deficit]',
    '    if deficit.any():\n'
    '        deficit_employees = detail.loc[deficit].groupby(["id_tienda", "personId"], as_index=False).agg(semanas_deficit=("Semana", "size"), semanas_explicables=("deficit_explicable_ausencia", "sum"), horas_deficit=("horas_no_planificadas_hasta_contrato", "sum"), horas_explicables=("horas_ausencia_aplicables", "sum"))\n'
    '        deficit_employees["todo_explicable"] = deficit_employees["semanas_deficit"].eq(deficit_employees["semanas_explicables"])\n'
    '        explained = int(deficit_employees["todo_explicable"].sum())\n'
    '        insight = st.columns(3)\n'
    '        kpi(insight[0], "Empleados con déficit", fmt(len(deficit_employees)), "Al menos una semana por debajo del contrato", "red")\n'
    '        kpi(insight[1], "Explicables por ausencias", fmt(explained), pct_text(pct(explained, len(deficit_employees))), "purple")\n'
    '        kpi(insight[2], "Horas explicables estimadas", f"{fmt(deficit_employees.horas_explicables.sum(),1)} h", f"De {fmt(deficit_employees.horas_deficit.sum(),1)} h de déficit", "purple")\n'
    '        top = detail.loc[deficit]'
)

source = source.replace(
    '    help_text("Tabla operativa al nivel correcto. La ausencia es una pista contextual, no una imputacion de horas.")',
    '    help_text("La columna de explicación indica directamente si las horas teóricas asociadas a ausencias alcanzarían el contrato. Es una señal diagnóstica, no una imputación de trabajo.")'
)
source = source.replace(
    '"contexto_ausencia": "Contexto ausencia"})',
    '"contexto_ausencia": "Contexto ausencia", "planificadas_mas_ausencia": "Planificadas + ausencia estimada", "horas_potenciales_asociadas_ausencia": "Horas teóricas por ausencia", "explicacion_ausencia": "Explicación por ausencias"})'
)
source = source.replace(
    '"Horas faltantes", "Horas en exceso", "Dias ausencia sin turno", "Tipos ausencia", "Contexto ausencia"]',
    '"Horas faltantes", "Horas en exceso", "Dias ausencia sin turno", "Horas teóricas por ausencia", "Planificadas + ausencia estimada", "Tipos ausencia", "Explicación por ausencias", "Contexto ausencia"]'
)
source = source.replace(
    '"Horas en exceso": st.column_config.NumberColumn(format="%.1f h")})',
    '"Horas en exceso": st.column_config.NumberColumn(format="%.1f h"), "Horas teóricas por ausencia": st.column_config.NumberColumn(format="%.1f h"), "Planificadas + ausencia estimada": st.column_config.NumberColumn(format="%.1f h")})'
)

SHIFT_BALANCE = r'''
def render_shift_balance(frames):
    balance = frames.get("shift_balance", pd.DataFrame())
    st.subheader("Balance de turnos de mañana y tarde")
    help_text("Mañana: inicio antes de las 13:00. Tarde: inicio a las 13:00 o después. La vista detecta empleados sin rotación y mide el equilibrio del reparto.")
    if balance.empty:
        st.warning("No hay turnos disponibles para calcular el balance de franjas.")
        return
    total = len(balance)
    both = int(balance["rota_manana_tarde"].eq("SI").sum())
    morning = int(balance["estado_rotacion"].eq("Solo mañanas").sum())
    afternoon = int(balance["estado_rotacion"].eq("Solo tardes").sum())
    cols = st.columns(5)
    kpi(cols[0], "Empleados", fmt(total), "Con al menos un turno", "blue")
    kpi(cols[1], "Rotan mañana y tarde", fmt(both), pct_text(pct(both,total)), "green" if both == total else "purple")
    kpi(cols[2], "Solo mañanas", fmt(morning), pct_text(pct(morning,total)), "red" if morning else "green")
    kpi(cols[3], "Solo tardes", fmt(afternoon), pct_text(pct(afternoon,total)), "red" if afternoon else "green")
    kpi(cols[4], "Índice de equilibrio", pct_text(balance["indice_equilibrio_pct"].mean()), "0 = una franja; 100 = reparto 50/50", "blue")
    if morning or afternoon:
        st.warning(f"Hay {morning + afternoon} empleados sin rotación: {morning} solo de mañana y {afternoon} solo de tarde.")
    else:
        st.success("Todos los empleados tienen al menos un turno de mañana y uno de tarde.")
    left, right = st.columns([.85, 1.5])
    with left:
        counts = balance["estado_rotacion"].value_counts().reindex(["Mañana y tarde", "Solo mañanas", "Solo tardes"], fill_value=0).rename_axis("Estado").reset_index(name="Empleados")
        fig = px.pie(counts, names="Estado", values="Empleados", hole=.55, color="Estado", color_discrete_map={"Mañana y tarde":"#22a447", "Solo mañanas":"#2563eb", "Solo tardes":"#7c3aed"}, height=390)
        fig.update_traces(textinfo="value+percent")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        chart = balance.assign(Empleado=balance["id_tienda"].astype(str)+" · "+balance["personId"].astype(str)).sort_values("sesgo_tarde_pct")
        fig = px.bar(chart, x="sesgo_tarde_pct", y="Empleado", orientation="h", color="estado_rotacion", color_discrete_map={"Mañana y tarde":"#22a447", "Solo mañanas":"#2563eb", "Solo tardes":"#7c3aed"}, custom_data=["turnos_manana","turnos_tarde","indice_equilibrio_pct"], height=min(900,max(360,130+24*len(chart))))
        fig.add_vline(x=0, line_dash="dash")
        fig.update_traces(hovertemplate="%{y}<br>Sesgo: %{x:.1f}<br>Mañanas: %{customdata[0]}<br>Tardes: %{customdata[1]}<br>Equilibrio: %{customdata[2]:.1f}%<extra></extra>")
        fig.update_layout(xaxis={"title":"Sesgo hacia tarde (%)","range":[-105,105]}, legend_title_text="Rotación")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Detalle por empleado")
    only_non_rotating = st.checkbox("Mostrar solo empleados sin rotación", value=True, key="shift_balance_only_non_rotating")
    view = balance.loc[balance["rota_manana_tarde"].eq("NO")].copy() if only_non_rotating else balance.copy()
    st.dataframe(view[["id_tienda","personId","estado_rotacion","turnos_manana","turnos_tarde","turnos_totales","horas_manana","horas_tarde","porcentaje_manana","porcentaje_tarde","indice_equilibrio_pct"]], hide_index=True, use_container_width=True)
'''
source = source.replace("\ndef render_absences(frames):", SHIFT_BALANCE + "\n\ndef render_absences(frames):")

# Inserta un calendario de empleados ausentes antes del gráfico por tipo.
calendar_code = '''    absence_daily = frames.get("absence_daily", pd.DataFrame()).copy()\n    if not absence_daily.empty:\n        absence_daily["weekday"] = absence_daily["fecha"].dt.weekday\n        absence_daily["week_start"] = absence_daily["fecha"] - pd.to_timedelta(absence_daily["weekday"], unit="D")\n        absence_daily["Semana calendario"] = absence_daily.apply(lambda r: f"{r.week_start:%d/%m} - {(r.week_start + pd.Timedelta(days=6)):%d/%m}", axis=1)\n        order = absence_daily[["week_start","Semana calendario"]].drop_duplicates().sort_values("week_start")["Semana calendario"].tolist()\n        calendar = absence_daily.pivot(index="Semana calendario", columns="weekday", values="empleados_ausentes").reindex(index=order, columns=range(7)).fillna(0)\n        calendar.columns = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]\n        st.markdown("#### Calendario diario de ausencias")\n        help_text("Cada celda muestra empleados únicos ausentes; los días sin ausencias se conservan con cero.")\n        fig = go.Figure(go.Heatmap(z=calendar.to_numpy(), x=calendar.columns, y=calendar.index, zmin=0, zmax=max(float(calendar.max().max()),1.0), colorscale=[[0,"#f8fafc"],[.01,"#f3e8ff"],[.55,"#c084fc"],[1,"#7e22ce"]], text=[[str(int(v)) for v in row] for row in calendar.to_numpy()], texttemplate="%{text}", colorbar={"title":"Empleados"}, hovertemplate="%{y}<br>%{x}<br>Empleados ausentes: %{z:.0f}<extra></extra>"))\n        fig.update_layout(height=max(300,120+48*len(calendar)), yaxis_autorange="reversed")\n        st.plotly_chart(fig, use_container_width=True)\n'''
source = source.replace('    if not absences.empty:\n        st.markdown("#### Ausencias por tipo")', calendar_code + '    if not absences.empty:\n        st.markdown("#### Ausencias por tipo")')

source = source.replace(
    'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Ausencias y fines de semana", "Metodologia"])',
    'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias y fines de semana", "Metodologia"])'
)
source = source.replace('with tabs[4]: render_absences(frames)\nwith tabs[5]:', 'with tabs[4]: render_shift_balance(frames)\nwith tabs[5]: render_absences(frames)\nwith tabs[6]:')

exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})
