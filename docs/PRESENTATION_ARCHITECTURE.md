# Arquitectura de presentación Streamlit

## 1. Composición productiva

La UI productiva no es un módulo estático. `streamlit_app.py` instala `schedule_adapter` bajo el nombre histórico `validator_engine` y ejecuta `dashboard_final.py`.

`dashboard_final.py::build_dashboard_source()` obtiene una fuente Python derivada de `app.py` a través de `dashboard_patch.py` → `dashboard_patch_v2.py` → `dashboard_patch_v3.py` y aplica, en orden, extensiones adicionales de presentación.

La prueba `tests/test_dashboard_final_pipeline.py` exige que la fuente final compile y conserve todos los renderizadores obligatorios.

## 2. Renderizadores vigentes

La composición final exige al menos:

```text
render_summary
render_restrictions
render_weekly
render_coverage
render_shift_balance
render_absences
render_weekends
render_workforce_mix
```

Los nombres visibles de pestaña evolucionan mediante reemplazos textuales, pero funcionalmente corresponden a:

- Resumen;
- Restricciones;
- Control/horas contractuales semanal;
- Cobertura diaria;
- Equilibrio de turnos/franjas;
- Ausencias;
- Fines de semana;
- Mix de plantilla;
- metodología/ayuda.

## 3. DataFrames de entrada

La capa de presentación parte de `workforce_validator.dataframes.result_dataframes(result)`:

| Clave | Origen | Uso principal |
|---|---|---|
| `shifts` | `ValidationResult.shifts` | turnos, cobertura, franjas, fines de semana, tablas |
| `summaries` | resumen mensual | KPIs/restricciones, cambios de contrato |
| `incidents` | reglas | detalle de incumplimientos |
| `weekly` | control semanal | horas contractuales, heatmaps, mix, empleados base |
| `absences` | ausencias | detalle y contexto |
| `shift_balance` | analytics base | balance base de dos franjas; la UI productiva lo puede recalcular |
| `absence_daily` | analytics | calendario/cobertura diaria de ausencias |

## 4. Resumen y restricciones

La base de `app.py`, modificada por parches, consume principalmente `summaries` e `incidents` para KPIs y tablas.

**Regla de separación:** los valores de incidencias de las cuatro reglas centrales deben atribuirse a `workforce_validator/rules/` y `summary.py`, no al dashboard.

## 5. Control semanal / horas contractuales

Consume `weekly`.

Cálculos de negocio como `horas_planificadas`, `diferencia_horas`, estado semanal y explicación por ausencia ya vienen del motor.

Cálculos/transformaciones de presentación añadidos posteriormente incluyen:

- heatmap empleado-semana;
- filtros de desviación;
- neutralización **visual** de déficits totalmente explicables por ausencia (`contract_hours_heatmap_dashboard.py`);
- enriquecimiento de etiquetas con horas contractuales;
- alerta de cambios de contrato entre meses consecutivos (`contract_shift_dashboard.py::build_contract_change_table()`).

La neutralización visual no cambia `weekly_rows`.

## 6. Cobertura diaria

Consume `shifts`, `data_dates` y/o `absence_daily` según bloque visual.

`review_iteration_dashboard.py::restrict_to_active_planning_weeks()` filtra de presentación las semanas sin ningún turno positivo en la planificación. Este filtro:

- actúa sobre copias de DataFrames;
- filtra `weekly`, `absences`, `absence_daily` y el conjunto visual de fechas;
- deja `summaries` intacto;
- no modifica el resultado del motor.

Por ello “lo que muestra la UI” puede ser un subconjunto temporal de `ValidationResult`.

## 7. Equilibrio/turnos

Existen dos niveles:

### Analytics base

`workforce_validator/analytics.py::classify_shift_period()` clasifica:

```text
inicio < 13:00 -> MAÑANA
inicio >= 13:00 -> TARDE
```

Ese resultado alimenta el DataFrame base `shift_balance`.

### Renderer productivo actual

`contract_shift_dashboard.py::build_configurable_shift_balance()` recalcula desde `frames["shifts"]` tres franjas con cortes editables:

```text
MAÑANA  si inicio < corte_mañana
CENTRAL si corte_mañana <= inicio <= corte_tarde
TARDE   si inicio > corte_tarde
```

Defaults actuales de UI:

```text
corte mañana: 11:00
corte tarde: 14:00
```

Los límites exactos son centrales; `tests/test_contract_shift_dashboard.py` verifica 11:00 y 14:00 como CENTRAL.

Calcula en presentación:

