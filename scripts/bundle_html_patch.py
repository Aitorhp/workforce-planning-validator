from __future__ import annotations


def _replace_one(source: str, old: str, new: str, label: str) -> str:
    found = source.count(old)
    if found != 1:
        raise ValueError(
            f"Parche HTML bundle '{label}': se esperaba 1 coincidencia y se encontraron {found}"
        )
    return source.replace(old, new, 1)


BUNDLE_CORE = r'''
  function isBundleData(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) return false;
    return Boolean(
      data.config && typeof data.config === "object" && !Array.isArray(data.config) &&
      data.people && typeof data.people === "object" && !Array.isArray(data.people) &&
      data.times && typeof data.times === "object" && !Array.isArray(data.times) &&
      Array.isArray(data.times.storeDayTimes)
    );
  }
'''


BUNDLE_EXTRACTION = r'''
  // ---- Adaptador bundle ----------------------------------------------------
  function bundlePeopleIndex(data) {
    const section = data.people || {};
    const people = section.data || [];
    if (!Array.isArray(people)) throw new Error("El bundle debe contener people.data como lista.");
    const index = new Map();
    for (const person of people) {
      if (!person || typeof person !== "object") continue;
      const personId = person.personId;
      if (personId !== null && personId !== undefined && personId !== "") index.set(personId, person);
    }
    return index;
  }

  function bundleApplicableHours(peopleIndex, personId, operatingDay) {
    const person = peopleIndex.get(personId);
    if (!person) throw new Error(`personId=${personId} aparece en times pero no en people.data.`);
    const periods = Array.isArray(person.employmentPeriods) ? person.employmentPeriods : [];
    const matching = [];
    for (const period of periods) {
      if (!period || typeof period !== "object") continue;
      const from = period.validFromDate ? parseDay(period.validFromDate) : -Infinity;
      const to = period.validToDate ? parseDay(period.validToDate) : Infinity;
      if (from <= operatingDay && operatingDay <= to) matching.push(period);
    }
    if (matching.length > 1) {
      throw new Error(`personId=${personId} tiene varios employmentPeriods aplicables en ${dayISO(operatingDay)}.`);
    }
    return matching.length ? matching[0].applicableWorkingHours : null;
  }

  function extractBundleData(data, scheduleSource) {
    const config = data.config || {};
    const storeId = (config.store || {}).id;
    if (storeId === null || storeId === undefined || storeId === "") {
      throw new Error("El bundle no contiene config.store.id.");
    }
    const storeDayTimes = (data.times || {}).storeDayTimes || [];
    if (!Array.isArray(storeDayTimes)) throw new Error("El bundle debe contener times.storeDayTimes como lista.");
    const peopleIndex = bundlePeopleIndex(data);
    const shifts = [];
    const employeeMonths = new Map();
    const employeeMonthsMeta = new Map();
    const absences = [];
    const presence = new Map();
    const presenceMeta = new Map();
    const maxBreakH = CONFIG.calculation.max_internal_break_hours;

    for (const storeDay of storeDayTimes) {
      if (!storeDay || typeof storeDay !== "object" || !storeDay.operatingDate) continue;
      const operatingDay = parseDay(storeDay.operatingDate);
      for (const personDay of storeDay.people || []) {
        if (!personDay || typeof personDay !== "object") continue;
        const personId = personDay.personId;
        const applicable = bundleApplicableHours(peopleIndex, personId, operatingDay);
        const empKey = storeId + SEP + personId;
        if (!presence.has(empKey)) {
          presence.set(empKey, new Set());
          presenceMeta.set(empKey, { store: storeId, person: personId });
        }
        presence.get(empKey).add(operatingDay);
        const mKey = empKey + SEP + monthKey(operatingDay);
        employeeMonths.set(mKey, applicable);
        employeeMonthsMeta.set(mKey, { store: storeId, person: personId, month: monthKey(operatingDay) });

        const dayTimes = personDay.dayTimes && typeof personDay.dayTimes === "object" ? personDay.dayTimes : {};
        const seen = new Set();
        const rawAbsences = Array.isArray(dayTimes.absences) ? dayTimes.absences : [];
        for (const absence of rawAbsences) {
          if (!absence || typeof absence !== "object") continue;
          const status = String(absence.status || "").toUpperCase();
          if (status !== "VALIDATED" && status !== "APPROVED") continue;
          const typeData = absence.type || {};
          const absenceType = String(typeData.name || typeData.description || absence.id || "AUSENCIA");
          const key = absenceType + SEP + status;
          if (seen.has(key)) continue;
          seen.add(key);
          absences.push({ store: storeId, person: personId, day: operatingDay, type: absenceType, status });
        }

        let selected = dayTimes[scheduleSource];
        if (!Array.isArray(selected)) selected = [];
        const segs = [];
        for (const segment of selected) {
          if (!isWork(segment)) continue;
          const startValue = segment.startDateTime, endValue = segment.endDateTime;
          if (!startValue || !endValue) continue;
          const start = parseDateTime(startValue), end = parseDateTime(endValue);
          if (end <= start) throw new Error(`Segmento invalido en ${scheduleSource}: personId=${personId}`);
          segs.push([start, end]);
        }
        if (!segs.length) continue;
        segs.sort((a, b) => a[0] - b[0]);
        const shiftStart = segs[0][0];
        const shiftEnd = Math.max(...segs.map(s => s[1]));
        const netMs = segs.reduce((acc, s) => acc + (s[1] - s[0]), 0);
        let breakMs = 0, previousEnd = segs[0][1];
        for (let i = 1; i < segs.length; i++) {
          const [currentStart, currentEnd] = segs[i];
          const gap = currentStart - previousEnd;
          if (gap > 0 && gap <= maxBreakH * 3600000) breakMs += gap;
          if (currentEnd > previousEnd) previousEnd = currentEnd;
        }
        shifts.push({
          store: storeId, person: personId, applicable, workDay: operatingDay,
          shiftStart, shiftEnd,
          workedHours: pyround(netMs / 3600000, 4),
          breakHours: pyround(breakMs / 3600000, 4),
        });
      }
    }
    const scmp = (a, b) => (String(a.store) < String(b.store) ? -1 : String(a.store) > String(b.store) ? 1 :
      String(a.person) < String(b.person) ? -1 : String(a.person) > String(b.person) ? 1 : 0);
    shifts.sort((a, b) => scmp(a, b) || a.workDay - b.workDay);
    absences.sort((a, b) => scmp(a, b) || a.day - b.day);
    return { shifts, employeeMonths, employeeMonthsMeta, absences, presence, presenceMeta, storeId };
  }
'''


