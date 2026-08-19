# Arquitectura vigente

## 1. Alcance y criterio de auditoría

Este documento describe la arquitectura **que ejecuta hoy el repositorio**, no una arquitectura idealizada. Se ha reconstruido siguiendo imports, `runpy`, sustitución de módulos en `sys.modules`, composición dinámica de código fuente, transformaciones de presentación y tests de pipeline.

La conclusión principal es que **`app.py` no es por sí solo la aplicación productiva**. La entrada productiva recomendada en `README.md` es:

```bash
python -m streamlit run streamlit_app.py
```

### Grafo real de arranque Streamlit

```text
streamlit_app.py
  |
  |-- import schedule_adapter
  |-- sys.modules["validator_engine"] = schedule_adapter
  |
  `-- runpy.run_path("dashboard_final.py", run_name="__main__")
          |
          `-- build_dashboard_source()
                 |
                 |-- lee dashboard_patch_v3.py
                 |     `-- reutiliza dashboard_patch_v2.py
                 |           `-- reutiliza dashboard_patch.py
                 |                 `-- transforma app.py
                 |
                 |-- apply_extensions(...)
                 |-- apply_multi_file_support(...)
                 |-- apply_contract_shift_support(...)
                 |-- apply_review_iteration_support(...)
                 |-- apply_weekend_assignment_support(...)
                 |-- apply_contract_hours_heatmap_support(...)
                 `-- apply_workforce_insights_support(...)
                          |
                          `-- compile(source, "app.py", "exec")
                                  `-- exec(..., __main__)
```

Referencias: `streamlit_app.py`, `dashboard_final.py`, `dashboard_patch_v3.py`, `multi_file_dashboard.py`, `contract_shift_dashboard.py`, `review_iteration_dashboard.py`, `weekend_assignment_integration.py`, `contract_hours_heatmap_dashboard.py`, `workforce_insights_dashboard.py`, `tests/test_dashboard_final_pipeline.py`.

## 2. Clasificación de módulos

| Fichero/módulo | Clasificación | Papel real |
|---|---|---|
| `streamlit_app.py` | Productivo / entrypoint | Arranque Streamlit. Sustituye dinámicamente `validator_engine` por `schedule_adapter` y ejecuta `dashboard_final.py`. |
| `dashboard_final.py` | Productivo / compositor | Construye la fuente final de la UI aplicando capas de presentación y comprueba renderizadores/marcadores obligatorios. |
| `app.py` | Base de presentación | Fuente base sobre la que trabajan los parches. No representa por sí sola la UI productiva final. |
| `schedule_adapter.py` | Fachada de compatibilidad productiva | API que ve la app productiva; reexporta motor modular y añade `combine_planning_documents`. |
| `validator_engine.py` | Fachada de compatibilidad | Reexporta la API modular histórica. La entrada productiva la sustituye en `sys.modules` por `schedule_adapter`. |
| `workforce_validator/` | **Fuente de verdad del motor Python** | Extracción, modelos, reglas, agregados, control semanal y salidas. |
| `dashboard_patch.py`, `dashboard_patch_v2.py`, `dashboard_patch_v3.py` | Parches históricos aún activos | Se encadenan para reconstruir la fuente base que después sigue transformándose. No son legado inerte. |
| `dashboard_extensions.py` | Presentación | Añade helpers y renderizadores, especialmente fines de semana y panel de reglas. |
| `multi_file_dashboard.py` | Presentación/adaptación de entrada | Modifica upload/cache para combinar uno o dos JSON antes de llamar al mismo motor. |
| `contract_shift_dashboard.py` | Presentación/analytics visual | Añade alertas de cambio de contrato y balance configurable mañana-central-tarde. |
| `review_iteration_dashboard.py` | Presentación/filtro visual | Elimina semanas completamente vacías de determinadas vistas y enriquece tablas con contrato. No muta el resultado del motor. |
| `weekend_assignment_dashboard.py` | Lógica funcional situada en presentación | Evalúa reglas configurables de fines de semana y asignación sin reutilizar días. No vive en `workforce_validator/`. |
| `weekend_assignment_integration.py` | Presentación/composición | Sustituye exclusivamente `render_weekends` por la versión configurable. |
| `contract_hours_heatmap_dashboard.py` | Presentación | Neutralización **visual** de déficits totalmente explicables por ausencias en heatmap. |
| `workforce_insights_dashboard.py` | Presentación/analytics visual | `Mix de plantilla` y gráfica de magnitud de descansos. |
| `validador_completo_dos_meses.html` | Lanzador HTML interno | Carga los `reference_payload_*.js` y reconstruye el HTML de referencia. |
| `html_assets/reference_payload_*.js` | Fuente versionada del HTML de referencia | Fragmentos base64+gzip del HTML/JS de referencia. |
| `scripts/build_distributable_html.py` | Generador productivo | Reconstruye HTML, aplica parches y genera `validador_distribuible.html`. |
| `scripts/weekend_html_patch.py`, `scripts/workforce_insights_html_patch.py` | Parches HTML productivos | Mantienen paridad visible/funcional con Streamlit. |
| `validador_distribuible.html` | **Artefacto generado** | Fichero autocontenido entregable. No editar manualmente como fuente de verdad. |
| `script_original_referencia.py` | Referencia histórica | Código de referencia previo; no forma parte del flujo productivo modular actual. |

