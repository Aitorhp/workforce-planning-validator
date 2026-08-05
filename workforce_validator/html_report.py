from __future__ import annotations

from datetime import date
from html import escape
from typing import Any, Iterable

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs


TR = {
    "es": {
        "overview": "Resumen", "restrictions": "Restricciones", "weekly": "Horas contractuales",
        "coverage": "Cobertura diaria", "balance": "Balance mañana/tarde", "absences": "Ausencias",
        "weekends": "Fines de semana", "method": "Metodología", "employees": "Empleados",
        "shifts": "Turnos", "planned": "Horas planificadas", "ok": "Sin incidencias",
        "ko": "Con incidencias", "incidents": "Incidencias", "detail": "Detalle",
        "no_data": "No hay datos disponibles.", "contract": "Horas de contrato",
        "missing": "Horas faltantes", "excess": "Horas en exceso", "absence_hours": "Horas estimadas de ausencia",
        "employee": "Empleado", "full_weekends": "Fines completos", "search": "Buscar empleado",
        "only_alerts": "Solo empleados sin fin de semana completo libre", "map_help":
        "Cada celda muestra 0, 1 o 2 días libres. La primera columna queda fija y las situaciones más críticas aparecen primero.",
        "zero": "0 días", "one": "1 día", "two": "2 días", "monthly": "Resumen empleado-mes",
        "restriction_chart": "Incidencias por restricción", "contract_chart": "Contrato y planificación por semana",
        "variance_chart": "Magnitud de los desajustes", "coverage_chart": "Evolución diaria de horas planificadas",
        "balance_chart": "Distribución de turnos", "absence_chart": "Ausencias por tipo",
    },
    "en": {
        "overview": "Overview", "restrictions": "Restrictions", "weekly": "Contract hours",
        "coverage": "Daily coverage", "balance": "Morning/afternoon balance", "absences": "Absences",
        "weekends": "Weekends", "method": "Methodology", "employees": "Employees",
        "shifts": "Shifts", "planned": "Planned hours", "ok": "No incidents",
        "ko": "With incidents", "incidents": "Incidents", "detail": "Detail",
        "no_data": "No data are available.", "contract": "Contract hours",
        "missing": "Missing hours", "excess": "Excess hours", "absence_hours": "Estimated absence hours",
        "employee": "Employee", "full_weekends": "Full weekends", "search": "Search employee",
        "only_alerts": "Only employees without a full weekend off", "map_help":
        "Each cell shows 0, 1 or 2 days off. The first column remains fixed and the most critical situations appear first.",
        "zero": "0 days", "one": "1 day", "two": "2 days", "monthly": "Employee-month summary",
        "restriction_chart": "Incidents by restriction", "contract_chart": "Contract and planned hours by week",
        "variance_chart": "Magnitude of variances", "coverage_chart": "Daily planned-hours trend",
        "balance_chart": "Shift distribution", "absence_chart": "Absences by type",
    },
}

INCIDENTS = {
    "es": {"MAS_DE_5_DIAS_CONSECUTIVOS": "Más de 5 días consecutivos", "TURNO_SUPERIOR_7_5H": "Turno superior a 7,5 h", "TURNO_INFERIOR_4H": "Turno inferior a 4 h", "DESCANSO_INFERIOR_11H": "Descanso inferior a 11 h"},
    "en": {"MAS_DE_5_DIAS_CONSECUTIVOS": "More than 5 consecutive days", "TURNO_SUPERIOR_7_5H": "Shift longer than 7.5 h", "TURNO_INFERIOR_4H": "Shift shorter than 4 h", "DESCANSO_INFERIOR_11H": "Rest shorter than 11 h"},
}


def _frames(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = {key: value.copy() for key, value in frames.items()}
    for frame in out.values():
        for column in ("day", "fecha", "fecha_inicio", "fecha_fin", "inicio_semana", "fin_semana"):
            if column in frame and not frame.empty:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return out


def _dates(values: Iterable[date] | None) -> list[pd.Timestamp]:
    return sorted({pd.Timestamp(value).normalize() for value in (values if values is not None else [])})


def _plot(fig: go.Figure) -> str:
    fig.update_layout(template="plotly_white", margin=dict(l=25, r=15, t=25, b=35), font=dict(family="Arial", size=12))
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False, "responsive": True})


