# Modelo canónico requerido por el motor

## 1. Objetivo

El modelo canónico representa la **semántica mínima** que una fuente alternativa debe aportar para reproducir el comportamiento del validador. No obliga a imitar `storeDayTimes` ni ninguna jerarquía del JSON actual.

La conclusión de la auditoría es que el motor posterior a extracción necesita cinco familias de información:

1. turnos normalizados;
2. ausencias aceptadas;
3. horas contractuales/aplicables;
4. presencia del empleado en la fuente por fecha;
5. cobertura temporal global del dataset.

Los modelos existentes `ShiftRow` y `AbsenceDay` ya cubren buena parte de ese contrato. `employee_months`, `employee_presence_dates` y `data_dates` son estructuras auxiliares no encapsuladas actualmente en dataclasses.

## 2. Entidades canónicas

### 2.1 Empleado / contrato aplicable

| Campo canónico | Tipo | Obligatorio | Semántica | Regla/cálculo dependiente |
|---|---|---:|---|---|
| `store_id` | scalar/string-like | Sí | Tienda lógica | Todas las agrupaciones. |
| `person_id` | scalar/string-like | Sí | Identidad estable del empleado | Todas las agrupaciones. |
| `applicable_working_hours` | número, texto numérico o nulo | Sí como concepto; valor puede faltar | Horas contractuales/aplicables usadas en control semanal y resúmenes | `summary.py`, `weekly_hours.py`, dashboards de contrato/mix. |
| `presence_dates` | `set[date]` por empleado | Sí | Fechas en que el empleado aparece en la fuente, independientemente de trabajar | `AUSENTE TODO EL PERIODO`; trazabilidad de cobertura personal. |
| `employee_month_contract` | mapping `(store, person, YYYY-MM) -> valor` | Sí para equivalencia exacta actual | Último valor observado para ese empleado-mes durante extracción | `summary.py`; semilla de contrato semanal. |

**Nota de equivalencia:** aunque arquitectónicamente sería preferible un contrato versionado por fecha/semana, el comportamiento vigente utiliza `employee_months` y después colapsa a un valor global por empleado en `weekly_hours.py`. Una réplica Golden Master debe preservar primero esa resolución.

### 2.2 Turno

Equivalente directo a `workforce_validator.models.ShiftRow`.

| Campo canónico | Tipo | Obligatorio | Semántica | Regla/cálculo dependiente |
|---|---|---:|---|---|
| `store_id` | scalar | Sí | Tienda | Agrupación. |
| `person_id` | scalar | Sí | Empleado | Agrupación. |
| `work_day` | `date` | Sí | Día operativo asignado por la fuente, no necesariamente `shift_start.date()` | Mes, semana, días consecutivos, fines de semana. |
| `shift_start` | `datetime` naive en semántica actual | Sí | Inicio del primer segmento WORK después de normalización | Descanso entre jornadas, franja visual. |
| `shift_end` | `datetime` naive | Sí | Máximo fin de los segmentos WORK | Descanso entre jornadas, detalle. |
| `worked_hours` | `float` | Sí | Suma de duraciones de segmentos WORK, redondeada a 4 decimales | Duración min/max, semanal, analytics. |
| `break_hours` | `float` | Sí | Suma de gaps positivos entre segmentos consecutivos cuyo gap es `<= max_internal_break_hours` | Salida/visualización; no modifica `worked_hours`. |
| `applicable_working_hours` | valor original del persona-día | Sí como concepto | Contrato asociado al día del turno | Resolución semanal y salidas. |

### 2.3 Segmentos de trabajo — entidad necesaria en el adaptador

El motor post-extracción consume turnos ya agregados, pero para reproducir **exactamente** la construcción actual el adaptador debe disponer temporalmente de segmentos:

| Campo | Tipo | Obligatorio | Semántica |
|---|---|---:|---|
| `segment_start` | datetime | Sí | Inicio WORK. |
| `segment_end` | datetime | Sí | Fin WORK, estrictamente mayor que inicio. |
| `segment_kind` | enum/concepto | Sí antes de filtrar | Debe permitir identificar trabajo equivalente a `hourType == WORK`. |
| `schedule_source` | `planned` / `plannedDraft` | Sí si existen varias versiones | Origen al que pertenece. |
| `manual_edit_state` | true / false / missing | Solo para draft | Estado trivalente necesario para filtros. |

Una nueva fuente que ya entregue turnos agregados puede omitir segmentos **solo si puede demostrar que `worked_hours`, `shift_start`, `shift_end` y `break_hours` son idénticos a los que produciría el algoritmo actual**.

