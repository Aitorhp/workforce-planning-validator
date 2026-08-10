from __future__ import annotations

import re


def _replace(source: str, old: str, new: str, *, expected: int, label: str) -> str:
    found = source.count(old)
    if found != expected:
        raise ValueError(
            f"Parche HTML de fines de semana '{label}': se esperaban {expected} coincidencias y se encontraron {found}"
        )
    return source.replace(old, new)


WEEKEND_RENDER = r'''function renderWeekends(F){
  let h=`<div class="subhead">${t("Fines de semana y rotación de descansos")}</div>`+help(t("Las reglas se evalúan sobre días concretos de descanso. Un mismo sábado o domingo no puede utilizarse para cumplir dos reglas distintas. Si existe alguna asignación válida de los descansos, el empleado se considera conforme."));

  const {monthly,detail}=prepWeekend(F);
  if(!monthly.length) return h+callout("warning",t("No hay información suficiente para calcular fines de semana."));

  const availHours=monthly.map(m=>m.app).filter(v=>v!=null&&isFinite(v));
  const obsMax=availHours.length?Math.max(...availHours):40; const limit=Math.max(80,obsMax);
  if(S.f.wkendMin==null) S.f.wkendMin=Math.min(30,limit);
  if(S.f.wkendMax==null) S.f.wkendMax=limit;

  h+=`<div class="controls">
    <div class="ctrl"><label>${t("Horas contractuales mínimas")}</label><input type="number" id="wkendMin" min="0" max="${limit}" step="1" value="${S.f.wkendMin}"></div>
    <div class="ctrl"><label>${t("Horas contractuales máximas")}</label><input type="number" id="wkendMax" min="0" max="${limit}" step="1" value="${S.f.wkendMax}"></div>
  </div>`;

  h+=`<div class="block"><h3>${t("Reglas de descanso de fin de semana")}</h3>${help(t("Introduce el mínimo exigido. Un valor 0 desactiva la regla. Sábados o domingos admite cualquier combinación de ambos días; por defecto un fin de semana completo aporta 2 días a esa regla."))}
  <div class="controls" style="grid-template-columns:repeat(4,1fr)">
    <div class="ctrl"><label>${t("Mínimo fines de semana completos libres")}</label><input type="number" id="wkendReqFull" min="0" step="1" value="${S.f.wkendReqFull}"></div>
    <div class="ctrl"><label>${t("Mínimo sábados libres")}</label><input type="number" id="wkendReqSat" min="0" step="1" value="${S.f.wkendReqSat}"></div>
    <div class="ctrl"><label>${t("Mínimo domingos libres")}</label><input type="number" id="wkendReqSun" min="0" step="1" value="${S.f.wkendReqSun}"></div>
    <div class="ctrl"><label>${t("Mínimo sábados o domingos libres")}</label><input type="number" id="wkendReqFlex" min="0" step="1" value="${S.f.wkendReqFlex}"></div>
  </div>
  <label class="chk"><input type="checkbox" id="wkendFlexDistinct" ${S.f.wkendFlexDistinct?"checked":""}> ${t("Los días de la regla «sábados o domingos» no pueden pertenecer al mismo fin de semana")}</label>
  <div class="chart-note">${t("Regla activa")}: ≥ ${S.f.wkendReqFull} ${t("fines completos")}, ≥ ${S.f.wkendReqSat} ${t("sábados libres")}, ≥ ${S.f.wkendReqSun} ${t("domingos libres")} y ≥ ${S.f.wkendReqFlex} ${t("sábados o domingos libres")}. ${t("Los días no se reutilizan entre reglas.")}</div></div>`;

  if(S.f.wkendMin>S.f.wkendMax) return h+callout("warning",t("Las horas mínimas no pueden ser superiores a las horas máximas."));
  const filtered=monthly.filter(m=>m.app!=null&&m.app>=S.f.wkendMin&&m.app<=S.f.wkendMax);
  if(!filtered.length) return h+callout("warning",t("No hay empleados que cumplan el rango contractual seleccionado."));

  const keys=new Set(filtered.map(m=>m.id_tienda+"|"+m.personId));
  const wends=detail.filter(d=>keys.has(d.id_tienda+"|"+d.personId));
  const allDates=[...F.dataSet].sort((a,b)=>a-b);
  const worked=new Set(F.shifts.map(s=>s.id_tienda+"|"+s.personId+"|"+s.day_int));

  function weekendStates(store,person,scopeDates){
    const scope=[...scopeDates].sort((a,b)=>a-b), states=new Map();
    const key=d=>store+"|"+person+"|"+d;
    const getState=start=>{ if(!states.has(start))states.set(start,{ini:start,sat:false,sun:false,full:false}); return states.get(start); };
    scope.forEach(day=>{ const wd=D.weekdayISO(day); if(wd!==5&&wd!==6)return; const start=wd===5?day:day-1; const st=getState(start); const free=!worked.has(key(day)); if(wd===5)st.sat=free; else st.sun=free; });
    scope.filter(day=>D.weekdayISO(day)===5).forEach(sat=>{ const sun=sat+1; if(!F.dataSet.has(sun))return; const st=getState(sat); st.full=!worked.has(key(sat))&&!worked.has(key(sun)); });
    return [...states.values()].sort((a,b)=>a.ini-b.ini);
  }

  function weekendOptions(st,distinct){
    const out=[[0,0,0,0]], sat=st.sat?[[0,0],[1,0],[0,1]]:[[0,0]], sun=st.sun?[[0,0],[1,0],[0,1]]:[[0,0]];
    sat.forEach(sa=>sun.forEach(su=>{ const flex=sa[1]+su[1]; if(distinct&&flex>1)return; out.push([0,sa[0],su[0],flex]); }));
    if(st.full)out.push([1,0,0,0]);
    return out;
  }

  function evaluate(states){
    const target=[S.f.wkendReqFull,S.f.wkendReqSat,S.f.wkendReqSun,S.f.wkendReqFlex].map(v=>Math.max(0,Math.floor(Number(v)||0)));
    const full=states.filter(s=>s.full).length, sat=states.filter(s=>s.sat).length, sun=states.filter(s=>s.sun).length;
    const flex=S.f.wkendFlexDistinct?states.filter(s=>s.sat||s.sun).length:sat+sun;
    const failWk=full<target[0], failSat=sat<target[1], failSun=sun<target[2], failFlex=flex<target[3];
    const direct=failWk||failSat||failSun||failFlex;
    let combinable=false;
    if(!direct){
      let dp=new Set(["0,0,0,0"]); const targetKey=target.join(",");
      for(const st of states){
        const next=new Set();
        for(const item of dp){
          const cur=item.split(",").map(Number);
          for(const inc of weekendOptions(st,S.f.wkendFlexDistinct)){
            const value=cur.map((v,i)=>Math.min(target[i],v+inc[i])); next.add(value.join(","));
          }
        }
        dp=next; if(dp.has(targetKey)){combinable=true;break;}
      }
      if(!combinable)combinable=dp.has(targetKey);
    }
    const failComb=!direct&&!combinable;
    return {full,sat,sun,flex,failWk,failSat,failSun,failFlex,failComb,failAny:direct||failComb};
  }

  const ge=groupBy(filtered,m=>m.id_tienda+"|"+m.personId);
  const employees=[...ge.values()].map(rs=>{ const e={id_tienda:rs[0].id_tienda,personId:rs[0].personId,app:Math.max(...rs.map(r=>r.app)),fs:sum(rs.map(r=>r.fs_libres)),sab:sum(rs.map(r=>r.sab_libres)),dom:sum(rs.map(r=>r.dom_libres))}; e.ev=evaluate(weekendStates(e.id_tienda,e.personId,allDates)); return e; });
  employees.sort((a,b)=>(b.app??-Infinity)-(a.app??-Infinity)||String(a.personId).localeCompare(String(b.personId)));

  const nWk=employees.filter(e=>e.ev.failWk), nSat=employees.filter(e=>e.ev.failSat), nSun=employees.filter(e=>e.ev.failSun), nFlex=employees.filter(e=>e.ev.failFlex), nComb=employees.filter(e=>e.ev.failComb), nAny=employees.filter(e=>e.ev.failAny);
  h+=kpiGrid([
    {label:t("Empleados analizados"),value:fmt(employees.length),detail:t("Contrato entre {a} y {b} h",{a:fmt(S.f.wkendMin),b:fmt(S.f.wkendMax)}),tone:"blue"},
    {label:t("Con alguna incidencia"),value:fmt(nAny.length),detail:pctText(pct(nAny.length,employees.length)),tone:nAny.length?"red":"green"},
    {label:t("Incumplen fines completos"),value:fmt(nWk.length),detail:`${t("Mínimo")}: ${S.f.wkendReqFull}`,tone:nWk.length?"red":"green"},
    {label:t("Incumplen sábados"),value:fmt(nSat.length),detail:`${t("Mínimo")}: ${S.f.wkendReqSat}`,tone:nSat.length?"red":"green"},
    {label:t("Incumplen domingos"),value:fmt(nSun.length),detail:`${t("Mínimo")}: ${S.f.wkendReqSun}`,tone:nSun.length?"red":"green"},
    {label:t("Incumplen sábado o domingo"),value:fmt(nFlex.length),detail:`${t("Mínimo")}: ${S.f.wkendReqFlex}`,tone:nFlex.length?"red":"green"},
  ],6);
  if(nComb.length)h+=callout("warning",t("Hay {n} empleado(s) cuyos contadores por separado alcanzan los mínimos, pero no existe una asignación que cumpla todas las reglas sin reutilizar días.",{n:nComb.length}));

  if(wends.length){
    h+=`<div class="block"><h3>${t("Rotación por fin de semana")}</h3>`;
    const gw=groupBy(wends,d=>d.ini); const rot=[...gw.entries()].map(([ini,rs])=>({ini:Number(ini),label:rs[0].fin,comp:rs.filter(r=>r.libre).length,sab:rs.filter(r=>r.sat).length,dom:rs.filter(r=>r.sun).length})).sort((a,b)=>a.ini-b.ini);
    h+=chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:390,dec:0})+`</div>`;

    h+=`<div class="block"><h3>${t("Mapa empleado-fin de semana")}</h3>`+help(t("El mapa mantiene fijas las columnas de empleado y contrato. Una fila es alerta si incumple cualquiera de los mínimos activos o la combinación sin reutilización."));
    const order=[...groupBy(wends,d=>d.ini).entries()].sort((a,b)=>Number(a[0])-Number(b[0])).map(([,rs])=>rs[0].fin);
    const pv=new Map(); wends.forEach(d=>pv.set((d.id_tienda+"|"+d.personId)+"|"+d.fin,(d.sat?1:0)+(d.sun?1:0)));
    const mapRows=employees.map(e=>{ const key=e.id_tienda+"|"+e.personId; const values=order.map(w=>pv.has(key+"|"+w)?pv.get(key+"|"+w):null); const full=values.filter(v=>v===2).length; const freeDays=sum(values.filter(v=>v!=null)); return {...e,key,values,full,freeDays,alert:e.ev.failAny}; }).sort((a,b)=>Number(b.alert)-Number(a.alert)||a.full-b.full||a.freeDays-b.freeDays||String(a.personId).localeCompare(String(b.personId)));
    h+=`<div class="wkmap-controls"><input type="search" id="wkendMapSearch" placeholder="${t("Buscar empleado en el mapa")}" value="${esc(S.f.wkendMapQuery||"")}"><label class="chk"><input type="checkbox" id="wkendMapAlerts" ${S.f.wkendMapAlerts?"checked":""}> ${t("Mostrar solo alertas")}</label></div>`;
    h+=`<div class="wkmap-wrap"><table class="wkmap" id="weekendMapTable"><thead><tr><th class="wk-employee">${t("Empleado")}</th><th class="wk-contract">${t("Horas contrato")}</th>`+order.map(w=>`<th>${esc(w)}</th>`).join("")+`<th>${t("Resumen del periodo")}</th></tr></thead><tbody>`;
    mapRows.forEach(row=>{ h+=`<tr data-search="${esc((row.id_tienda+" "+row.personId).toLowerCase())}" data-alert="${row.alert?"1":"0"}"><td class="wk-employee">${esc(row.id_tienda+" · "+row.personId)}${row.alert?`<span class="wk-alert">${t("Alerta")}</span>`:""}</td><td class="wk-contract">${row.app==null?"—":fmt(row.app,1)+" h"}</td>`; row.values.forEach(v=>{ h+=`<td>${v==null?"":`<span class="wk-cell wk-${v}">${v}</span>`}</td>`; }); h+=`<td>${t("Fines completos: {n} de {total}",{n:row.full,total:order.length})}</td></tr>`; });
    h+=`</tbody></table></div>`+legend([{label:t("0 días"),color:"#d8e1ec"},{label:t("1 día"),color:"#8dbcf6"},{label:t("2 días"),color:"#244ed8"}])+`</div>`;
  }

  function weekendIncidentText(ev){
    const alerts=[];
    if(ev.failWk)alerts.push(t("Fines completos < ")+S.f.wkendReqFull);
    if(ev.failSat)alerts.push(t("Sábados < ")+S.f.wkendReqSat);
    if(ev.failSun)alerts.push(t("Domingos < ")+S.f.wkendReqSun);
    if(ev.failFlex)alerts.push(t("Sábados o domingos < ")+S.f.wkendReqFlex);
    if(ev.failComb)alerts.push(t("No combinable sin reutilizar días"));
    return alerts.join(", ")||t("Sin alertas");
  }

  h+=`<div class="block"><h3>${t("Incidencias según las reglas introducidas")}</h3>`+help(t("Las incidencias directas indican que no hay suficientes descansos del tipo requerido. Combinación indica que los contadores aislados alcanzan los mínimos, pero los días disponibles no pueden repartirse entre todas las reglas sin reutilización."));
  const diagSets=[[t("Todas"),nAny],[t("Fines completos"),nWk],[t("Sábados"),nSat],[t("Domingos"),nSun],[t("Sáb. o dom."),nFlex],[t("Combinación"),nComb]];
  if(S.f.wkendDiag>=diagSets.length)S.f.wkendDiag=0;
  h+=`<div class="chips" id="wkendDiag">`+diagSets.map((d,i)=>`<span class="chip ${S.f.wkendDiag===i?"on":""}" data-i="${i}">${d[0]} (${d[1].length})</span>`).join("")+`</div>`;
  const cur=diagSets[S.f.wkendDiag][1];
  if(!cur.length) h+=callout("info",t("No hay empleados en esta categoría."));
  else{ const rows=[...cur].sort((a,b)=>a.fs-b.fs||a.sab-b.sab||a.dom-b.dom).map(e=>({Tienda:e.id_tienda,Empleado:e.personId,"Horas contrato":e.app,"Fines completos libres":e.fs,"Sábados libres":e.sab,"Domingos libres":e.dom,"Días S/D disponibles":e.ev.flex,"Incumplimientos":weekendIncidentText(e.ev)})); h+=table([tc("Tienda"),tc("Empleado"),tc("Horas contrato"),tc("Fines completos libres"),tc("Sábados libres"),tc("Domingos libres"),tc("Días S/D disponibles"),tc("Incumplimientos")],rows,{height:400,numCols:["Horas contrato","Fines completos libres","Sábados libres","Domingos libres","Días S/D disponibles"]}); }
  h+=`</div>`;

  h+=`<div class="block"><h3>${t("Resumen empleado-mes")}</h3><label class="chk"><input type="checkbox" id="wkendAlerts" ${S.f.wkendAlerts?"checked":""}> ${t("Mostrar solo empleado-mes con alguna incidencia")}</label>`;
  const monthRows=filtered.map(m=>{ const [Y,M]=m.Mes.split("-").map(Number); const scope=allDates.filter(d=>{const x=D.dayYMD(d);return x.y===Y&&x.m===M;}); const ev=evaluate(weekendStates(m.id_tienda,m.personId,scope)); return {m,ev}; });
  let view=monthRows; if(S.f.wkendAlerts)view=view.filter(x=>x.ev.failAny);
  const rows=view.map(({m,ev})=>({Mes:m.Mes,id_tienda:m.id_tienda,personId:m.personId,"Horas contrato":m.app,"Fines libres":m.fs_libres,"Fines eval.":m.fs_eval,"Sábados libres":m.sab_libres,"Sábados eval.":m.sab_eval,"Domingos libres":m.dom_libres,"Domingos eval.":m.dom_eval,"Días S/D disponibles":ev.flex,"Alerta":weekendIncidentText(ev)})).sort((a,b)=>a.Alerta.localeCompare(b.Alerta)||a.Mes.localeCompare(b.Mes)||String(a.personId).localeCompare(String(b.personId)));
  h+=table([tc("Mes"),tc("id_tienda"),tc("personId"),tc("Horas contrato"),tc("Fines libres"),tc("Fines eval."),tc("Sábados libres"),tc("Sábados eval."),tc("Domingos libres"),tc("Domingos eval."),tc("Días S/D disponibles"),tc("Alerta")],rows,{height:480,numCols:["Horas contrato","Fines libres","Fines eval.","Sábados libres","Sábados eval.","Domingos libres","Domingos eval.","Días S/D disponibles"]})+`</div>`;
  return h;
}'''