BUNDLE_UI = r'''
function bundleDocumentInfo(data, filename){
  const storeId=((data.config||{}).store||{}).id;
  if(storeId===null||storeId===undefined||storeId==="") throw new Error(`${filename}: ${t("El bundle no contiene config.store.id.")}`);
  if(!data.people||!Array.isArray(data.people.data)) throw new Error(`${filename}: ${t("El bundle debe contener people.data como lista.")}`);
  const storeDayTimes=(data.times||{}).storeDayTimes;
  if(!Array.isArray(storeDayTimes)) throw new Error(`${filename}: ${t("El bundle debe contener times.storeDayTimes como lista.")}`);
  const dates=[]; const seen=new Set();
  for(const item of storeDayTimes){
    if(!item||typeof item!=="object"||!item.operatingDate) continue;
    const day=D.parseDay(item.operatingDate);
    if(seen.has(day)) throw new Error(`${filename}: ${t("El bundle contiene fechas operativas duplicadas.")}`);
    seen.add(day); dates.push(day);
  }
  dates.sort((a,b)=>a-b);
  if(!dates.length) throw new Error(`${filename}: ${t("No se han encontrado fechas operativas en el bundle.")}`);
  return {data,filename,storeId,dates,dateSet:new Set(dates),month:null,first:dates[0],last:dates[dates.length-1],kind:"bundle"};
}

function combinePlanningInputs(entries){
  const bundles=entries.filter(entry=>D.isBundleData(entry.data));
  if(bundles.length){
    if(entries.length!==1||bundles.length!==1) throw new Error(t("El bundle consolidado debe cargarse como un único fichero y no puede mezclarse con planificaciones del formato anterior."));
    const info=bundleDocumentInfo(bundles[0].data,bundles[0].filename);
    return {data:info.data,infos:[info],periodStart:info.first,periodEnd:info.last,inputKind:"bundle"};
  }
  const combined=combinePlanningDocuments(entries);
  return {...combined,inputKind:"legacy"};
}
'''


