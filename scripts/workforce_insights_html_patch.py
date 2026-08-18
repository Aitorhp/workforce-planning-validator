from __future__ import annotations

import re


def _replace_one(source: str, old: str, new: str, label: str) -> str:
    found = source.count(old)
    if found != 1:
        raise ValueError(
            f"Parche HTML de insights '{label}': se esperaba 1 coincidencia y se encontraron {found}"
        )
    return source.replace(old, new, 1)


def _insert_mix_tab(source: str) -> str:
    candidates = (
        ('["weekends","Fines de semana"],["methodology","Metodología"]', '["weekends","Fines de semana"],["workforceMix","Mix de plantilla"],["methodology","Metodología"]'),
        ('["weekends","Fines de semana"],["methodology","Metodologia"]', '["weekends","Fines de semana"],["workforceMix","Mix de plantilla"],["methodology","Metodologia"]'),
        ('["weekends","Fines de semana"],["method","Metodología"]', '["weekends","Fines de semana"],["workforceMix","Mix de plantilla"],["method","Metodología"]'),
        ('["weekends","Fines de semana"],["method","Metodologia"]', '["weekends","Fines de semana"],["workforceMix","Mix de plantilla"],["method","Metodologia"]'),
    )
    for old, new in candidates:
        if old in source:
            return source.replace(old, new, 1)

    pattern = re.compile(
        r'(\[\s*["\']weekends["\']\s*,\s*["\']Fines de semana["\']\s*\]\s*,)'
        r'(\s*\[\s*["\'](?:methodology|method)["\']\s*,\s*["\']Metodolog(?:ía|ia)["\']\s*\])'
    )
    source, count = pattern.subn(
        r'\1["workforceMix","Mix de plantilla"],\2', source, count=1
    )
    if count != 1:
        raise ValueError(
            "Parche HTML de insights: no se encontró la lista de pestañas para insertar Mix de plantilla"
        )
    return source


def _insert_mix_dispatch(source: str) -> str:
    candidates = (
        (
            'else if(S.tab==="weekends") html=renderWeekends(F);',
            'else if(S.tab==="weekends") html=renderWeekends(F);\n'
            '  else if(S.tab==="workforceMix") html=renderWorkforceMix(F);',
        ),
        (
            "else if(S.tab==='weekends') html=renderWeekends(F);",
            "else if(S.tab==='weekends') html=renderWeekends(F);\n"
            "  else if(S.tab==='workforceMix') html=renderWorkforceMix(F);",
        ),
        (
            'else if(S.tab==="weekends")h=renderWeekends(F);',
            'else if(S.tab==="weekends")h=renderWeekends(F);\n'
            '  else if(S.tab==="workforceMix")h=renderWorkforceMix(F);',
        ),
        (
            'case "weekends": return renderWeekends(F);',
            'case "weekends": return renderWeekends(F);\n'
            '    case "workforceMix": return renderWorkforceMix(F);',
        ),
    )
    for old, new in candidates:
        if old in source:
            return source.replace(old, new, 1)

    pattern = re.compile(r'(["\']weekends["\']\s*:\s*renderWeekends\s*,)')
    source, count = pattern.subn(
        r'\1 "workforceMix":renderWorkforceMix,', source, count=1
    )
    if count != 1:
        raise ValueError(
            "Parche HTML de insights: no se encontró el enrutado de pestañas para Mix de plantilla"
        )
    return source