def patch_weekend_assignment(source: str) -> str:
    """Replica en el HTML autónomo la asignación exacta de descansos de Streamlit."""
    source = _replace(
        source,
        'wkendReqFull:1, wkendReqSat:1, wkendReqSun:1, wkendAlerts:true',
        'wkendReqFull:1, wkendReqSat:1, wkendReqSun:1, wkendReqFlex:0, wkendFlexDistinct:false, wkendAlerts:true',
        expected=2,
        label="estado de reglas",
    )
    source = _replace(
        source,
        'on("wkendReqSun","change",e=>{S.f.wkendReqSun=Math.max(0,Math.floor(Number(e.target.value)||0));renderTab();});',
        'on("wkendReqSun","change",e=>{S.f.wkendReqSun=Math.max(0,Math.floor(Number(e.target.value)||0));renderTab();});\n'
        '  on("wkendReqFlex","change",e=>{S.f.wkendReqFlex=Math.max(0,Math.floor(Number(e.target.value)||0));renderTab();});\n'
        '  on("wkendFlexDistinct","change",e=>{S.f.wkendFlexDistinct=e.target.checked;renderTab();});',
        expected=1,
        label="bindings de reglas",
    )
    translations = (
        '  "Mínimo sábados o domingos libres":"Minimum Saturdays or Sundays off",\n'
        '  "sábados o domingos libres":"Saturdays or Sundays off",\n'
        '  "Los días de la regla «sábados o domingos» no pueden pertenecer al mismo fin de semana":"Days used by the Saturdays-or-Sundays rule cannot belong to the same weekend",\n'
        '  "Los días no se reutilizan entre reglas.":"Days are not reused across rules.",\n'
        '  "Incumplen sábado o domingo":"Fail Saturday-or-Sunday rule",\n'
        '  "Sáb. o dom.":"Sat. or Sun.","Combinación":"Combination",\n'
        '  "Días S/D disponibles":"Available Sat/Sun days","Incumplimientos":"Breaches",\n'
        '  "No combinable sin reutilizar días":"Cannot be combined without reusing days",\n'
        '  "Mostrar solo empleado-mes con alguna incidencia":"Show only employee-months with an incident",\n'
        '  "Sábados o domingos < ":"Saturdays or Sundays < ",\n'
        '  "Hay {n} empleado(s) cuyos contadores por separado alcanzan los mínimos, pero no existe una asignación que cumpla todas las reglas sin reutilizar días.":"{n} employee(s) meet the individual counters, but there is no allocation that satisfies every rule without reusing days.",\n'
        '  "Las reglas se evalúan sobre días concretos de descanso. Un mismo sábado o domingo no puede utilizarse para cumplir dos reglas distintas. Si existe alguna asignación válida de los descansos, el empleado se considera conforme.":"Rules are evaluated on specific days off. The same Saturday or Sunday cannot satisfy two different rules. If any valid allocation exists, the employee is compliant.",\n'
        '  "Introduce el mínimo exigido. Un valor 0 desactiva la regla. Sábados o domingos admite cualquier combinación de ambos días; por defecto un fin de semana completo aporta 2 días a esa regla.":"Enter the required minimum. Zero disables the rule. Saturdays or Sundays accepts any mix of both days; by default a full weekend contributes two days to that rule.",\n'
        '  "El mapa mantiene fijas las columnas de empleado y contrato. Una fila es alerta si incumple cualquiera de los mínimos activos o la combinación sin reutilización.":"The map keeps employee and contract columns fixed. A row is an alert if it fails any active minimum or the non-reuse combination.",\n'
        '  "Las incidencias directas indican que no hay suficientes descansos del tipo requerido. Combinación indica que los contadores aislados alcanzan los mínimos, pero los días disponibles no pueden repartirse entre todas las reglas sin reutilización.":"Direct incidents mean there are not enough days off of the required type. Combination means the individual counters reach their minima, but the available days cannot be allocated across all rules without reuse.",\n'
    )
    anchor = '  // ---- Metodología ----\n'
    source = _replace(source, anchor, translations + '\n' + anchor, expected=1, label="traducciones")

    pattern = re.compile(
        r'function renderWeekends\(F\)\{.*?\n\}\n\n\n/\* ---------- Metodología ---------- \*/',
        re.S,
    )
    matches = pattern.findall(source)
    if len(matches) != 1:
        raise ValueError(
            f"Parche HTML de fines de semana: se esperaba un renderWeekends y se encontraron {len(matches)}"
        )
    return pattern.sub(
        WEEKEND_RENDER + '\n\n\n/* ---------- Metodología ---------- */', source, count=1
    )
