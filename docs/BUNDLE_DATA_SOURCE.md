# Integración de la fuente `bundle`

## 1. Objetivo y alcance

Esta integración incorpora el fichero consolidado `bundle` como nueva fuente de información sin cambiar la lógica funcional del validador.

La primera fase entrega **paridad en Streamlit**. El HTML distribuible queda fuera de esta fase de validación inicial, de acuerdo con la decisión de producto de probar una sola superficie antes de duplicar la adaptación en JavaScript.

El principio rector sigue siendo el documentado en `NEW_DATA_SOURCE_GUIDE.md`:

```text
BUNDLE -> BundleAdapter -> CanonicalDataset -> MOTOR EXISTENTE -> Streamlit
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
| edición manual draft | `dayTimes.plannedDraftManuallyEdited` | Semántica trivalente `True`/`False`/ausente |
| segmento de trabajo | `hourType == WORK` | Los demás tipos se ignoran |
| inicio/fin segmento | `startDateTime` / `endDateTime` | Mismo parser actual; se descarta `tzinfo` sin conversión UTC |
| turno | segmentos WORK del persona-día | Mismo algoritmo de agregación actual |
| ausencia | `dayTimes.absences[]` | Solo `VALIDATED`/`APPROVED`, misma deduplicación y fallback de tipo |

## 4. Contratos

La fuente antigua entregaba `person.applicableWorkingHours` dentro de cada persona-día. El bundle separa esa información en `people.data[].employmentPeriods[]`.

`BundleAdapter` resuelve el contrato aplicable utilizando:

```text
validFromDate <= operatingDate <= validToDate
```

Los límites ausentes se interpretan como abiertos. Si no existe periodo aplicable, el contrato canónico queda en `None`, reproduciendo la posibilidad de contrato no evaluable del motor actual.

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

## 7. Campos del bundle deliberadamente no utilizados en fase 1

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

## 8. Compatibilidad y rutas de ejecución

Durante la migración permanecen dos rutas:

```text
Ruta de referencia
JSON actual -> pipeline actual -> ValidationResult

Ruta canónica de prueba
JSON actual -> CurrentJsonAdapter -> CanonicalDataset -> motor canónico

Ruta bundle
bundle -> BundleAdapter -> CanonicalDataset -> motor canónico
```

`run_validation()` del motor antiguo se mantiene para no romper la referencia. La nueva función `run_canonical_validation()` consume el contrato normalizado sin conocer la fuente externa.

La fachada productiva `schedule_adapter.py` decide automáticamente si la entrada es bundle o formato anterior, de modo que la composición Streamlit no necesita conocer detalles de la nueva fuente.

## 9. Golden Master mínimo

La suite de regresión de esta integración verifica:

- igualdad canónica entre un JSON actual y un bundle semánticamente equivalente;
- igualdad de turnos, ausencias, contratos, presencia, cobertura, incidencias, resumen mensual y control semanal entre la ruta antigua y `CurrentJsonAdapter`;
- detección de `planned` y `plannedDraft` en bundle;
- carga del bundle como documento consolidado único;
- rechazo de mezcla bundle + JSON legado.

## 10. Validación con el bundle de referencia 3394

Para el bundle de referencia con cobertura `2026-08-19` a `2026-10-15`, el adaptador produce:

| Métrica | `planned` | `plannedDraft` |
|---|---:|---:|
| Turnos persona-día | 2.096 | 1.520 |
| Horas netas por segmentos WORK | 14.629,0 | 10.650,0 |
| Descansos internos | 1.357,0 h | 1.166,0 h |
| Ausencias aceptadas | 627 | 627 |
| Fechas de cobertura | 58 | 58 |
| Empleados con presencia | 188 | 188 |

Estos valores proceden de la normalización que alimentará el motor, no de los agregados precalculados del bundle.

## 11. Fuera de alcance de esta fase

- adaptar el HTML autónomo;
- aprovechar `coverage`/`violations` del bundle;
- corregir la resolución histórica de contrato del control semanal;
- introducir fallback entre `planned` y `plannedDraft`;
- cambiar timezone, reglas, operadores, fines de semana o cálculos visuales.

Cualquier diferencia funcional detectada durante las pruebas debe tratarse primero como una incidencia de paridad de fuente, no como una oportunidad de cambiar reglas.
