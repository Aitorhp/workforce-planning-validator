# Reglas de negocio y agregación mensual

## 1. Registro de reglas

La ejecución de reglas está centralizada en `workforce_validator/rules/registry.py::run_rules()`.

Orden actual del registro:

```python
RULES = (
    max_shift_duration.validate,
    min_shift_duration.validate,
    min_rest_between_shifts.validate,
    max_consecutive_days.validate,
)
```

Cada regla devuelve objetos `Incident`; el registro concatena y ordena por tienda, empleado, mes, fecha de inicio y tipo.

## 2. Configuración vigente

Fuente: `config/rules.json`, cargada y validada por `workforce_validator/config.py`.

| Parámetro | Valor actual | Naturaleza |
|---|---:|---|
| `calculation.max_internal_break_hours` | `1.0` h | Configuración de construcción de turno |
| `calculation.weekly_hours_tolerance` | `0.01` h | Configuración del control semanal |
| `rules.max_consecutive_days.limit` | `5` | Configuración de regla |
| `rules.max_shift_hours.limit` | `7.5` h | Configuración de regla |
| `rules.min_shift_hours.limit` | `4.0` h | Configuración de regla |
| `rules.min_rest_hours.limit` | `11.0` h | Configuración de regla |

Cada regla puede deshabilitarse mediante `enabled`. La ruta de configuración puede sustituirse con `WORKFORCE_VALIDATOR_CONFIG`.

**No interpretar estos valores como constantes conceptuales.** Son los valores vigentes de configuración.

## 3. Matriz exacta de reglas

| Regla | Fichero / función | Input | Fórmula/criterio | Operador exacto que incumple | Límite actual | Output |
|---|---|---|---|---|---:|---|
| Máximo de turno | `rules/max_shift_duration.py::validate` | cada `ShiftRow.worked_hours` | compara horas netas del turno | `worked_hours > limit` | 7.5 h | `TURNO_SUPERIOR_7_5H` |
| Mínimo de turno | `rules/min_shift_duration.py::validate` | cada `ShiftRow.worked_hours` | compara horas netas del turno | `worked_hours < limit` | 4 h | `TURNO_INFERIOR_4H` |
| Descanso entre jornadas | `rules/min_rest_between_shifts.py::validate` | turnos consecutivos del empleado | `(current.shift_start - previous.shift_end) / 3600` | `rest < limit` | 11 h | `DESCANSO_INFERIOR_11H` |
| Días consecutivos | `rules/max_consecutive_days.py::validate` | fechas `work_day` del empleado | rachas de fechas únicas adyacentes | `len(streak) > limit` | 5 días | `MAS_DE_5_DIAS_CONSECUTIVOS` |

Los tests de frontera están en `tests/test_rules.py`.

## 4. Casos frontera demostrados

- turno exactamente `7.5 h`: cumple;
- turno `> 7.5 h`: incidencia;
- turno exactamente `4 h`: cumple;
- turno `< 4 h`: incidencia;
- descanso exactamente `11 h`: cumple;
- descanso `< 11 h`: incidencia;
- racha exactamente `5 días`: cumple;
- racha `6 días`: incidencia.

Esto implica que los operadores de conformidad son, respectivamente, `<=`, `>=`, `>=` y `<=`.

## 5. Construcción del turno que alimenta las reglas

Fuente: `workforce_validator/extraction.py::extract_data()`.

Para el horario seleccionado:

1. conserva únicamente segmentos `hourType == WORK` de forma case-insensitive;
2. ignora segmentos sin inicio o fin;
3. parsea ambos timestamps;
4. exige `end > start`; de lo contrario lanza `ValueError`;
5. ordena por inicio;
6. `shift_start` = inicio del primer segmento;
7. `shift_end` = máximo fin de todos los segmentos;
8. `worked_hours` = suma de **todas las duraciones de los segmentos**;
9. `break_hours` = suma de gaps positivos entre segmentos cuando `gap <= max_internal_break_hours`.

### Ejemplo A — gap interno dentro del umbral

```text
08:00-12:00 = 4.0 h
12:30-16:00 = 3.5 h
gap = 0.5 h
```

Resultado:

```text
shift_start = 08:00
shift_end   = 16:00
worked_hours = 7.5
break_hours  = 0.5
```

La duración de reglas de turno es `7.5`, no las 8 horas de envolvente.

### Ejemplo B — gap exactamente igual al límite actual

```text
08:00-12:00
13:00-16:00
```

Con límite `1.0 h`, el gap cuenta como `break_hours = 1.0` porque la condición es `0 < gap <= max_internal_break`.

### Ejemplo C — gap superior al límite

```text
08:00-12:00
13:30-16:00
```

Resultado:

```text
shift_start = 08:00
shift_end   = 16:00
worked_hours = 6.5
break_hours  = 0.0
```