def _table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return ""
    view = frame.copy()
    if columns:
        view = view[[column for column in columns if column in view]]
    for column in view:
        if pd.api.types.is_datetime64_any_dtype(view[column]):
            view[column] = view[column].dt.strftime("%d/%m/%Y")
    return view.to_html(index=False, border=0, classes="data-table", escape=True)


def _card(label: str, value: str, tone: str) -> str:
    return f'<article class="kpi {tone}"><span>{escape(label)}</span><strong>{escape(value)}</strong></article>'


def _weekend_rows(shifts: pd.DataFrame, weekly: pd.DataFrame, data_dates: Iterable[date] | None) -> pd.DataFrame:
    dates = _dates(data_dates)
    saturdays = [day for day in dates if day.weekday() == 5 and day + pd.Timedelta(days=1) in dates]
    if not saturdays:
        return pd.DataFrame()
    if not weekly.empty and {"id_tienda", "personId"}.issubset(weekly.columns):
        cols = ["id_tienda", "personId"] + (["applicableWorkingHours"] if "applicableWorkingHours" in weekly else [])
        employees = weekly[cols].copy()
    elif not shifts.empty:
        employees = shifts[["id_tienda", "personId", "applicableWorkingHours"]].copy()
    else:
        return pd.DataFrame()
    if "applicableWorkingHours" not in employees:
        employees["applicableWorkingHours"] = pd.NA
    employees["applicableWorkingHours"] = pd.to_numeric(employees["applicableWorkingHours"], errors="coerce")
    employees = employees.sort_values("applicableWorkingHours").drop_duplicates(["id_tienda", "personId"], keep="last")
    worked = set()
    if not shifts.empty:
        for row in shifts[["id_tienda", "personId", "day"]].itertuples(index=False):
            worked.add((str(row.id_tienda), str(row.personId), pd.Timestamp(row.day).normalize()))
    rows = []
    for employee in employees.itertuples(index=False):
        for saturday in saturdays:
            store, person = str(employee.id_tienda), str(employee.personId)
            sunday = saturday + pd.Timedelta(days=1)
            days_off = int((store, person, saturday) not in worked) + int((store, person, sunday) not in worked)
            rows.append({"id_tienda": employee.id_tienda, "personId": employee.personId, "applicableWorkingHours": employee.applicableWorkingHours, "inicio_fin_semana": saturday, "Fin de semana": f"{saturday:%d/%m} - {sunday:%d/%m}", "dias_libres": days_off})
    return pd.DataFrame(rows)


def build_weekend_map_html(weekends: pd.DataFrame, language: str = "es", include_controls: bool = True) -> str:
    lang = language if language in TR else "es"
    t = TR[lang]
    if weekends.empty:
        return f'<div class="empty">{escape(t["no_data"])}</div>'
    data = weekends.copy()
    if "dias_libres" not in data:
        sat = data["sabado_libre"].astype(int) if "sabado_libre" in data else pd.Series(0, index=data.index)
        sun = data["domingo_libre"].astype(int) if "domingo_libre" in data else pd.Series(0, index=data.index)
        data["dias_libres"] = sat + sun
    data["inicio_fin_semana"] = pd.to_datetime(data["inicio_fin_semana"], errors="coerce")
    order = data[["inicio_fin_semana", "Fin de semana"]].drop_duplicates().sort_values("inicio_fin_semana")["Fin de semana"].tolist()
    idx = ["id_tienda", "personId"] + (["applicableWorkingHours"] if "applicableWorkingHours" in data else [])
    matrix = data.pivot_table(index=idx, columns="Fin de semana", values="dias_libres", aggfunc="first").reindex(columns=order).fillna(0).astype(int).reset_index()
    matrix["_complete"] = matrix[order].eq(2).sum(axis=1)
    matrix["_days"] = matrix[order].sum(axis=1)
    matrix = matrix.sort_values(["_complete", "_days", "personId"])
    controls = ""
    if include_controls:
        controls = f'<div class="weekend-controls"><input class="weekend-search" type="search" placeholder="{escape(t["search"])}"><label><input class="weekend-alerts" type="checkbox"> {escape(t["only_alerts"])}</label></div>'
    head = f'<th class="employee-col">{escape(t["employee"])}</th>' + "".join(f"<th>{escape(label)}</th>" for label in order) + f'<th class="summary-col">{escape(t["full_weekends"])}</th>'
    body = []
    for _, row in matrix.iterrows():
        contract = "—" if pd.isna(row.get("applicableWorkingHours")) else f'{float(row["applicableWorkingHours"]):g} h'
        employee = f'{row["id_tienda"]} · {row["personId"]} · {contract}'
        cells = [f'<th class="employee-col">{escape(employee)}</th>']
        for label in order:
            value = int(row[label]); title = t["zero"] if value == 0 else t["one"] if value == 1 else t["two"]
            cells.append(f'<td class="days-{value}" title="{escape(title)}"><span>{value}</span></td>')
        complete = int(row["_complete"]); cells.append(f'<td class="summary-col"><strong>{complete}</strong></td>')
        body.append(f'<tr data-employee="{escape(employee.lower())}" data-alert="{int(complete == 0)}">{"".join(cells)}</tr>')
    legend = f'<div class="weekend-legend"><span><i class="legend-0"></i>{escape(t["zero"])}</span><span><i class="legend-1"></i>{escape(t["one"])}</span><span><i class="legend-2"></i>{escape(t["two"])}</span></div>'
    return f'<div class="weekend-widget">{controls}<div class="weekend-scroll"><table class="weekend-table"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>{legend}</div>'


