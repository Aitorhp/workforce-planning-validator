# Pruebas, equivalencia y Golden Master

## 1. Objetivo

La sustitución de la fuente debe demostrarse mediante resultados, no por similitud de arquitectura. La referencia funcional es el comportamiento actual.

```text
Fuente actual -> pipeline actual -> GOLDEN MASTER
Nueva fuente -> adaptador -> mismo significado -> resultados candidatos
```

La comparación debe hacerse en varios niveles para localizar exactamente una divergencia.

## 2. Suite actual inventariada

| Test | Cobertura principal |
|---|---|
| `tests/test_rules.py` | límites exactos de las cuatro reglas y racha entre meses |
| `tests/test_schedule_sources.py` | planned/draft, filtro manual, booleano no fuente |
| `tests/test_config_and_sources.py` | fuentes y configuración externa/desactivación |
| `tests/test_source_detection_cache.py` | detección/caché de origen en UI |
| `tests/test_regression.py` | snapshot funcional end-to-end y hojas Excel |
| `tests/test_analytics.py` | balance base 13:00 y ausencia diaria |
| `tests/test_multi_file.py` | combinación/rechazos de uno/dos meses |
| `tests/test_multi_file_dashboard.py` | integración de carga múltiple en dashboard |
| `tests/test_public_api.py` | compatibilidad de API pública |
| `tests/test_dashboard_final_pipeline.py` | composición final, marcadores y compilación |
| `tests/test_contract_shift_dashboard.py` | cambio contrato y franjas configurables |
| `tests/test_review_iteration_dashboard.py` | filtro de semanas vacías, lookup contrato, umbrales legacy de weekend |
| `tests/test_contract_hours_heatmap_dashboard.py` | parche visual de horas/ausencias |
| `tests/test_weekend_assignment_dashboard.py` | asignación de días de descanso sin reutilización |
| `tests/test_weekend_html_patch.py` | parche HTML de weekend |
| `tests/test_workforce_insights_dashboard.py` | Mix de plantilla y magnitud weekend |
| `tests/test_workforce_insights_html_patch.py` | paridad estructural HTML de insights |
| `tests/test_html_dashboard.py` | SHA/features del HTML de referencia y autocontención |

## 3. Huecos relevantes detectados

La suite actual no demuestra exhaustivamente:

- gaps internos exactamente por debajo/encima del umbral;
- segmentos solapados;
- timestamps con offsets distintos;
- turno cruzando medianoche con `operatingDate` distinto del `date()` de fin;
- resolución de `applicableWorkingHours` cambiante aplicada globalmente a semanas anteriores;
- contrato no convertible/`None` en una semana completa;
- todos los estados de ausencia no aceptados;
- deduplicación exacta de ausencias;
- semana de 6 días de cobertura como caso unitario directo;
- cambio de año ISO;
- diferencia entre fines de semana de `summary.py` y dashboard;
- duplicados internos de `storeDayTimes`;
- equivalencia numérica Python ↔ JavaScript/HTML.

## 4. Golden Master por capas

### Nivel A — normalización

Comparar exactamente, ordenando por claves estables:

```text
ShiftRow:
store_id, person_id, work_day, shift_start, shift_end,
worked_hours, break_hours, applicable_working_hours

AbsenceDay:
store_id, person_id, absence_day, absence_type, absence_status

employee_months
employee_presence_dates
data_dates
```

### Nivel B — motor

Comparar:

- `Incident`;
- `summaries`;
- `weekly_rows`.

### Nivel C — salidas

Comparar DataFrames de `result_dataframes()` después de normalizar:

- fechas/datetimes a ISO;
- NaN/None a una representación común;
- floats con tolerancia únicamente donde el código ya redondea;
- orden de filas por claves funcionales.

### Nivel D — presentación

Comparar datasets derivados por:

- `prepare_weekend_analysis()`;
- `evaluate_weekend_rule_table()`;
- `build_configurable_shift_balance()`;
- `build_contract_change_table()`;
- `prepare_workforce_mix()`;
- filtro de semanas activas.

### Nivel E — HTML

Exponer o capturar estructuras equivalentes del JavaScript y comparar contra las salidas Python. Los tests actuales de presencia de features no sustituyen esta prueba.

## 5. Columnas exactas vs normalizables

### Comparación exacta

- ids;
- fechas;
- estados;
- tipos de incidencia;
- contadores enteros;
- flags `SI/NO`;
- ISO year/week;
- nombres de ausencia;
- fuentes/filtros.

### Normalización permitida

- datetimes: representación ISO equivalente **sin cambiar timezone semántico**;
- floats ya redondeados por motor: comparar al mismo número de decimales;
- `None`, `NaN` y celdas vacías: normalizar antes de comparar si la serialización difiere;
- orden de DataFrame: ordenar por claves antes de assert si el orden no es contractual.

No normalizar diferencias funcionales como `39.99` vs `40.00`, distinto día operativo o distinta cobertura.

## 6. Casos frontera obligatorios

Los siguientes casos deben materializarse como fixtures unitarios. “Resultado esperado” se refiere al comportamiento vigente.

