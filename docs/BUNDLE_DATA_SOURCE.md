# Integración de la fuente `bundle`

## 1. Objetivo y alcance

Esta integración incorpora el fichero consolidado `bundle` como nueva fuente de información sin cambiar la lógica funcional del validador.

La primera fase entregó **paridad en Streamlit**. La segunda fase incorpora también el **HTML autónomo/distribuible**, manteniendo la misma semántica y sin modificar reglas ni fórmulas.

El principio rector sigue siendo el documentado en `NEW_DATA_SOURCE_GUIDE.md`:

```text
BUNDLE -> adaptador de fuente -> semántica canónica -> MOTOR EXISTENTE -> Streamlit / HTML
```

No se utilizan los agregados adicionales del bundle para sustituir cálculos existentes.

## 2. Formato detectado

Un documento se considera `bundle` cuando contiene como mínimo:

```text
config
people
  └── data[]
times
  └── storeDayTimes[]
```

La tienda se identifica mediante `config.store.id`.

La carga consolidada se admite como **un único fichero**. No puede mezclarse en una misma ejecución con uno o dos JSON mensuales del formato anterior.

## 3. Mapeo al modelo canónico

| Concepto canónico | Ruta bundle | Transformación |
|---|---|---|
| `store_id` | `config.store.id` | Identidad directa |
| `person_id` | `times.storeDayTimes[].people[].personId` | Identidad directa |
| `data_dates` | `times.storeDayTimes[].operatingDate` | Fecha ISO; incluye días sin turnos |
| presencia empleado-día | existencia en `times.storeDayTimes[].people[]` | Independiente de tener turno |
| contrato aplicable | `people.data[].employmentPeriods[]` | Periodo cuya fecha incluye `operatingDate` |
| contrato empleado-mes | contrato resuelto por persona-día | Se conserva el último valor procesado del mes, igual que la extracción actual |
| plan publicado | `dayTimes.planned[]` | Sin fallback |
| borrador | `dayTimes.plannedDraft[]` | Sin fallback |
| edición manual draft | `dayTimes.plannedDraftManuallyEdited` | Semántica trivalente `True`/`False`/ausente en Python; el HTML mantiene la selección de fuente vigente y no introduce una tercera fuente |
| segmento de trabajo | `hourType == WORK` | Los demás tipos se ignoran |
| inicio/fin segmento | `startDateTime` / `endDateTime` | Mismo tratamiento wall-clock; no conversión UTC funcional |
| turno | segmentos WORK del persona-día | Mismo algoritmo de agregación actual |
| ausencia | `dayTimes.absences[]` | Solo `VALIDATED`/`APPROVED`, misma deduplicación y fallback de tipo |

## 4. Contratos

La fuente antigua entregaba `person.applicableWorkingHours` dentro de cada persona-día. El bundle separa esa información en `people.data[].employmentPeriods[]`.

Los adaptadores resuelven el contrato aplicable utilizando:

```text
validFromDate <= operatingDate <= validToDate
```

Los límites ausentes se interpretan como abiertos. Si no existe periodo aplicable, el contrato canónico queda en `None`/`null`, reproduciendo la posibilidad de contrato no evaluable del motor actual.

Si aparecen varios periodos simultáneamente aplicables para una persona-fecha, el adaptador falla explícitamente en lugar de elegir uno de forma silenciosa.

## 5. Construcción de turnos

No se usan `times.hours`, `dayTimes.hours` ni ningún agregado de horas del bundle como fuente del motor.

Se conserva exactamente el algoritmo existente:

```text
shift_start = primer inicio WORK ordenado
shift_end = máximo fin WORK
worked_hours = suma de duraciones de segmentos WORK
break_hours = suma de gaps positivos <= max_internal_break_hours
```

También se conserva `end > start` y el redondeo a cuatro decimales.

## 6. Fuentes de horario

Las capacidades siguen siendo únicamente:

- `planned`;
- `plannedDraft`.

`plannedDraftManuallyEdited` sigue siendo un filtro y no una tercera fuente.

No se introduce un “plan efectivo” que mezcle automáticamente publicado y borrador. El bundle contiene agregados que podrían sugerir esa semántica, pero utilizarlos cambiaría el comportamiento documentado del motor.

## 7. Campos del bundle deliberadamente no utilizados

Quedan fuera del motor de paridad:

- `violations`;
- `coverage`;
- `requests`;
- `absenceTypes`;
- `statusTypes`;
- `taskTypes`;
- agregados `times.hours`;
- agregados `dayTimes.hours`;
- headcounts y métricas precalculadas.

Estos datos podrán evaluarse en fases posteriores, una vez demostrada la equivalencia funcional.