WEEKEND_CSS = r'''.weekend-widget{border:1px solid #d9e0ea;border-radius:12px;padding:12px;background:#fff}.weekend-controls{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.weekend-controls input[type=search]{min-width:280px;border:1px solid #d9e0ea;border-radius:8px;padding:9px}.weekend-controls label{font-size:13px;font-weight:700}.weekend-scroll{max-height:68vh;overflow:auto;border:1px solid #d9e0ea;border-radius:10px}.weekend-table{border-collapse:separate;border-spacing:0;width:max-content;min-width:100%;font-size:12px}.weekend-table th,.weekend-table td{border-right:2px solid #fff;border-bottom:2px solid #fff;height:38px;min-width:104px;text-align:center}.weekend-table thead th{position:sticky;top:0;z-index:4;background:#fff;color:#536078;padding:8px}.weekend-table .employee-col{position:sticky;left:0;z-index:3;min-width:245px;max-width:245px;text-align:left;background:#fff;padding:0 12px;border-right:1px solid #d9e0ea;box-shadow:4px 0 8px rgba(23,32,51,.05)}.weekend-table thead .employee-col{z-index:6}.weekend-table .summary-col{position:sticky;right:0;z-index:3;min-width:105px;background:#f8fafc;border-left:1px solid #d9e0ea}.weekend-table thead .summary-col{z-index:6}.weekend-table td span{display:inline-flex;width:100%;height:100%;align-items:center;justify-content:center;font-weight:700}.days-0{background:#cbd5e1;color:#334155}.days-1{background:#8abcf3;color:#17355f}.days-2{background:#2456df;color:#fff}.weekend-table tbody tr:hover .employee-col{background:#eef4ff}.weekend-table tbody tr.hidden{display:none}.weekend-legend{display:flex;gap:16px;margin-top:10px;font-size:12px}.weekend-legend span{display:flex;align-items:center;gap:6px}.weekend-legend i{width:16px;height:16px;border-radius:4px;display:inline-block}.legend-0{background:#cbd5e1}.legend-1{background:#8abcf3}.legend-2{background:#2456df}'''
WEEKEND_JS = r'''document.querySelectorAll('.weekend-widget').forEach(w=>{const s=w.querySelector('.weekend-search'),a=w.querySelector('.weekend-alerts'),f=()=>{const q=(s?.value||'').trim().toLowerCase(),only=a?.checked||false;w.querySelectorAll('tbody tr').forEach(r=>r.classList.toggle('hidden',!((!q||r.dataset.employee.includes(q))&&(!only||r.dataset.alert==='1'))))};s?.addEventListener('input',f);a?.addEventListener('change',f)});'''


