from __future__ import annotations


def _replace_one(source: str, old: str, new: str, label: str) -> str:
    found = source.count(old)
    if found != 1:
        raise ValueError(
            f"Parche HTML de insights '{label}': se esperaba 1 coincidencia y se encontraron {found}"
        )
    return source.replace(old, new, 1)


def _insert_mix_tab(source: str) -> str:
    old = 'const TAB_KEYS=["Resumen","Restricciones","Horas contractuales","Cobertura diaria","Balance mañana/tarde","Ausencias","Fines de semana","Metodología"];'
    new = 'const TAB_KEYS=["Resumen","Restricciones","Horas contractuales","Cobertura diaria","Balance mañana/tarde","Ausencias","Fines de semana","Mix de plantilla","Metodología"];'
    return _replace_one(source, old, new, "pestaña Mix de plantilla")


def _insert_mix_dispatch(source: str) -> str:
    source = _replace_one(
        source,
        'const RENDERERS=[renderResumen,renderRestricciones,renderHoras,renderCobertura,renderBalance,renderAusencias,renderWeekends,renderMetodologia];',
        'const RENDERERS=[renderResumen,renderRestricciones,renderHoras,renderCobertura,renderBalance,renderAusencias,renderWeekends,renderWorkforceMix,renderMetodologia];',
        "lista de renderers",
    )
    source = _replace_one(
        source,
        'panel.innerHTML = S.tab===7? renderMetodologia() : RENDERERS[S.tab](F);',
        'panel.innerHTML = S.tab===8? renderMetodologia() : RENDERERS[S.tab](F);',
        "índice de Metodología",
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
    new_chart = '''const totalEmployees=Math.max(employees.length,1);\n    rot.forEach(r=>r.pct=r.comp/totalEmployees*100);\n    h+=chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:255,dec:0})+`</div>`;\n\n    h+=`<div class="block"><h3>${t("Magnitud del descanso por fin de semana")}</h3><div class="chart-note">${t("Empleados con sábado y domingo libres en cada fin de semana y peso que representan sobre la plantilla analizada.")}</div><div class="wfv-weekend-share">`+rot.map(r=>`<div class="wfv-weekend-share-row"><span>${esc(r.label)}</span><div class="wfv-weekend-share-track"><i style="width:${Math.min(100,Math.max(0,r.pct))}%"></i></div><strong>${r.comp} · ${pctText(r.pct)}</strong></div>`).join("")+`</div><div class="chart-note">${t("Base del porcentaje: {n} empleado(s) incluidos en el rango contractual seleccionado.",{n:employees.length})}</div></div>`;'''
    source = _replace_one(
        source, old_chart, new_chart, "rotación y magnitud de fin de semana"
    )

    css = r'''
<style id="wfv-workforce-insights-style">
.wfv-weekend-share{display:flex;flex-direction:column;gap:9px;margin-top:14px}
.wfv-weekend-share-row{display:grid;grid-template-columns:minmax(100px,150px) minmax(160px,1fr) minmax(88px,115px);gap:10px;align-items:center;font-size:.84rem}
.wfv-weekend-share-track,.wfv-mix-track{height:26px;background:#e2e8f0;border-radius:7px;overflow:hidden}
.wfv-weekend-share-track i{display:block;height:100%;background:#2563eb;border-radius:7px}
.wfv-weekend-share-row strong{text-align:right;font-variant-numeric:tabular-nums}
.wfv-mix-bars{display:flex;flex-direction:column;gap:10px;margin-top:10px}
.wfv-mix-row{display:grid;grid-template-columns:95px minmax(160px,1fr);gap:12px;align-items:center}
.wfv-mix-contract{font-weight:700;text-align:right}
.wfv-mix-fill{height:100%;min-width:42px;background:#2563eb;border-radius:7px;display:flex;align-items:center;padding:0 8px;color:#fff;font-size:.78rem;font-weight:700;white-space:nowrap}
@media(max-width:700px){.wfv-weekend-share-row{grid-template-columns:85px minmax(90px,1fr) 82px}.wfv-mix-row{grid-template-columns:75px minmax(120px,1fr)}}
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
        '  "Magnitud del descanso por fin de semana":"Weekend rest magnitude",\n'
        '  "Empleados con sábado y domingo libres en cada fin de semana y peso que representan sobre la plantilla analizada.":"Employees with both Saturday and Sunday off for each weekend and their share of the analysed workforce.",\n'
        '  "Base del porcentaje: {n} empleado(s) incluidos en el rango contractual seleccionado.":"Percentage base: {n} employee(s) included in the selected contract-hour range.",\n'
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
