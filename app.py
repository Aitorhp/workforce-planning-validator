from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from validator_engine import (
    MAX_CONSECUTIVE_DAYS,
    MAX_SHIFT_HOURS,
    MIN_REST_HOURS,
    MIN_SHIFT_HOURS,
    SCHEDULE_SOURCES,
    build_excel_bytes,
    detect_schedule_sources,
    load_json_bytes,
    result_dataframes,
    run_validation,
)

st.set_page_config(page_title="Validador de planificaciones", page_icon="📅", layout="wide")
st.markdown("""
<style>
.block-container {padding-top:1.2rem; max-width:1600px;}
.kpi-card {border-radius:14px; padding:15px 16px; min-height:112px; border:1px solid rgba(15,23,42,.14);}
.kpi-label {font-size:.78rem; font-weight:700; margin-bottom:8px; opacity:.9;}
.kpi-value {font-size:1.7rem; font-weight:800; line-height:1.05; margin-bottom:8px;}
.kpi-detail {font-size:.78rem; font-weight:600; opacity:.9;}
.kpi-neutral {background:#e2e8f0; color:#0f172a}.kpi-blue {background:#dbeafe; color:#123a70}
.kpi-green {background:#dcfce7; color:#14532d}.kpi-amber {background:#fef3c7; color:#713f12}
.kpi-red {background:#fee2e2; color:#7f1d1d}.kpi-purple {background:#ede9fe; color:#4c1d95}
.viz-help {background:#f8fafc; border-left:4px solid #2563eb; color:#334155; padding:9px 12px; border-radius:7px; margin:.15rem 0 .7rem; font-size:.84rem;}
.source-box {background:#eff6ff; border:1px solid #bfdbfe; padding:12px; border-radius:10px; color:#1e3a5f;}
</style>
""", unsafe_allow_html=True)

INCIDENT_LABELS = {
    "MAS_DE_5_DIAS_CONSECUTIVOS": "Mas de 5 dias consecutivos",
    "TURNO_SUPERIOR_7_5H": "Turno superior a 7,5 h",
    "TURNO_INFERIOR_4H": "Turno inferior a 4 h",
    "DESCANSO_INFERIOR_11H": "Descanso inferior a 11 h",
}
STATUS_ORDER = ["COINCIDE", "FALTAN HORAS", "EXCESO HORAS", "NO EVALUABLE", "SIN HORAS CONTRATO"]
STATUS_COLORS = {"COINCIDE":"#22a447", "FALTAN HORAS":"#dc3545", "EXCESO HORAS":"#f59e0b", "NO EVALUABLE":"#94a3b8", "SIN HORAS CONTRATO":"#64748b"}
WEEKLY_DIAGNOSIS_ORDER = [
    "Contrato cubierto",
    "Cubierto con exceso",
    "Deficit compatible con ausencias",
    "Deficit parcialmente compatible",
    "Deficit sin apoyo de ausencias",
    "Ausente todo el periodo",
]
WEEKLY_DIAGNOSIS_COLORS = {
    "Contrato cubierto": "#22a447",
    "Cubierto con exceso": "#f59e0b",
    "Deficit compatible con ausencias": "#2563eb",
    "Deficit parcialmente compatible": "#7c3aed",
    "Deficit sin apoyo de ausencias": "#dc3545",
    "Ausente todo el periodo": "#64748b",
}


def fmt(value, decimals=0):
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(num, den):
    return None if not den else num / den * 100


def pct_text(value):
    return "—" if value is None else f"{value:.1f}%".replace(".", ",")