## 8. Compatibilidad y rutas de ejecución Python/Streamlit

Durante la migración permanecen dos rutas:

```text
Ruta de referencia
JSON actual -> pipeline actual -> ValidationResult

Ruta canónica de prueba
JSON actual -> CurrentJsonAdapter -> CanonicalDataset -> motor canónico

Ruta bundle
bundle -> BundleAdapter -> CanonicalDataset -> motor canónico
```

`run_validation()` del motor antiguo se mantiene para no romper la referencia. `run_canonical_validation()` consume el contrato normalizado sin conocer la fuente externa.

La fachada productiva `schedule_adapter.py` decide automáticamente si la entrada es bundle o formato anterior, de modo que la composición Streamlit no necesita conocer detalles de la nueva fuente.

## 9. Ruta HTML distribuible

El HTML autónomo mantiene su motor JavaScript existente. Para no reescribir reglas ni fórmulas, la nueva fuente se adapta en la frontera de entrada mediante `scripts/bundle_html_patch.py`:

```text
bundle
  -> detección de formato
  -> resolución people.data / employmentPeriods
  -> extracción equivalente de turnos, ausencias, presencia y data_dates
  -> motor JavaScript existente
  -> datasets y presentación HTML existentes
```

El parche reproduce las mismas invariantes del `BundleAdapter` Python y no usa agregados precalculados del bundle.

La política de carga HTML es la misma que en Streamlit:

- un bundle consolidado se carga como un único fichero;
- puede abarcar varios meses;
- no se aplica la restricción de “un mes por fichero” del formato legado;
- no puede mezclarse con JSON del formato anterior en una misma ejecución;
- la entrada legado de uno o dos meses consecutivos se conserva para regresión.

`validador_distribuible.html` sigue siendo **artefacto generado**. No se edita manualmente. La cadena oficial es:

```text
reference_payload_*.js
  -> scripts/build_distributable_html.py
       -> patch_bundle_source
       -> parches productivos existentes
  -> validador_distribuible.html
```

El workflow `.github/workflows/build-distributable-html.yml` incluye `scripts/bundle_html_patch.py` entre sus dependencias y regenera el artefacto al cambiar el adaptador.

## 10. Golden Master mínimo

La suite de regresión de esta integración verifica en Python:

- igualdad canónica entre un JSON actual y un bundle semánticamente equivalente;
- igualdad de turnos, ausencias, contratos, presencia, cobertura, incidencias, resumen mensual y control semanal entre la ruta antigua y `CurrentJsonAdapter`;
- detección de `planned` y `plannedDraft` en bundle;
- carga del bundle como documento consolidado único;
- rechazo de mezcla bundle + JSON legado.

Para HTML, `tests/test_bundle_html_patch.py` verifica:

- que el parche aplica sobre el payload de referencia real;
- que toda la cadena de parches del generador compone correctamente;
- que se mantienen las capacidades de entrada legado;
- que el HTML final contiene la frontera bundle junto con los parches productivos preexistentes.

La equivalencia numérica exhaustiva Python ↔ JavaScript sigue siendo un nivel Golden Master separado, tal como exige `HTML_PARITY.md`; no se sustituye por una mera comprobación de textos o screenshots.

## 11. Validación con el bundle de referencia 3394

Para el bundle de referencia con cobertura `2026-08-19` a `2026-10-15`, la normalización produce:

| Métrica | `planned` | `plannedDraft` |
|---|---:|---:|
| Turnos persona-día | 2.096 | 1.520 |
| Horas netas por segmentos WORK | 14.629,0 | 10.650,0 |
| Descansos internos | 1.357,0 h | 1.166,0 h |
| Ausencias aceptadas | 627 | 627 |
| Fechas de cobertura | 58 | 58 |
| Empleados con presencia | 188 | 188 |

La proyección JavaScript del bundle se ha contrastado sobre el mismo fichero y reproduce los conteos de segmentos WORK, horas netas, ausencias, fechas y persona-días esperados antes de entrar al motor HTML.

Estos valores proceden de la normalización que alimenta los motores, no de los agregados precalculados del bundle.

## 12. Fuera de alcance de esta fase

- aprovechar `coverage`/`violations` del bundle;
- corregir la resolución histórica de contrato del control semanal;
- introducir fallback entre `planned` y `plannedDraft`;
- cambiar timezone, reglas, operadores, fines de semana o cálculos visuales;
- rediseñar la composición del HTML por aprovechar el cambio de fuente.

Cualquier diferencia funcional detectada durante las pruebas debe tratarse primero como una incidencia de paridad de fuente, no como una oportunidad de cambiar reglas.