## 3. Fuente de verdad de la lógica de negocio Python

El flujo de `workforce_validator.engine.run_validation()` es:

```text
run_validation(data, schedule_source, manual_edit_filter, settings)
    |
    |-- filter_schedule_data(...)
    |      workforce_validator/schedule_sources.py
    |
    |-- extract_data(...)
    |      workforce_validator/extraction.py
    |      -> shifts
    |      -> employee_months
    |      -> absences
    |      -> employee_presence_dates
    |
    |-- analyze_shifts(...)
    |      workforce_validator/summary.py
    |      -> run_rules(...)
    |      -> summaries
    |      -> incidents
    |
    |-- collect_data_dates(filtered)
    |      workforce_validator/dates.py
    |
    `-- analyze_weekly_hours(...)
           workforce_validator/weekly_hours.py
           -> weekly_rows

ValidationResult(...)
```

`ValidationResult` (`workforce_validator/models.py`) conserva además `source_data`, `schedule_source`, `data_dates` y el filtro manual efectivo.

## 4. Pipeline de salida

`workforce_validator/dataframes.py::result_dataframes()` transforma el `ValidationResult` en:

- `shifts`;
- `summaries`;
- `incidents`;
- `weekly`;
- `absences`;
- `shift_balance`;
- `absence_daily`.

`workforce_validator/excel.py::build_excel_bytes()` exporta cinco datasets funcionales: turnos, validación mensual, incidencias, control semanal y ausencias, además de una hoja de información.

Streamlit consume los DataFrames y después aplica cálculos adicionales de presentación. Es esencial no interpretar esos cálculos visuales como parte automática del motor.

## 5. Frontera actual Fuente → Motor

### Acoplamiento existente

Hoy `run_validation()` todavía recibe un `dict` con la estructura del JSON vigente. Por tanto, el motor **no está completamente desacoplado de la fuente**: `schedule_sources.py`, `extraction.py` y `dates.py` conocen `storeDayTimes`, `people`, `dayTimes`, etc.

### Frontera conceptual recomendada

```text
NUEVA FUENTE
   |
   v
SourceAdapter
   |
   v
MODELO CANÓNICO
   |
   +--> shifts: list[ShiftRow]
   +--> absences: list[AbsenceDay]
   +--> employee_months / contrato
   +--> employee_presence_dates
   +--> data_dates
   |
   v
MOTOR EXISTENTE
   +--> rules/
   +--> summary.py
   +--> weekly_hours.py
   +--> analytics.py
   +--> dataframes.py / excel.py
```

**RECOMENDACIÓN:** para una nueva fuente, evitar recrear artificialmente `storeDayTimes`; adaptar directamente a las estructuras semánticas que necesita el motor o introducir un contrato explícito equivalente.

## 6. Qué debería mantenerse intacto al sustituir la fuente

Siempre que el adaptador produzca semántica idéntica, son candidatos fuertes a no modificarse:

- `workforce_validator/rules/`;
- `workforce_validator/summary.py`;
- `workforce_validator/weekly_hours.py`;
- `workforce_validator/dates.py` en sus helpers de continuidad/semana/fin de semana, aunque `collect_data_dates()` sí está acoplado al JSON;
- `workforce_validator/analytics.py`;
- `workforce_validator/dataframes.py`;
- `workforce_validator/excel.py`;
- `config/rules.json` y `workforce_validator/config.py`.

La capa a sustituir o aislar es principalmente:

- lectura del formato (`io.py` para JSON actual);
- detección de fuentes (`schedule_sources.py`);
- extracción (`extraction.py`);
- `collect_data_dates()`;
- combinación de documentos (`multi_file.py`) cuando la nueva fuente no sea “uno/dos JSON mensuales”.

## 7. COMPORTAMIENTO OBSERVADO vs arquitectura recomendada

### COMPORTAMIENTO OBSERVADO

La UI productiva se obtiene mediante transformaciones textuales y `exec()` sobre `app.py`. Los parches históricos siguen siendo parte del runtime. Algunas reglas funcionales de fines de semana y algunos analytics viven fuera de `workforce_validator/`.

### INTENCIÓN PROBABLE

La composición incremental parece haber permitido evolucionar la interfaz sin reescribir una base grande y mantener compatibilidad con versiones previas.

### DUDA FUNCIONAL

No puede demostrarse por código si todos los cálculos actualmente situados en presentación —especialmente reglas configurables de fines de semana— deben considerarse formalmente “reglas de negocio” a largo plazo o únicamente análisis interactivos.

### RECOMENDACIÓN

Antes de sustituir la fuente de datos, introducir una frontera explícita de adaptador/modelo canónico y consolidar posteriormente la composición de presentación. **No realizar esa consolidación durante una migración de fuente**: primero demostrar equivalencia funcional mediante Golden Master.