def kpi(container, label, value, detail="", tone="neutral"):
    container.markdown(
        f'<div class="kpi-card kpi-{tone}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def help_text(text):
    st.markdown(f'<div class="viz-help">{text}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def parse_file(file_bytes: bytes):
    data = load_json_bytes(file_bytes)
    return data, detect_schedule_sources(data)


@st.cache_data(show_spinner=False)
def analyse(file_bytes: bytes, schedule_source: str):
    data = load_json_bytes(file_bytes)
    result = run_validation(data, schedule_source)
    return result, result_dataframes(result)


def normalise_frames(frames):
    output = {name: frame.copy() for name, frame in frames.items()}
    for frame in output.values():
        for column in ("day", "fecha", "fecha_inicio", "fecha_fin", "inicio_semana", "fin_semana"):
            if column in frame.columns and not frame.empty:
                frame[column] = pd.to_datetime(frame[column])
    return output


def employee_compliance(summaries):
    if summaries.empty:
        return pd.DataFrame(columns=["personId", "cumple"])
    return summaries.assign(ok=summaries["cumple_todas_las_reglas"].eq("SI")).groupby(["id_tienda", "personId"], as_index=False)["ok"].all().rename(columns={"ok":"cumple"})


def weekly_summary(weekly):
    if weekly.empty:
        return pd.DataFrame()
    counts = weekly.groupby(["ano_iso", "semana_iso", "inicio_semana", "fin_semana", "estado_planificacion"]).size().unstack(fill_value=0).reset_index()
    for status in STATUS_ORDER:
        if status not in counts.columns:
            counts[status] = 0
    sums = weekly.groupby(["ano_iso", "semana_iso", "inicio_semana", "fin_semana"], as_index=False).agg(
        horas_planificadas=("horas_planificadas", "sum"),
        horas_faltantes=("horas_no_planificadas_hasta_contrato", "sum"),
        horas_exceso=("horas_planificadas_en_exceso", "sum"),
    )
    result = counts.merge(sums, on=["ano_iso", "semana_iso", "inicio_semana", "fin_semana"])
    result["Semana"] = result.apply(lambda r: f"{int(r.ano_iso)}-S{int(r.semana_iso):02d}", axis=1)
    return result.sort_values(["ano_iso", "semana_iso"])


def prepare_weekly_analysis(weekly):
    """Build employee and week views from the existing engine output."""
    evaluable_statuses = ["COINCIDE", "FALTAN HORAS", "EXCESO HORAS"]
    evaluable = weekly.loc[weekly["estado_planificacion"].isin(evaluable_statuses)].copy()
    all_employees = weekly[["id_tienda", "personId"]].drop_duplicates()
    if evaluable.empty:
        return evaluable, pd.DataFrame(), pd.DataFrame(), len(all_employees)

    numeric_columns = [
        "applicableWorkingHours",
        "horas_planificadas",
        "horas_no_planificadas_hasta_contrato",
        "horas_planificadas_en_exceso",
        "horas_potenciales_asociadas_ausencia",
        "dias_ausencia_sin_turno",
    ]
    for column in numeric_columns:
        evaluable[column] = pd.to_numeric(evaluable[column], errors="coerce").fillna(0.0)

    evaluable["ausente_todo"] = evaluable["ausente_todo_el_periodo"].eq("SI")
    estimable = ~evaluable["ausente_todo"]
    evaluable["horas_deficit_compatibles_ausencia"] = 0.0
    evaluable.loc[estimable, "horas_deficit_compatibles_ausencia"] = pd.concat(
        [
            evaluable.loc[estimable, "horas_no_planificadas_hasta_contrato"],
            evaluable.loc[estimable, "horas_potenciales_asociadas_ausencia"],
        ],
        axis=1,
    ).min(axis=1)
    evaluable["horas_deficit_sin_explicar"] = 0.0
    evaluable.loc[estimable, "horas_deficit_sin_explicar"] = (
        evaluable.loc[estimable, "horas_no_planificadas_hasta_contrato"]
        - evaluable.loc[estimable, "horas_deficit_compatibles_ausencia"]
    ).clip(lower=0.0)
    evaluable["semana_cubierta"] = ~evaluable["estado_planificacion"].eq("FALTAN HORAS")
    evaluable["semana_exacta"] = evaluable["estado_planificacion"].eq("COINCIDE")
    evaluable["semana_deficit"] = evaluable["estado_planificacion"].eq("FALTAN HORAS")
    evaluable["semana_exceso"] = evaluable["estado_planificacion"].eq("EXCESO HORAS")

    grouped = evaluable.groupby(["id_tienda", "personId"], as_index=False).agg(
        semanas_evaluables=("estado_planificacion", "size"),
        semanas_cubiertas=("semana_cubierta", "sum"),
        semanas_exactas=("semana_exacta", "sum"),
        semanas_con_deficit=("semana_deficit", "sum"),
        semanas_con_exceso=("semana_exceso", "sum"),
        horas_contrato=("applicableWorkingHours", "sum"),
        horas_planificadas=("horas_planificadas", "sum"),
        horas_faltantes=("horas_no_planificadas_hasta_contrato", "sum"),
        horas_exceso=("horas_planificadas_en_exceso", "sum"),
        dias_ausencia_sin_turno=("dias_ausencia_sin_turno", "sum"),
        horas_deficit_compatibles_ausencia=("horas_deficit_compatibles_ausencia", "sum"),
        horas_deficit_sin_explicar=("horas_deficit_sin_explicar", "sum"),
        ausente_todo_periodo=("ausente_todo", "max"),
    )
    grouped["cobertura_horas_periodo_pct"] = grouped.apply(
        lambda row: pct(row["horas_planificadas"], row["horas_contrato"]), axis=1
    )

    def diagnosis(row):
        if row["ausente_todo_periodo"]:
            return "Ausente todo el periodo"
        if row["semanas_con_deficit"] == 0:
            return "Cubierto con exceso" if row["semanas_con_exceso"] else "Contrato cubierto"
        if row["horas_deficit_compatibles_ausencia"] <= 0.01:
            return "Deficit sin apoyo de ausencias"
        if row["horas_deficit_sin_explicar"] <= 0.01:
            return "Deficit compatible con ausencias"
        return "Deficit parcialmente compatible"

    grouped["diagnostico"] = grouped.apply(diagnosis, axis=1)
    grouped = grouped.sort_values(
        ["horas_deficit_sin_explicar", "horas_faltantes", "personId"],
        ascending=[False, False, True],
    )

    by_week = evaluable.loc[~evaluable["ausente_todo"]].groupby(
        ["ano_iso", "semana_iso", "inicio_semana", "fin_semana"], as_index=False
    ).agg(
        horas_deficit=("horas_no_planificadas_hasta_contrato", "sum"),
        horas_compatibles_ausencia=("horas_deficit_compatibles_ausencia", "sum"),
        horas_sin_explicar=("horas_deficit_sin_explicar", "sum"),
        empleados_con_deficit=("semana_deficit", "sum"),
    )
    by_week["Semana"] = by_week.apply(lambda row: f"{int(row.ano_iso)}-S{int(row.semana_iso):02d}", axis=1)
    by_week = by_week.sort_values(["ano_iso", "semana_iso"])

    non_evaluable_employees = len(all_employees) - grouped[["id_tienda", "personId"]].drop_duplicates().shape[0]
    return evaluable, grouped, by_week, non_evaluable_employees


def render_summary(frames):
    shifts, summaries, incidents, weekly = frames["shifts"], frames["summaries"], frames["incidents"], frames["weekly"]
    employees = employee_compliance(summaries)
    total = len(employees)
    compliant = int(employees["cumple"].sum()) if total else 0
    evaluable = weekly[weekly["estado_planificacion"].isin(["COINCIDE", "FALTAN HORAS", "EXCESO HORAS"])] if not weekly.empty else weekly
    matching = int(evaluable["estado_planificacion"].eq("COINCIDE").sum()) if not evaluable.empty else 0
    cols = st.columns(6)
    kpi(cols[0], "Empleados", fmt(total), "Personas unicas del fichero", "blue")
    kpi(cols[1], "Turnos", fmt(len(shifts)), "Dias-persona con horario", "blue")
    kpi(cols[2], "Horas planificadas", f"{fmt(shifts['horas_totales'].sum(),1)} h" if not shifts.empty else "0 h", "Suma neta de segmentos WORK", "purple")
    kpi(cols[3], "Sin incidencias", fmt(compliant), pct_text(pct(compliant,total)), "green")
    kpi(cols[4], "Con incidencias", fmt(total-compliant), "Al menos una regla incumplida", "amber")
    kpi(cols[5], "Incidencias", fmt(len(incidents)), "Registros de excepcion", "red")

    left, middle, right = st.columns([1.25, 1, 1])
    with left:
        st.markdown("#### Incidencias por restriccion")
        help_text("Cuenta cuantas excepciones se han generado para el origen de horarios seleccionado. Una persona puede aportar varias incidencias.")
        if incidents.empty:
            st.success("No se han detectado incidencias.")
        else:
            chart = incidents.assign(Regla=incidents["tipo_incidencia"].map(INCIDENT_LABELS)).groupby("Regla", as_index=False).size().rename(columns={"size":"Incidencias"}).sort_values("Incidencias")
            st.plotly_chart(px.bar(chart, x="Incidencias", y="Regla", orientation="h", text="Incidencias", height=350), use_container_width=True)
    with middle:
        st.markdown("#### Estado de empleados")
        help_text("Un empleado se considera sin incidencias solo si cumple las cuatro restricciones en todos los meses analizados.")
        status = pd.DataFrame({"Estado":["Sin incidencias", "Con incidencias"], "Empleados":[compliant,total-compliant]})
        fig = px.pie(status, names="Estado", values="Empleados", hole=.58, color="Estado", color_discrete_map={"Sin incidencias":"#22a447","Con incidencias":"#dc3545"}, height=350)
        fig.update_traces(textinfo="value+percent")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### Cumplimiento semanal")
        help_text("Porcentaje de registros empleado-semana evaluables cuyas horas planificadas coinciden con el contrato. Se excluyen semanas parciales y contratos no numericos.")
        value = pct(matching, len(evaluable)) or 0
        fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number={"suffix":"%"}, gauge={"axis":{"range":[0,100]},"bar":{"color":"#2563eb"}}))
        fig.update_layout(height=300, margin=dict(l=20,r=20,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)


def render_restrictions(frames):
    summaries, incidents = frames["summaries"], frames["incidents"]
    st.subheader("Restricciones")
    help_text("Las cuatro reglas se aplican de forma identica al origen seleccionado. El denominador del cumplimiento por regla es empleado-mes.")
    mapping = {
        "Maximo 5 dias consecutivos":"cumple_max_5_dias",
        "Duracion maxima 7,5 h":"cumple_duracion_maxima",
        "Duracion minima 4 h":"cumple_duracion_minima",
        "Descanso minimo 11 h":"cumple_descanso_entre_jornadas",
    }
    cols = st.columns(4)
    for col, (label, field) in zip(cols, mapping.items()):
        ok = int(summaries[field].eq("SI").sum()) if not summaries.empty else 0
        kpi(col, label, pct_text(pct(ok,len(summaries))), f"{len(summaries)-ok} empleado-mes no cumplen", "green" if ok == len(summaries) else "amber")
    st.markdown("#### Detalle reciente")
    help_text("Muestra hasta 30 incidencias ordenadas desde la fecha mas reciente. Valor observado y limite permiten entender por que se genero cada excepcion.")
    if incidents.empty:
        st.success("No hay incidencias.")
    else:
        view = incidents.assign(Regla=incidents["tipo_incidencia"].map(INCIDENT_LABELS)).sort_values("fecha_inicio", ascending=False).head(30)
        st.dataframe(view[["personId","Regla","fecha_inicio","fecha_fin","valor_observado","limite","detalle"]], hide_index=True, use_container_width=True)


def render_weekly(frames):
    weekly = frames["weekly"]
    st.subheader("Control de horas semanales")
    help_text(
        "Esta pantalla responde a tres preguntas: cuantos empleados tienen cubiertas todas sus horas contractuales, "
        "cuantos presentan deficit en alguna semana y que parte del deficit es compatible con ausencias registradas. "
        "El analisis principal usa empleados unicos; el detalle conserva el nivel empleado-semana."
    )
    if weekly.empty:
        st.warning("No hay registros semanales.")
        return

    evaluable, employees, by_week, non_evaluable = prepare_weekly_analysis(weekly)
    if employees.empty:
        st.warning("No hay empleados evaluables: se necesitan semanas completas y horas contractuales numericas.")
        return

    covered_mask = employees["semanas_con_deficit"].eq(0)
    deficit_mask = employees["semanas_con_deficit"].gt(0)
    covered_employees = int(covered_mask.sum())
    deficit_employees = int(deficit_mask.sum())
    absent_entire = int(employees["ausente_todo_periodo"].sum())
    total_missing = employees["horas_faltantes"].sum()
    estimable_missing = (
        employees.loc[~employees["ausente_todo_periodo"], "horas_deficit_compatibles_ausencia"].sum()
        + employees.loc[~employees["ausente_todo_periodo"], "horas_deficit_sin_explicar"].sum()
    )
    compatible_missing = employees.loc[~employees["ausente_todo_periodo"], "horas_deficit_compatibles_ausencia"].sum()
    compatible_pct = pct(compatible_missing, estimable_missing)

    cols = st.columns(5)
    kpi(cols[0], "Empleados evaluables", fmt(len(employees)), f"{non_evaluable} sin semanas evaluables", "blue")
    kpi(cols[1], "Contrato cubierto", fmt(covered_employees), pct_text(pct(covered_employees, len(employees))), "green")
    kpi(cols[2], "Con deficit", fmt(deficit_employees), pct_text(pct(deficit_employees, len(employees))), "red")
    kpi(cols[3], "Horas no planificadas", f"{fmt(total_missing,1)} h", "No se compensan con excesos", "red" if total_missing else "green")
    kpi(
        cols[4],
        "Deficit compatible con ausencias",
        pct_text(compatible_pct),
        f"{fmt(compatible_missing,1)} de {fmt(estimable_missing,1)} h estimables",
        "purple",
    )

    if absent_entire:
        st.info(
            f"Hay {absent_entire} empleado(s) marcados como ausentes durante todo el periodo. "
            "Se muestran como categoria separada y no se estiman horas explicables porque no existe una jornada media planificada fiable."
        )

    left, right = st.columns([1, 1.35])
    with left:
        st.markdown("#### Respuesta por empleado")
        help_text(
            "Un empleado aparece como 'contrato cubierto' cuando ninguna de sus semanas evaluables queda por debajo del contrato. "
            "Los excesos se separan porque cubren el contrato, pero siguen siendo una desviacion a revisar."
        )
        diagnosis = employees["diagnostico"].value_counts().reindex(WEEKLY_DIAGNOSIS_ORDER, fill_value=0)
        diagnosis = diagnosis[diagnosis.gt(0)].rename_axis("Diagnostico").reset_index(name="Empleados")
        fig = px.bar(
            diagnosis,
            x="Empleados",
            y="Diagnostico",
            orientation="h",
            text="Empleados",
            color="Diagnostico",
            color_discrete_map=WEEKLY_DIAGNOSIS_COLORS,
            height=410,
        )
        fig.update_layout(showlegend=False, yaxis={"categoryorder":"array", "categoryarray":list(reversed(WEEKLY_DIAGNOSIS_ORDER))})
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Deficit semanal: ausencia vs. pendiente de explicar")
        help_text(
            "Las horas compatibles con ausencia son una estimacion: dias de ausencia sin turno multiplicados por la jornada media planificada del empleado, "
            "limitadas al deficit real. Las ausencias no se suman a las horas trabajadas. Se excluyen los ausentes todo el periodo."
        )
        deficit_weeks = by_week.loc[by_week["horas_deficit"].gt(0)].copy()
        if deficit_weeks.empty:
            st.success("No hay horas deficitarias en las semanas evaluables.")
        else:
            long = deficit_weeks.melt(
                id_vars="Semana",
                value_vars=["horas_compatibles_ausencia", "horas_sin_explicar"],
                var_name="Tipo",
                value_name="Horas",
            )
            labels = {
                "horas_compatibles_ausencia": "Compatibles con ausencias",
                "horas_sin_explicar": "Sin explicar por ausencias",
            }
            long["Tipo"] = long["Tipo"].map(labels)
            fig = px.bar(
                long,
                x="Semana",
                y="Horas",
                color="Tipo",
                barmode="stack",
                color_discrete_map={
                    "Compatibles con ausencias":"#7c3aed",
                    "Sin explicar por ausencias":"#dc3545",
                },
                height=410,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Empleados que requieren revision")
    help_text(
        "La tabla agrega todo el periodo por empleado. 'Cobertura del periodo' compara horas totales, pero la clasificacion se decide semana a semana para evitar que un exceso compense un deficit de otra semana."
    )
    only_deficit = st.checkbox("Mostrar solo empleados con deficit", value=True, key="weekly_only_deficit")
    view = employees.loc[employees["semanas_con_deficit"].gt(0)].copy() if only_deficit else employees.copy()
    view = view.rename(columns={
        "diagnostico":"Diagnostico",
        "semanas_evaluables":"Semanas evaluables",
        "semanas_cubiertas":"Semanas cubiertas",
        "semanas_con_deficit":"Semanas con deficit",
        "semanas_con_exceso":"Semanas con exceso",
        "horas_contrato":"Horas de contrato",
        "horas_planificadas":"Horas planificadas",
        "cobertura_horas_periodo_pct":"Cobertura periodo (%)",
        "horas_faltantes":"Horas faltantes",
        "horas_exceso":"Horas en exceso",
        "dias_ausencia_sin_turno":"Dias de ausencia sin turno",
        "horas_deficit_compatibles_ausencia":"Deficit compatible con ausencia (h)",
        "horas_deficit_sin_explicar":"Deficit sin explicar (h)",
    })
    columns = [
        "id_tienda", "personId", "Diagnostico", "Semanas evaluables", "Semanas cubiertas",
        "Semanas con deficit", "Semanas con exceso", "Horas de contrato", "Horas planificadas",
        "Cobertura periodo (%)", "Horas faltantes", "Horas en exceso", "Dias de ausencia sin turno",
        "Deficit compatible con ausencia (h)", "Deficit sin explicar (h)",
    ]
    st.dataframe(
        view[columns],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Cobertura periodo (%)": st.column_config.NumberColumn(format="%.1f %%"),
            "Horas de contrato": st.column_config.NumberColumn(format="%.1f h"),
            "Horas planificadas": st.column_config.NumberColumn(format="%.1f h"),
            "Horas faltantes": st.column_config.NumberColumn(format="%.1f h"),
            "Horas en exceso": st.column_config.NumberColumn(format="%.1f h"),
            "Deficit compatible con ausencia (h)": st.column_config.NumberColumn(format="%.1f h"),
            "Deficit sin explicar (h)": st.column_config.NumberColumn(format="%.1f h"),
        },
    )

    with st.expander("Ver detalle empleado-semana y criterios de calculo"):
        st.markdown(
            """
            - **Semana evaluable:** los siete dias de la semana estan presentes en el fichero y `applicableWorkingHours` es numerico.
            - **Contrato cubierto:** horas planificadas iguales o superiores al contrato en todas las semanas evaluables.
            - **Deficit compatible con ausencias:** el deficit puede quedar cubierto total o parcialmente por la estimacion de horas asociadas a dias de ausencia sin turno.
            - **Importante:** la compatibilidad con ausencias es una señal de diagnostico, no una imputacion de horas trabajadas ni una prueba causal.
            """
        )
        detail = evaluable.sort_values(["inicio_semana", "id_tienda", "personId"]).copy()
        detail["Semana"] = detail.apply(lambda row: f"{int(row.ano_iso)}-S{int(row.semana_iso):02d}", axis=1)
        st.dataframe(
            detail[[
                "Semana", "id_tienda", "personId", "applicableWorkingHours", "horas_planificadas",
                "estado_planificacion", "horas_no_planificadas_hasta_contrato", "horas_planificadas_en_exceso",
                "dias_ausencia_sin_turno", "tipos_ausencia", "horas_deficit_compatibles_ausencia",
                "horas_deficit_sin_explicar", "posible_explicacion_por_ausencia",
            ]],
            hide_index=True,
            use_container_width=True,
        )


def render_shifts(frames):
    shifts = frames["shifts"]
    st.subheader("Turnos")
    help_text("Un turno diario agrega todos los segmentos WORK del origen seleccionado. La duracion es la suma neta de segmentos, no el intervalo entre primera entrada y ultima salida.")
    if shifts.empty:
        st.warning("El origen seleccionado no contiene segmentos WORK.")
        return
    cols = st.columns(4)
    kpi(cols[0], "Turnos", fmt(len(shifts)), "Dias-persona", "blue")
    kpi(cols[1], "Duracion media", f"{fmt(shifts.horas_totales.mean(),2)} h", "Media por turno", "purple")
    kpi(cols[2], "Turnos < 4 h", fmt(int(shifts.horas_totales.lt(MIN_SHIFT_HOURS).sum())), "Incumplen duracion minima", "red")
    kpi(cols[3], "Turnos > 7,5 h", fmt(int(shifts.horas_totales.gt(MAX_SHIFT_HOURS).sum())), "Incumplen duracion maxima", "red")
    st.markdown("#### Distribucion de duraciones")
    help_text("Las lineas discontinuas marcan los limites de 4 y 7,5 horas. Los valores fuera del intervalo generan incidencias.")
    fig = px.histogram(shifts, x="horas_totales", nbins=25, labels={"horas_totales":"Horas netas", "count":"Turnos"}, height=370)
    fig.add_vline(x=MIN_SHIFT_HOURS, line_dash="dash")
    fig.add_vline(x=MAX_SHIFT_HOURS, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)


def render_absences(frames):
    absences, summaries = frames["absences"], frames["summaries"]
    st.subheader("Ausencias y fines de semana")
    help_text("Las ausencias proceden siempre de dayTimes.absences y no cambian al alternar el origen de horarios. Lo que si puede cambiar es si una ausencia coincide o no con un turno del origen seleccionado.")
    cols = st.columns(4)
    kpi(cols[0], "Registros de ausencia", fmt(len(absences)), "Estados VALIDATED o APPROVED", "purple")
    kpi(cols[1], "Empleados afectados", fmt(absences.personId.nunique() if not absences.empty else 0), "Personas con alguna ausencia", "purple")
    kpi(cols[2], "Media fines de semana libres", fmt(summaries.fines_semana_completos_libres.mean(),2) if not summaries.empty else "—", "Por empleado-mes", "blue")
    kpi(cols[3], "Sin fin de semana completo", fmt(int(summaries.fines_semana_completos_libres.eq(0).sum())) if not summaries.empty else "0", "Registros empleado-mes", "amber")
    if not absences.empty:
        st.markdown("#### Ausencias por tipo")
        help_text("Cuenta registros de ausencia por tipo. Dos tipos distintos en una misma fecha se mantienen como dos registros.")
        by_type = absences.groupby("tipo_ausencia", as_index=False).size().rename(columns={"size":"Registros"}).sort_values("Registros")
        st.plotly_chart(px.bar(by_type, x="Registros", y="tipo_ausencia", orientation="h", text="Registros", height=350), use_container_width=True)


st.sidebar.title("Validador")
uploaded = st.sidebar.file_uploader("Subir planificacion JSON/TXT", type=["json","txt"])
if uploaded is None:
    st.title("Validador de planificaciones")
    st.info("Sube un fichero para detectar los origenes de horarios disponibles.")
    st.stop()

try:
    data, source_stats = parse_file(uploaded.getvalue())
except Exception as exc:
    st.error(f"No se ha podido leer el fichero: {exc}")
    st.stop()

available = [source for source, stats in source_stats.items() if stats["work_segments"] > 0]
if not available:
    st.error("No se han encontrado segmentos WORK en planned, plannedDraft ni plannedDraftManuallyEdited.")
    st.stop()

selected_source = st.sidebar.selectbox(
    "Origen de horarios a evaluar",
    options=available,
    format_func=lambda key: f"{SCHEDULE_SOURCES[key]} ({key})",
    help="La seleccion determina que coleccion de horarios utiliza todo el motor de validacion.",
)

st.sidebar.markdown("**Fuentes detectadas**")
for source, stats in source_stats.items():
    symbol = "✅" if stats["work_segments"] else "—"
    st.sidebar.caption(f"{symbol} {source}: {stats['work_segments']} segmentos WORK")

try:
    with st.spinner(f"Analizando {selected_source}..."):
        result, frames = analyse(uploaded.getvalue(), selected_source)
        frames = normalise_frames(frames)
except Exception as exc:
    st.error(f"No se ha podido ejecutar el analisis: {exc}")
    st.stop()

store_id = (result.source_data.get("store") or {}).get("id", "Sin identificar")
st.sidebar.markdown(f"**Tienda:** {store_id}")
st.sidebar.caption(f"Fichero: {uploaded.name}")
st.sidebar.download_button(
    "Descargar Excel de detalle",
    data=build_excel_bytes(result),
    file_name=f"validacion_{selected_source}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

st.title("Validador de planificaciones")
st.markdown(
    f'<div class="source-box"><b>Origen analizado:</b> {SCHEDULE_SOURCES[selected_source]} '
    f'(<code>{selected_source}</code>). Todas las incidencias, horas y visualizaciones corresponden exclusivamente a esta fuente.</div>',
    unsafe_allow_html=True,
)
st.caption(f"Tienda {store_id} · Analisis generado {datetime.now():%d/%m/%Y %H:%M}")

tabs = st.tabs(["Resumen", "Restricciones", "Horas semanales", "Turnos", "Ausencias y fines de semana", "Metodologia"])
with tabs[0]: render_summary(frames)
with tabs[1]: render_restrictions(frames)
with tabs[2]: render_weekly(frames)
with tabs[3]: render_shifts(frames)
with tabs[4]: render_absences(frames)
with tabs[5]:
    st.subheader("Metodologia")
    st.markdown(f"""
    **Origen seleccionado:** `{selected_source}`. El motor lee exclusivamente `dayTimes.{selected_source}`.

    - Solo se utilizan segmentos con `hourType = WORK`.
    - La duracion diaria es la suma neta de los segmentos seleccionados.
    - Se aplican las mismas reglas: maximo {MAX_CONSECUTIVE_DAYS} dias consecutivos, entre {MIN_SHIFT_HOURS:g} y {MAX_SHIFT_HOURS:g} horas por turno y al menos {MIN_REST_HOURS:g} horas entre jornadas.
    - El control semanal compara las horas del origen seleccionado con `applicableWorkingHours`.
    - Las ausencias no se suman a la planificacion; solo se usan como posible explicacion del deficit.
    - Cambiar el selector vuelve a ejecutar todo el analisis sin mezclar fuentes.
    """)