### 2.4 Ausencia

Equivalente a `AbsenceDay`.

| Campo canónico | Tipo | Obligatorio | Semántica | Regla/cálculo dependiente |
|---|---|---:|---|---|
| `store_id` | scalar | Sí | Tienda | Agrupación. |
| `person_id` | scalar | Sí | Empleado | Agrupación. |
| `absence_day` | `date` | Sí | Día operativo de ausencia | Semanal, analytics diarios. |
| `absence_type` | `str` | Sí | Nombre/etiqueta normalizada | Contexto y explicación. |
| `absence_status` | `str` | Sí | Estado aceptado, hoy `VALIDATED` o `APPROVED` | Trazabilidad. |

El adaptador debe aplicar o reproducir la deduplicación actual por persona-día `(absence_type, absence_status)`.

### 2.5 Cobertura temporal del dataset

| Campo canónico | Tipo | Obligatorio | Semántica | Regla/cálculo dependiente |
|---|---|---:|---|---|
| `data_dates` | `set[date]` | Sí | Fechas que la fuente afirma contener, aunque nadie trabaje | Evaluabilidad semanal, ausencia diaria, presentación de fines de semana. |
| `first_date` | derivado | No | `min(data_dates)` | Inicio de scope. |
| `last_date` | derivado | No | `max(data_dates)` | Fin de scope. |
| `covered_day_count` | derivado | No | `len(data_dates)` | Diagnóstico. |

**Invariante crítico:** `data_dates` no es “días con turnos”. Es “días existentes en la fuente”.

## 3. Contrato canónico agregado propuesto

Sin imponer implementación, una interfaz suficiente sería conceptualmente:

```python
CanonicalDataset(
    shifts: list[ShiftRow],
    absences: list[AbsenceDay],
    employee_months: dict[(store_id, person_id, month), Any],
    employee_presence_dates: dict[(store_id, person_id), set[date]],
    data_dates: set[date],
    schedule_source: str,
    manual_edit_filter: str,
)
```

Con esto podrían ejecutarse directamente:

```text
rules/ -> summary.py -> weekly_hours.py -> analytics/dataframes/excel
```

sin que esas capas conozcan el formato externo.

## 4. Dependencias adicionales detectadas

Para la **aplicación completa**, no solo el núcleo de reglas, también deben preservarse:

- `schedule_source`, usado en metadatos/Excel/UI;
- filtro manual efectivo;
- contrato asociado a cada ShiftRow;
- `data_dates` completo para dashboards;
- tienda/empleado comparables de forma estable;
- granularidad mensual del contrato para `summaries` y para la alerta visual de cambios contractuales.

No se ha encontrado una dependencia productiva del motor modular de atributos nominales de empleado.

## 5. Invariantes de normalización

Cualquier adaptador debe garantizar antes del motor:

- un `work_day` válido por turno;
- `shift_end > shift_start`;
- orden temporal reproducible;
- horas netas en horas decimales;
- redondeo equivalente a 4 decimales donde hoy se aplica;
- identificación estable tienda/persona;
- estados de ausencia normalizados según la semántica vigente;
- distinción entre ausencia y no trabajo;
- cobertura temporal independiente de existencia de turnos.

## 6. Frontera recomendada

```text
Fuente específica
   |
   | parsea nombres/rutas/códigos propios
   v
SourceAdapter
   |
   | resuelve schedule source, edición manual,
   | segmentos WORK, contratos, ausencias y cobertura
   v
CanonicalDataset
   |
   v
Motor estable
```

### Qué NO debería conocer el motor tras el refactor futuro

- `storeDayTimes`;
- `people`;
- `dayTimes`;
- claves concretas de una API o base de datos;
- nombres de columnas CSV;
- payloads específicos de una fuente.

## 7. COMPORTAMIENTO OBSERVADO y recomendación

### COMPORTAMIENTO OBSERVADO

El repositorio ya posee un modelo interno parcial (`ShiftRow`, `AbsenceDay`, `Incident`, `ValidationResult`), pero la entrada de `run_validation()` sigue siendo el JSON específico.

### RECOMENDACIÓN

Crear en una fase posterior un `CanonicalDataset` o interfaz equivalente y ofrecer dos entradas:

```text
CurrentJsonAdapter -> CanonicalDataset
NewSourceAdapter  -> CanonicalDataset
```

Ambas deben pasar la misma suite Golden Master antes de retirar cualquier compatibilidad con el JSON actual.