- turnos por franja;
- horas por franja;
- promedio por semana;
- porcentaje por franja;
- número de franjas cubiertas;
- índice de equilibrio de tres categorías;
- franjas faltantes.

Estos cálculos **no son reglas del motor**.

## 8. Ausencias

Consume `absences`, `absence_daily` y `weekly`.

El dashboard añade visualizaciones como calendario diario, KPIs y lectura explícita de las estimaciones de déficit. La estimación original procede de `weekly_hours.py`; el dashboard puede derivar:

```text
horas_ausencia_aplicables = min(horas_faltantes, horas_potenciales)
planificadas_mas_ausencia = planificadas + horas_ausencia_aplicables
```

Estas columnas son de diagnóstico visual y no imputan horas trabajadas al motor.

## 9. Fines de semana

Esta es la frontera más importante entre presentación y negocio.

### Preparación visual

`dashboard_extensions.py::prepare_weekend_analysis()`:

- toma fechas reales de `data_dates`;
- calcula sábados/domingo evaluables presentes;
- empareja sábado con domingo solo cuando ambos existen en cobertura;
- calcula descanso por empleado y mes.

### Reglas interactivas

`weekend_assignment_dashboard.py` implementa lógica funcional de asignación de recursos de descanso:

- mínimo de fines completos;
- mínimo de sábados;
- mínimo de domingos;
- mínimo flexible de sábados o domingos;
- opción de exigir fines de semana distintos para días flexibles;
- prohibición de reutilizar el mismo día para cumplir dos reglas;
- búsqueda combinatoria mediante estados/DP para decidir si existe una asignación válida.

`weekend_assignment_integration.py` reemplaza el `render_weekends` anterior por esta versión.

**COMPORTAMIENTO OBSERVADO:** esta lógica funciona como regla funcional para el usuario, pero está situada en módulos de presentación, fuera de `workforce_validator/rules/`.

### Visualización de magnitud

`workforce_insights_dashboard.py` reduce la altura de la evolución y añade porcentaje de plantilla con fin de semana completo libre por fin de semana.

## 10. Mix de plantilla

`workforce_insights_dashboard.py::prepare_workforce_mix()` consume `weekly` ya calculado.

Proceso:

1. convierte `applicableWorkingHours` a numérico;
2. elimina nulos;
3. opcionalmente filtra tienda;
4. ordena por `inicio_semana` cuando existe;
5. conserva la última fila por empleado;
6. agrupa por horas contractuales.

Calcula exclusivamente para presentación:

- empleados por tipo de contrato;
- `% plantilla`;
- horas contratadas = contrato × empleados;
- `% horas contratadas`;
- suma total y jornada media para KPIs.

No genera incidencias ni modifica el motor.

## 11. Cálculos de presentación identificados

| Cálculo | Módulo | Naturaleza |
|---|---|---|
| Filtrar semanas globalmente vacías | `review_iteration_dashboard.py` | Filtro visual |
| Lookup de último contrato para enriquecer tablas | `review_iteration_dashboard.py` | Presentación |
| Detectar cambios de contrato entre meses | `contract_shift_dashboard.py` | Alerta de calidad visual |
| Balance configurable 3 franjas | `contract_shift_dashboard.py` | Analytics visual |
| Neutralizar déficit por ausencia en heatmap | `contract_hours_heatmap_dashboard.py` | Solo visual |
| Preparar fines de semana con cobertura real | `dashboard_extensions.py` | Analytics visual con semántica distinta del resumen motor |
| Reglas configurables/asignación de fines de semana | `weekend_assignment_dashboard.py` | Funcional, pero ubicada en presentación |
| Mix contractual | `workforce_insights_dashboard.py` | Informativo |
| % plantilla con fin completo libre | `workforce_insights_dashboard.py` | Informativo |

## 12. Riesgo para una nueva fuente

Una integración que compare únicamente `ValidationResult` puede ser equivalente en motor pero no en producto visible si cambia alguno de los DataFrames o fechas que alimentan estos cálculos de presentación.

Por eso el Golden Master debe comparar dos niveles:

1. **motor**: shifts, absences, incidents, summaries, weekly;
2. **producto**: datasets derivados relevantes para dashboard, incluida preparación de fines de semana y mix.

## 13. Recomendación arquitectónica

### ESTADO ACTUAL

La presentación se compone dinámicamente y contiene analytics/reglas funcionales adicionales.

### RECOMENDACIÓN

Después de demostrar equivalencia de la nueva fuente, extraer progresivamente cálculos funcionales de presentación a módulos estables y testeables. No mezclar ese refactor con la sustitución de fuente.