MIX_RENDER = r'''
function renderWorkforceMix(F){
  let h=`<div class="subhead">${t("Mix de plantilla")}</div>`+help(t("Distribución informativa de la plantilla según sus horas contractuales. Esta pantalla no aplica reglas ni genera incidencias."));
  const weekly=(F&&F.weekly)||[];
  if(!weekly.length) return h+callout("warning",t("No hay información contractual suficiente para construir el mix de plantilla."));

  const byEmployee=new Map();
  weekly.forEach((r,idx)=>{
    const store=r.id_tienda??r.store_id??r.storeId??"";
    const person=r.personId??r.person_id??r.employeeId??"";
    const raw=r.applicableWorkingHours??r._app??r.app;
    const app=raw==null||raw===""?null:Number(raw);
    if(app==null||!Number.isFinite(app)) return;
    const when=r.inicio_semana??r.week_start??r.inicio??idx;
    const key=String(store)+"|"+String(person);
    const current=byEmployee.get(key);
    if(!current||String(when)>=String(current.when)) byEmployee.set(key,{store,person,app,when});
  });
  const employees=[...byEmployee.values()];
  if(!employees.length) return h+callout("warning",t("No hay información contractual suficiente para construir el mix de plantilla."));

  const grouped=new Map();
  employees.forEach(e=>grouped.set(e.app,(grouped.get(e.app)||0)+1));
  const mix=[...grouped.entries()].map(([app,count])=>({app:Number(app),count})).sort((a,b)=>a.app-b.app);
  const totalEmployees=employees.length;
  const totalHours=employees.reduce((acc,e)=>acc+e.app,0);
  const avg=totalEmployees?totalHours/totalEmployees:0;
  mix.forEach(r=>{r.pct=totalEmployees?r.count/totalEmployees*100:0;r.hours=r.app*r.count;r.hoursPct=totalHours?r.hours/totalHours*100:0;});

  h+=kpiGrid([
    {label:t("Empleados"),value:fmt(totalEmployees),detail:t("Con horas contractuales válidas"),tone:"blue"},
    {label:t("Tipos de contrato"),value:fmt(mix.length),detail:t("Horas contractuales distintas"),tone:"blue"},
    {label:t("Horas contratadas/semana"),value:fmt(totalHours,1),detail:t("Suma de horas de contrato"),tone:"blue"},
    {label:t("Jornada media"),value:fmt(avg,1)+" h",detail:t("Media por empleado"),tone:"blue"},
  ],4);

  h+=`<div class="block"><h3>${t("Distribución por horas de contrato")}</h3><div class="wfv-mix-bars">`;
  const maxCount=Math.max(...mix.map(r=>r.count),1);
  mix.forEach(r=>{
    const width=Math.max(3,r.count/maxCount*100);
    h+=`<div class="wfv-mix-row"><div class="wfv-mix-contract">${fmt(r.app,1)} h</div><div class="wfv-mix-track"><div class="wfv-mix-fill" style="width:${width}%"><span>${fmt(r.count)} · ${pctText(r.pct)}</span></div></div></div>`;
  });
  h+=`</div></div>`;

  const rows=mix.map(r=>({"Horas contrato":r.app,"Empleados":r.count,"% plantilla":r.pct,"Horas contratadas/semana":r.hours,"% horas contratadas":r.hoursPct}));
  h+=`<div class="block"><h3>${t("Detalle del mix")}</h3>`+
      table([tc("Horas contrato"),tc("Empleados"),tc("% plantilla"),tc("Horas contratadas/semana"),tc("% horas contratadas")],rows,{height:420,numCols:["Horas contrato","Empleados","% plantilla","Horas contratadas/semana","% horas contratadas"]})+
      `<div class="chart-note">${t("El porcentaje de plantilla se calcula sobre empleados con horas contractuales válidas. El porcentaje de horas muestra el peso de cada tipo de contrato sobre la capacidad contractual semanal total.")}</div></div>`;
  return h;
}
'''