El gap de 1.5 h no se contabiliza como descanso interno, pero tampoco se suma a horas trabajadas. La envolvente temporal sigue terminando a las 16:00.

### Solapamientos

**COMPORTAMIENTO OBSERVADO:** `worked_hours` suma cada duración sin fusionar intervalos solapados. Dos segmentos solapados pueden, por tanto, duplicar tiempo en la suma. No existe validación específica de solape.

**DUDA FUNCIONAL:** debe confirmarse si la fuente garantiza que nunca existen segmentos WORK solapados.

## 6. Días consecutivos y meses

`dates.py::find_consecutive_streaks()`:

- elimina duplicados con `set`;
- ordena fechas;
- una fecha continúa la racha cuando es exactamente `día_anterior + 1 día`;
- no reinicia en el cambio de mes.

`max_consecutive_days.validate()` genera una incidencia por **cada mes tocado por la racha incumplidora**, pero cada incidencia conserva el inicio, fin y longitud de la racha completa.

Ejemplo demostrado por `test_cross_month_streak_is_reported_in_both_months`: una racha de seis días del 29/07 al 03/08 produce incidencias en `2026-07` y `2026-08`.

## 7. Descanso entre jornadas

`min_rest_between_shifts.validate()` agrupa por `(store_id, person_id)`, ordena los turnos por `(shift_start, shift_end)` y compara pares consecutivos.

```text
rest_hours = current.shift_start - previous.shift_end
```

No usa `work_day` para calcular el número de horas, salvo para etiquetar fechas y asignar la incidencia al mes del turno actual.

Si un turno termina un día a las 20:00 y el siguiente empieza a las 07:00 del día siguiente, el descanso es 11 h y cumple exactamente.

## 8. Agregación mensual

Fuente: `workforce_validator/summary.py::build_monthly_summaries()`.

Granularidad:

```text
tienda + empleado + mes
```

La lista de filas nace de `employee_months`; un empleado puede tener resumen mensual aunque no haya turnos.

Campos principales:

| Campo | Cálculo |
|---|---|
| `dias_trabajados` | número de `work_day` únicos de turnos del mes |
| `max_dias_consecutivos` | longitud máxima de cualquier racha global del empleado que toque ese mes |
| `incidencias_dias_consecutivos` | número de Incident del tipo configurado para ese mes |
| `turnos_superiores_7_5h` | count de incidencias max-turno del mes |
| `turnos_inferiores_4h` | count de incidencias min-turno del mes |
| `descansos_inferiores_11h` | count de incidencias descanso del mes |
| `cumple_*` | `SI` cuando el contador correspondiente es 0 |
| `cumple_todas_las_reglas` | `SI` cuando la suma de los cuatro contadores es 0 |
| `fines_semana_completos_libres` | `dates.weekend_counts()` |
| `sabados_libres` | `dates.weekend_counts()` |
| `domingos_libres` | `dates.weekend_counts()` |

### Etiquetas con límites embebidos

Los nombres `cumple_max_5_dias`, `turnos_superiores_7_5h`, `turnos_inferiores_4h`, `descansos_inferiores_11h` contienen los valores actuales en el nombre de columna aunque los límites son configurables.

**DEUDA TÉCNICA:** si se modifica `config/rules.json`, la lógica cambia pero los nombres de columna podrían quedar semánticamente desactualizados.

## 9. Fines de semana del resumen mensual

`dates.py::weekend_counts(year, month, worked_days)` genera **todos los días calendario del mes**, no solo `data_dates`.

- sábado libre = sábado calendario no presente en `worked_days`;
- domingo libre = domingo calendario no presente en `worked_days`;
- fin de semana completo = sábado no trabajado, domingo siguiente en **el mismo mes** y tampoco trabajado.

Consecuencias:

1. un sábado del último día del mes cuyo domingo cae en el mes siguiente **no** cuenta como fin de semana completo en este resumen;
2. si el fichero no contiene determinados sábados/domingo, el motor mensual puede interpretarlos como libres porque solo contrasta contra `worked_days`.

La pestaña Streamlit de fines de semana utiliza actualmente otra lógica basada en `data_dates`; ver `PRESENTATION_ARCHITECTURE.md` y `TEMPORAL_LOGIC.md`.

## 10. Referencias de prueba

- `tests/test_rules.py`: operadores exactos y racha entre meses.
- `tests/test_regression.py`: integración reglas + resumen + semanal + Excel.
- `tests/test_config_and_sources.py`: configuración externa y desactivación de regla.

## 11. Regla para una nueva fuente

La nueva fuente debe reproducir primero el mismo `ShiftRow.worked_hours`, `shift_start`, `shift_end` y `work_day`. Si esos valores cambian, cambiarán simultáneamente varias reglas y no podrá atribuirse la diferencia al motor.