def patch_bundle_source(source: str) -> str:
    """Añade soporte bundle al HTML sin cambiar reglas ni cálculos posteriores."""
    source = _replace_one(
        source,
        "  // ---- Detección de orígenes ----------------------------------------------\n",
        BUNDLE_CORE + "\n  // ---- Detección de orígenes ----------------------------------------------\n",
        "detector de bundle",
    )

    source = _replace_one(
        source,
        "    for (const storeDay of data.storeDayTimes || []) {\n",
        "    const sourceData = isBundleData(data) ? { storeDayTimes: (data.times || {}).storeDayTimes || [] } : data;\n"
        "    for (const storeDay of sourceData.storeDayTimes || []) {\n",
        "detección de fuentes en bundle",
    )

    source = _replace_one(
        source,
        "  // ---- Fechas de datos -----------------------------------------------------\n",
        BUNDLE_EXTRACTION + "\n  // ---- Fechas de datos -----------------------------------------------------\n",
        "adaptador de extracción bundle",
    )

    source = _replace_one(
        source,
        "  // ---- Rachas consecutivas -------------------------------------------------\n",
        "  function collectInputDataDates(data) {\n"
        "    if (!isBundleData(data)) return collectDataDates(data);\n"
        "    return collectDataDates({ storeDayTimes: (data.times || {}).storeDayTimes || [] });\n"
        "  }\n\n"
        "  // ---- Rachas consecutivas -------------------------------------------------\n",
        "cobertura temporal bundle",
    )

    source = _replace_one(
        source,
        "    const ex = extractData(data, scheduleSource);\n",
        "    const ex = isBundleData(data) ? extractBundleData(data, scheduleSource) : extractData(data, scheduleSource);\n",
        "orquestación extracción",
    )
    source = _replace_one(
        source,
        "    const dataDates = collectDataDates(data);\n",
        "    const dataDates = collectInputDataDates(data);\n",
        "orquestación fechas",
    )
    source = _replace_one(
        source,
        "    CONFIG, SCHEDULE_SOURCES, detectScheduleSources, runValidation,\n",
        "    CONFIG, SCHEDULE_SOURCES, isBundleData, detectScheduleSources, runValidation,\n",
        "API pública JS",
    )

    source = _replace_one(
        source,
        "function planningDocumentInfo(data, filename){\n",
        BUNDLE_UI + "\nfunction planningDocumentInfo(data, filename){\n",
        "frontera de carga bundle",
    )
    source = _replace_one(
        source,
        "    const combined=combinePlanningDocuments(entries);\n",
        "    const combined=combinePlanningInputs(entries);\n",
        "carga unificada",
    )
    source = _replace_one(
        source,
        "    S.raw=combined.data; S.rawFiles=entries.map(e=>e.data); S.fileInfo=combined.infos;\n",
        "    S.raw=combined.data; S.rawFiles=entries.map(e=>e.data); S.fileInfo=combined.infos; S.inputKind=combined.inputKind||\"legacy\";\n",
        "estado de tipo de entrada",
    )

    source = _replace_one(
        source,
        '  const fileMessage=S.filenames.length>1?t("Se han combinado {n} ficheros de la misma tienda para analizar el periodo completo.",{n:S.filenames.length}):t("Un fichero de la tienda se analiza como periodo independiente.");',
        '  const fileMessage=S.inputKind==="bundle"?t("El bundle consolidado se analiza como un único periodo y se normaliza antes de aplicar el motor."):S.filenames.length>1?t("Se han combinado {n} ficheros de la misma tienda para analizar el periodo completo.",{n:S.filenames.length}):t("Un fichero de la tienda se analiza como periodo independiente.");',
        "mensaje de cabecera bundle",
    )

    source = _replace_one(
        source,
        '    <li>${S.filenames.length>1?t("Se han combinado {n} ficheros de la misma tienda para analizar el periodo completo.",{n:S.filenames.length}):t("Un fichero de la tienda se analiza como periodo independiente.")}</li>',
        '    <li>${S.inputKind==="bundle"?t("El bundle consolidado se normaliza con la misma semántica de contratos, turnos, ausencias y cobertura antes de aplicar las reglas."):S.filenames.length>1?t("Se han combinado {n} ficheros de la misma tienda para analizar el periodo completo.",{n:S.filenames.length}):t("Un fichero de la tienda se analiza como periodo independiente.")}</li>',
        "metodología bundle",
    )

    translations = (
        '  "El bundle consolidado debe cargarse como un único fichero y no puede mezclarse con planificaciones del formato anterior.":"The consolidated bundle must be loaded as a single file and cannot be mixed with legacy schedule files.",\n'
        '  "El bundle no contiene config.store.id.":"The bundle does not contain config.store.id.",\n'
        '  "El bundle debe contener people.data como lista.":"The bundle must contain people.data as a list.",\n'
        '  "El bundle debe contener times.storeDayTimes como lista.":"The bundle must contain times.storeDayTimes as a list.",\n'
        '  "El bundle contiene fechas operativas duplicadas.":"The bundle contains duplicate operating dates.",\n'
        '  "No se han encontrado fechas operativas en el bundle.":"No operating dates were found in the bundle.",\n'
        '  "El bundle consolidado se analiza como un único periodo y se normaliza antes de aplicar el motor.":"The consolidated bundle is analysed as a single period and normalized before the engine is applied.",\n'
        '  "El bundle consolidado se normaliza con la misma semántica de contratos, turnos, ausencias y cobertura antes de aplicar las reglas.":"The consolidated bundle is normalized with the same contract, shift, absence and coverage semantics before applying the rules.",\n'
    )
    source = _replace_one(
        source,
        "  // ---- Errors / loading ----\n",
        translations + "  // ---- Errors / loading ----\n",
        "traducciones bundle",
    )
    return source