def build_weekend_map_component(weekends: pd.DataFrame, language: str = "es") -> str:
    widget = build_weekend_map_html(weekends, language, True)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box}}body{{margin:0;font-family:Arial;color:#172033}}.empty{{padding:28px;text-align:center;color:#657086}}{WEEKEND_CSS}</style></head><body>{widget}<script>{WEEKEND_JS}</script></body></html>'


def _overview(frames: dict[str, pd.DataFrame], lang: str) -> str:
    t = TR[lang]; shifts = frames.get("shifts", pd.DataFrame()); summaries = frames.get("summaries", pd.DataFrame()); incidents = frames.get("incidents", pd.DataFrame())
    employees = summaries[["id_tienda", "personId"]].drop_duplicates() if not summaries.empty else shifts[["id_tienda", "personId"]].drop_duplicates() if not shifts.empty else pd.DataFrame()
    ok = 0
    if not summaries.empty and "cumple_todas_las_reglas" in summaries:
        ok = int(summaries.assign(_ok=summaries["cumple_todas_las_reglas"].eq("SI")).groupby(["id_tienda", "personId"])["_ok"].all().sum())
    planned = pd.to_numeric(shifts.get("horas_totales", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    cards = "".join([_card(t["employees"], str(len(employees)), "blue"), _card(t["shifts"], str(len(shifts)), "blue"), _card(t["planned"], f"{planned:.1f} h", "purple"), _card(t["ok"], str(ok), "green"), _card(t["ko"], str(max(len(employees)-ok, 0)), "amber"), _card(t["incidents"], str(len(incidents)), "red")])
    chart = ""
    if not incidents.empty and "tipo_incidencia" in incidents:
        counts = incidents["tipo_incidencia"].map(INCIDENTS[lang]).fillna(incidents["tipo_incidencia"]).value_counts().sort_values()
        chart = f'<section class="panel"><h3>{escape(t["restriction_chart"])}</h3>{_plot(go.Figure(go.Bar(x=counts.values,y=counts.index,orientation="h")))}</section>'
    return f'<div class="kpi-grid">{cards}</div><div class="two-col">{chart}</div>'


def _restrictions(frames: dict[str, pd.DataFrame], lang: str) -> str:
    frame = frames.get("incidents", pd.DataFrame()).copy(); t = TR[lang]
    if frame.empty: return f'<div class="empty">{escape(t["no_data"])}</div>'
    frame["tipo_incidencia"] = frame["tipo_incidencia"].map(INCIDENTS[lang]).fillna(frame["tipo_incidencia"])
    return _table(frame)


def _weekly(frames: dict[str, pd.DataFrame], lang: str) -> str:
    frame = frames.get("weekly", pd.DataFrame()).copy(); t = TR[lang]
    if frame.empty: return f'<div class="empty">{escape(t["no_data"])}</div>'
    numeric = ["applicableWorkingHours", "horas_planificadas", "horas_no_planificadas_hasta_contrato", "horas_planificadas_en_exceso", "horas_potenciales_asociadas_ausencia"]
    for column in numeric:
        if column in frame: frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    keys = [column for column in ("ano_iso", "semana_iso", "inicio_semana", "fin_semana") if column in frame]
    if not keys: return _table(frame)
    agg = {name: (source, "sum") for name, source in (("contract", "applicableWorkingHours"), ("planned", "horas_planificadas"), ("missing", "horas_no_planificadas_hasta_contrato"), ("excess", "horas_planificadas_en_exceso"), ("absence", "horas_potenciales_asociadas_ausencia")) if source in frame}
    total = frame.groupby(keys, as_index=False).agg(**agg); total["week"] = total.apply(lambda r: f'{int(r.ano_iso)}-W{int(r.semana_iso):02d}', axis=1) if {"ano_iso", "semana_iso"}.issubset(total) else total.index.astype(str)
    left = go.Figure(); right = go.Figure()
    if "contract" in total: left.add_trace(go.Scatter(x=total["week"],y=total["contract"],mode="lines+markers",name=t["contract"]))
    if "planned" in total: left.add_trace(go.Scatter(x=total["week"],y=total["planned"],mode="lines+markers",name=t["planned"]))
    for key, label in (("missing",t["missing"]),("excess",t["excess"]),("absence",t["absence_hours"])):
        if key in total: right.add_trace(go.Bar(x=total["week"],y=total[key],name=label))
    right.update_layout(barmode="group")
    return f'<div class="two-col"><section class="panel"><h3>{escape(t["contract_chart"])}</h3>{_plot(left)}</section><section class="panel"><h3>{escape(t["variance_chart"])}</h3>{_plot(right)}</section></div><details><summary>{escape(t["detail"])}</summary>{_table(frame)}</details>'


def _coverage(frames: dict[str, pd.DataFrame], data_dates: Iterable[date] | None, lang: str) -> str:
    t=TR[lang]; shifts=frames.get("shifts",pd.DataFrame()).copy(); dates=_dates(data_dates)
    if not dates: return f'<div class="empty">{escape(t["no_data"])}</div>'
    base=pd.DataFrame({"day":dates}); grouped=pd.DataFrame(columns=["day","hours"])
    if not shifts.empty:
        shifts["day"]=pd.to_datetime(shifts["day"]).dt.normalize(); grouped=shifts.groupby("day",as_index=False).agg(hours=("horas_totales","sum"))
    daily=base.merge(grouped,on="day",how="left").fillna(0); fig=go.Figure(go.Scatter(x=daily["day"],y=daily["hours"],mode="lines+markers",fill="tozeroy",name=t["planned"]))
    return f'<section class="panel"><h3>{escape(t["coverage_chart"])}</h3>{_plot(fig)}</section>'


def _balance(frames: dict[str, pd.DataFrame], lang: str) -> str:
    t=TR[lang]; frame=frames.get("shift_balance",pd.DataFrame()).copy()
    if frame.empty: return f'<div class="empty">{escape(t["no_data"])}</div>'
    chart=""
    if "estado_rotacion" in frame:
        if lang=="en": frame["estado_rotacion"]=frame["estado_rotacion"].replace({"Mañana y tarde":"Morning and afternoon","Solo mañanas":"Morning only","Solo tardes":"Afternoon only"})
        counts=frame["estado_rotacion"].value_counts(); chart=f'<section class="panel"><h3>{escape(t["balance_chart"])}</h3>{_plot(go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=.55)))}</section>'
    return chart+f'<details open><summary>{escape(t["detail"])}</summary>{_table(frame)}</details>'


def _absences(frames: dict[str, pd.DataFrame], lang: str) -> str:
    t=TR[lang]; frame=frames.get("absences",pd.DataFrame()).copy()
    if frame.empty: return f'<div class="empty">{escape(t["no_data"])}</div>'
    counts=frame["tipo_ausencia"].value_counts().sort_values() if "tipo_ausencia" in frame else pd.Series(dtype=int)
    chart=_plot(go.Figure(go.Bar(x=counts.values,y=counts.index,orientation="h"))) if not counts.empty else ""
    return f'<section class="panel"><h3>{escape(t["absence_chart"])}</h3>{chart}</section><details><summary>{escape(t["detail"])}</summary>{_table(frame)}</details>'


def _weekends(frames: dict[str, pd.DataFrame], data_dates: Iterable[date] | None, lang: str) -> str:
    t=TR[lang]; rows=_weekend_rows(frames.get("shifts",pd.DataFrame()),frames.get("weekly",pd.DataFrame()),data_dates); summaries=frames.get("summaries",pd.DataFrame())
    detail=f'<details><summary>{escape(t["monthly"])}</summary>{_table(summaries,["mes","id_tienda","personId","applicableWorkingHours","fines_semana_completos_libres","sabados_libres","domingos_libres"])}</details>' if not summaries.empty else ""
    return f'<p class="help">{escape(t["map_help"])}</p>{build_weekend_map_html(rows,lang,True)}{detail}'


def _language(lang: str, frames: dict[str, pd.DataFrame], data_dates: Iterable[date] | None) -> str:
    t=TR[lang]; sections=[("overview",t["overview"],_overview(frames,lang)),("restrictions",t["restrictions"],_restrictions(frames,lang)),("weekly",t["weekly"],_weekly(frames,lang)),("coverage",t["coverage"],_coverage(frames,data_dates,lang)),("balance",t["balance"],_balance(frames,lang)),("absences",t["absences"],_absences(frames,lang)),("weekends",t["weekends"],_weekends(frames,data_dates,lang)),("method",t["method"],f'<ul><li>{"El informe reutiliza el motor Python sin modificar sus cálculos." if lang=="es" else "The report reuses the Python engine without changing its calculations."}</li><li>{"Las ausencias no se suman como horas trabajadas." if lang=="es" else "Absences are not added as worked hours."}</li><li>{"El HTML puede abrirse sin instalar Streamlit." if lang=="es" else "The HTML can be opened without installing Streamlit."}</li></ul>')]
    nav=[]; body=[]
    for index,(key,label,content) in enumerate(sections):
        active=" active" if index==0 else ""; nav.append(f'<button class="tab-button{active}" data-tab="{lang}-{key}">{escape(label)}</button>'); body.append(f'<section id="{lang}-{key}" class="tab-panel{active}"><h2>{escape(label)}</h2>{content}</section>')
    return f'<div class="language-panel" data-language="{lang}"><nav class="tabs">{"".join(nav)}</nav>{"".join(body)}</div>'


REPORT_CSS = r''':root{--ink:#172033;--muted:#657086;--line:#d9e0ea;--blue:#2456df}*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:var(--ink);font-family:Arial}.app-header{position:sticky;top:0;z-index:50;background:#fff;border-bottom:1px solid var(--line);padding:12px 20px}.header-row{display:flex;align-items:center;gap:18px}.language-switch{display:flex;gap:6px}.language-switch button,.tab-button{border:1px solid var(--line);background:#fff;border-radius:8px;padding:8px 12px;font-weight:700;cursor:pointer}.language-switch button.active{background:var(--ink);color:#fff}.app-header h1{font-size:20px;margin:0}.metadata{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:8px}.report-shell{max-width:1600px;margin:auto;padding:18px}.language-panel{display:none}.language-panel.active{display:block}.tabs{display:flex;gap:8px;overflow-x:auto;padding-bottom:12px}.tab-button.active{background:var(--blue);color:#fff}.tab-panel{display:none;background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px}.tab-panel.active{display:block}.tab-panel h2{margin-top:0}.kpi-grid{display:grid;grid-template-columns:repeat(6,minmax(145px,1fr));gap:12px}.kpi{border-radius:12px;padding:14px;min-height:95px;border:1px solid #d8e0ea}.kpi span{display:block;font-size:12px;font-weight:700}.kpi strong{display:block;font-size:28px;margin-top:10px}.blue{background:#e9f1ff}.green{background:#e6f6ed}.red{background:#fdebea}.amber{background:#fff2df}.purple{background:#f1eafe}.two-col{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px}.panel{border:1px solid var(--line);border-radius:12px;padding:14px;min-width:0}.panel h3{margin-top:0}.data-table{width:100%;border-collapse:collapse;font-size:12px}.data-table th{background:#eef3f9;text-align:left}.data-table th,.data-table td{border-bottom:1px solid var(--line);padding:8px}details{margin-top:16px;border:1px solid var(--line);border-radius:10px;padding:10px;overflow:auto}summary{font-weight:700;cursor:pointer}.empty{padding:28px;text-align:center;color:var(--muted)}.help{color:var(--muted)}''' + WEEKEND_CSS + r'''@media(max-width:1000px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.two-col{grid-template-columns:1fr}.report-shell{padding:10px}}'''
REPORT_JS = r'''function resizePlots(){setTimeout(()=>document.querySelectorAll('.js-plotly-plot').forEach(e=>window.Plotly&&Plotly.Plots.resize(e)),30)}function setLanguage(l){document.querySelectorAll('.language-panel').forEach(p=>p.classList.toggle('active',p.dataset.language===l));document.querySelectorAll('.language-switch button').forEach(b=>b.classList.toggle('active',b.dataset.language===l));resizePlots()}document.querySelectorAll('.language-switch button').forEach(b=>b.addEventListener('click',()=>setLanguage(b.dataset.language)));document.querySelectorAll('.tab-button').forEach(b=>b.addEventListener('click',()=>{const p=b.closest('.language-panel');p.querySelectorAll('.tab-button,.tab-panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');resizePlots()}));''' + WEEKEND_JS + "setLanguage('es');"


def build_html_report(result: Any, frames: dict[str, pd.DataFrame], schedule_source_label: str, file_names: Iterable[str] | None = None, data_dates: Iterable[date] | None = None) -> bytes:
    current=_frames(frames); dates=set(data_dates if data_dates is not None else getattr(result,"data_dates",set())); values=_dates(dates); source=getattr(result,"source_data",{}) or {}; store=(source.get("store") or {}).get("id","—"); period=f'{values[0]:%d/%m/%Y} - {values[-1]:%d/%m/%Y}' if values else "—"; names=", ".join(map(str,file_names or [])) or "—"
    metadata=f'<div class="metadata"><span><b>Store / Tienda:</b> {escape(str(store))}</span><span><b>Period / Periodo:</b> {escape(period)}</span><span><b>Source / Origen:</b> {escape(schedule_source_label)}</span><span><b>Files / Ficheros:</b> {escape(names)}</span></div>'
    body=_language("es",current,dates)+_language("en",current,dates)
    html=f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Workforce Planning Validator</title><style>{REPORT_CSS}</style><script>{get_plotlyjs()}</script></head><body><header class="app-header"><div class="header-row"><div class="language-switch"><button class="active" data-language="es">ES</button><button data-language="en">EN</button></div><h1>Workforce Planning Validator</h1></div>{metadata}</header><div class="report-shell">{body}</div><script>{REPORT_JS}</script></body></html>'
    return html.encode("utf-8")