| # | Entrada mínima | Resultado esperado | Responsable | Motivo |
|---:|---|---|---|---|
| 1 | 09:00–13:00 WORK | 4 h; sin incidencia mínima | `extraction`, `min_shift_duration.validate` | operador `<` |
| 2 | 09:00–12:59 | incidencia mínima | misma | `< 4` |
| 3 | 09:00–16:30 | 7.5 h; sin incidencia máxima | `max_shift_duration.validate` | operador `>` |
| 4 | 09:00–16:31 | incidencia máxima | misma | `> 7.5` |
| 5 | turno fin 20:00, siguiente inicio 07:00 | 11 h; cumple | `min_rest_between_shifts.validate` | operador `<` |
| 6 | siguiente 06:59 | incidencia descanso | misma | `< 11` |
| 7 | cinco `work_day` consecutivos | cumple | `find_consecutive_streaks`, regla | `> 5` |
| 8 | seis consecutivos | una racha incumplidora | misma | límite exacto |
| 9 | 29/07–03/08 seis días | racha 6; incidencia en ambos meses | regla + summary | no reset mensual |
| 10 | `data_dates` lunes-domingo | `dias_cubiertos=7`, evaluable | `weekly_hours` | cobertura completa |
| 11 | falta una fecha en `data_dates` | `dias_cubiertos=6`, `NO EVALUABLE` | misma | fichero ≠ empleado |
| 12 | semana en frontera ISO | `ano_iso/semana_iso` de `isocalendar()` | misma | cambio de año |
| 13 | sábado+domingo cubiertos y sin turno | fin completo libre en dashboard | `prepare_weekend_analysis` / weekend assignment | pareja evaluable |
| 14 | sábado fin de mes + domingo mes siguiente | motor mensual no lo cuenta; dashboard puede contar si ambos cubiertos | `weekend_counts` vs dashboard | divergencia vigente |
| 15 | ausencia `APPROVED` | extraída | `extract_data` | estado aceptado |
| 16 | ausencia `VALIDATED` | extraída | misma | estado aceptado |
| 17 | ausencia `PENDING` u otro | ignorada | misma | whitelist |
| 18 | ausencia aceptada + turno mismo día | ausencia existe, pero no explica déficit | `weekly_hours` | exclusión worked day |
| 19 | presencia solo en días con ausencia, cero turnos | `AUSENTE TODO EL PERIODO` | `weekly_hours` | caso especial |
| 20 | contrato `None` y semana completa | `SIN HORAS CONTRATO` | `weekly_hours` | conversión fallida |
| 21 | diferencia absoluta `<= 0.01` | `COINCIDE` | `weekly_hours` | tolerancia inclusive |
| 22 | 08-12 + 12:30-16 | inicio 08, fin16, work7.5, break0.5 | `extract_data` | múltiples segmentos |
| 23 | gap 0.5 con límite1 | gap suma a break | misma | `0 < gap <= limit` |
| 24 | gap 1.5 con límite1 | no suma break; work sigue suma segmentos | misma | gap superior |
| 25 | `planned` con WORK | turno desde published; filtro manual ignorado | source filter + extraction | fuente 1 |
| 26 | `plannedDraft` con WORK | turno desde draft | misma | fuente 2 |
| 27 | draft flag True + `edited` | incluido | `_matches` | identidad booleana |
| 28 | flag False + `not_edited` | incluido | `_matches` | identidad booleana |
| 29 | flag ausente + filtro edited/not_edited | excluido; con `all` incluido | `_matches` | estado trivalente |
| 30 | dos ficheros, misma tienda, meses consecutivos sin solape | combinar; continuidad temporal entre ambos | `combine_planning_documents` + engine | periodo conjunto |
| 31 | dos ficheros con cualquier fecha común | `ValueError`; no ejecutar motor | `combine_planning_documents` | solapamiento prohibido |

## 7. Casos adicionales recomendados

### Segmentos solapados

```text
08:00-12:00
11:00-15:00
```

El comportamiento actual suma 8 h de trabajo, no 7 h de unión. Debe congelarse como Golden Master o confirmarse como dato imposible.

### Offset horario

Comparar `09:00+02:00` y `09:00Z`: ambos pierden `tzinfo` sin conversión y quedan 09:00 naive. Este caso documenta el comportamiento actual, aunque pueda ser técnicamente indeseable.

### Cambio contractual

Empleado 40 h en agosto y 30 h en septiembre con turnos en ambos: congelar qué valor aplica actualmente a todas las semanas y usarlo como referencia antes de cualquier rediseño.

### Duplicado de operatingDate dentro de un solo JSON

Documentar/snapshotear el comportamiento porque multi-file no lo rechaza internamente.

## 8. Fixture Golden Master recomendado

Crear un conjunto pequeño pero expresivo con:

- dos empleados;
- dos meses consecutivos;
- una semana que cruza mes;
- contrato cambiante;
- segmentos múltiples;
- ausencia aceptada y no aceptada;
- draft editado/no editado/missing;
- turno largo/corto;
- racha de seis días;
- descanso de 10h59 y 11h;
- fin de semana de frontera mensual.

Persistir snapshots como JSON/CSV legibles, no únicamente pickle binario.

## 9. Estrategia de migración segura

### Fase 1

Congelar snapshots del pipeline actual sin introducir adaptador.

### Fase 2

Implementar `CurrentJsonAdapter` y demostrar igualdad contra esos snapshots.

### Fase 3

Implementar `NewSourceAdapter`; para entradas funcionalmente equivalentes debe generar el mismo modelo canónico.

### Fase 4

Comparar salidas del motor y presentación.

### Fase 5

Comparar HTML/JavaScript.

### Fase 6

Solo tras equivalencia, discutir correcciones funcionales o deuda técnica en una iteración separada.

## 10. Criterio de aceptación

La migración no está validada mientras exista una diferencia no explicada en cualquiera de:

```text
turnos
ausencias
presencia
cobertura
incidencias
resúmenes
weekly
fines de semana
contratos
analytics visuales
HTML
```

Una diferencia “más correcta” sigue siendo una diferencia funcional y debe aprobarse explícitamente fuera del objetivo de equivalencia.