def patch_workforce_insights(source: str) -> str:
    """Mantiene en paridad HTML los insights de fines de semana y mix de plantilla."""
    old_chart = 'h+=chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:390,dec:0})+`</div>`;'
    new_chart = '''const totalEmployees=Math.max(employees.length,1);\n    rot.forEach(r=>r.pct=r.comp/totalEmployees*100);\n    h+=`<div class="wfv-weekend-grid"><div>`+chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:255,dec:0})+`</div><div><div class="chart-note">${t("Peso de la plantilla con fin de semana completo libre")}</div><div class="wfv-weekend-share">`+rot.map(r=>`<div class="wfv-weekend-share-row"><span>${esc(r.label)}</span><div class="wfv-weekend-share-track"><i style="width:${Math.min(100,Math.max(0,r.pct))}%"></i></div><strong>${r.comp} · ${pctText(r.pct)}</strong></div>`).join("")+`</div></div></div><div class="chart-note">${t("Porcentaje calculado sobre {n} empleado(s) incluidos en el rango contractual seleccionado.",{n:employees.length})}</div></div>`;'''
    source = _replace_one(
        source, old_chart, new_chart, "rotación y porcentaje de fin de semana"
    )

    css = r'''
<style id="wfv-workforce-insights-style">
.wfv-weekend-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(320px,1fr);gap:16px;align-items:start}
.wfv-weekend-share{display:flex;flex-direction:column;gap:9px;margin-top:8px}
.wfv-weekend-share-row{display:grid;grid-template-columns:minmax(85px,120px) minmax(100px,1fr) minmax(72px,92px);gap:8px;align-items:center;font-size:.82rem}
.wfv-weekend-share-track,.wfv-mix-track{height:24px;background:#e2e8f0;border-radius:7px;overflow:hidden}
.wfv-weekend-share-track i{display:block;height:100%;background:#2563eb;border-radius:7px}
.wfv-weekend-share-row strong{text-align:right;font-variant-numeric:tabular-nums}
.wfv-mix-bars{display:flex;flex-direction:column;gap:10px;margin-top:10px}
.wfv-mix-row{display:grid;grid-template-columns:95px minmax(160px,1fr);gap:12px;align-items:center}
.wfv-mix-contract{font-weight:700;text-align:right}
.wfv-mix-fill{height:100%;min-width:42px;background:#2563eb;border-radius:7px;display:flex;align-items:center;padding:0 8px;color:#fff;font-size:.78rem;font-weight:700;white-space:nowrap}
@media(max-width:900px){.wfv-weekend-grid{grid-template-columns:1fr}.wfv-weekend-share-row{grid-template-columns:90px 1fr 82px}}
</style>
'''
    source = _replace_one(source, "</head>", css + "</head>", "estilos de insights")

    translations = (
        '  "Mix de plantilla":"Workforce mix",\n'
        '  "Distribución informativa de la plantilla según sus horas contractuales. Esta pantalla no aplica reglas ni genera incidencias.":"Informational workforce distribution by contracted weekly hours. This screen does not apply rules or generate incidents.",\n'
        '  "No hay información contractual suficiente para construir el mix de plantilla.":"There is not enough contract information to build the workforce mix.",\n'
        '  "Tipos de contrato":"Contract types","Con horas contractuales válidas":"With valid contracted hours",\n'
        '  "Horas contractuales distintas":"Distinct contracted-hour values","Horas contratadas/semana":"Contracted hours/week",\n'
        '  "Suma de horas de contrato":"Sum of contracted hours","Jornada media":"Average contract","Media por empleado":"Average per employee",\n'
        '  "Distribución por horas de contrato":"Distribution by contracted hours","Detalle del mix":"Mix detail",\n'
        '  "% plantilla":"% workforce","% horas contratadas":"% contracted hours",\n'
        '  "El porcentaje de plantilla se calcula sobre empleados con horas contractuales válidas. El porcentaje de horas muestra el peso de cada tipo de contrato sobre la capacidad contractual semanal total.":"Workforce percentage is calculated over employees with valid contracted hours. Hours percentage shows each contract type share of total weekly contracted capacity.",\n'
        '  "Peso de la plantilla con fin de semana completo libre":"Share of workforce with a full weekend off",\n'
        '  "Porcentaje calculado sobre {n} empleado(s) incluidos en el rango contractual seleccionado.":"Percentage calculated over {n} employee(s) included in the selected contract-hour range.",\n'
    )
    anchor = '  // ---- Metodología ----\n'
    source = _replace_one(source, anchor, translations + anchor, "traducciones")

    methodology_marker = "/* ---------- Metodología ---------- */"
    source = _replace_one(
        source,
        methodology_marker,
        MIX_RENDER + "\n\n" + methodology_marker,
        "renderer Mix de plantilla",
    )
    source = _insert_mix_tab(source)
    source = _insert_mix_dispatch(source)
    return source
