# Workforce Planning Validator — guía técnica de referencia

Esta carpeta documenta el comportamiento vigente del proyecto con un objetivo concreto: permitir que otra IA o desarrollador sustituya la fuente de datos sin cambiar el significado funcional ni los resultados del validador.

> **Principio rector:** cambiar la fuente de los datos sin cambiar el significado de los datos; después, cambiar el adaptador sin cambiar el motor de validación.

## Cómo leer esta documentación

Si no conoces el proyecto, sigue este orden:

1. [ARCHITECTURE.md](ARCHITECTURE.md) — arranque real, grafo de ejecución, clasificación de módulos y frontera entre fuente, motor y presentación.
2. [DATA_MODEL_CURRENT.md](DATA_MODEL_CURRENT.md) — estructura del JSON actual y todos los campos de origen consumidos.
3. [SCHEDULE_SOURCES.md](SCHEDULE_SOURCES.md) — semántica exacta de `planned`, `plannedDraft` y `plannedDraftManuallyEdited`.
4. [CANONICAL_DATA_MODEL.md](CANONICAL_DATA_MODEL.md) — contrato semántico mínimo que debería producir una nueva fuente.
5. [BUSINESS_RULES.md](BUSINESS_RULES.md) — reglas, operadores exactos, límites configurables y agregación mensual.
6. [TEMPORAL_LOGIC.md](TEMPORAL_LOGIC.md) — día operativo, timestamps, meses, semanas ISO, cobertura, rachas y fines de semana.
7. [WEEKLY_HOURS.md](WEEKLY_HOURS.md) — horas contractuales, control semanal y estados.
8. [ABSENCE_LOGIC.md](ABSENCE_LOGIC.md) — extracción de ausencias y estimación explicativa de déficit.
9. [MULTI_FILE_BEHAVIOR.md](MULTI_FILE_BEHAVIOR.md) — combinación de uno/dos ficheros y efectos temporales.
10. [PRESENTATION_ARCHITECTURE.md](PRESENTATION_ARCHITECTURE.md) — composición dinámica Streamlit y cálculos exclusivamente visuales.
11. [HTML_PARITY.md](HTML_PARITY.md) — arquitectura del HTML autónomo, generador, payloads, parches y regla de paridad.
12. [NEW_DATA_SOURCE_GUIDE.md](NEW_DATA_SOURCE_GUIDE.md) — diseño conceptual del adaptador y qué módulos deben conservarse.
13. [DATA_SOURCE_MAPPING_TEMPLATE.md](DATA_SOURCE_MAPPING_TEMPLATE.md) — matriz de equivalencia preparada para una nueva fuente.
14. [TESTING_AND_GOLDEN_MASTER.md](TESTING_AND_GOLDEN_MASTER.md) — cobertura actual, huecos, Golden Master y 31 casos frontera.
15. [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) — duplicidad, legado, acoplamientos y recomendaciones separadas del estado actual.

## Convención de evidencia

La documentación usa cuatro etiquetas cuando existe riesgo de mezclar hechos e interpretación:

- **COMPORTAMIENTO OBSERVADO**: demostrable leyendo código o tests actuales.
- **INTENCIÓN PROBABLE**: interpretación funcional razonable, no confirmada por el código.
- **DUDA FUNCIONAL**: requiere decisión del propietario del producto.
- **RECOMENDACIÓN**: propuesta futura; no describe el comportamiento vigente.

Las recomendaciones no deben utilizarse como especificación para reproducir resultados actuales.

## Fuente de verdad por capa

| Capa | Fuente de verdad vigente |
|---|---|
| Lectura JSON | `workforce_validator/io.py` |
| Detección/filtrado de origen de horario | `workforce_validator/schedule_sources.py` |
| Extracción al modelo interno | `workforce_validator/extraction.py` |
| Modelos internos | `workforce_validator/models.py` |
| Reglas | `workforce_validator/rules/` + `config/rules.json` |
| Agregación mensual | `workforce_validator/summary.py` |
| Control semanal | `workforce_validator/weekly_hours.py` |
| Orquestación | `workforce_validator/engine.py` |
| DataFrames | `workforce_validator/dataframes.py` |
| Excel | `workforce_validator/excel.py` |
| Entrada Streamlit productiva | `streamlit_app.py` |
| Composición Streamlit final | `dashboard_final.py` + capas `dashboard_*`/módulos de presentación |
| HTML de referencia | `html_assets/reference_payload_*.js` reconstruidos por `scripts/build_distributable_html.py` |
| HTML distribuible | `validador_distribuible.html` — artefacto generado, **no fuente de verdad** |

## Invariantes que una réplica debe preservar

Una nueva integración no es equivalente solo porque “muestra los mismos gráficos”. Debe preservar, como mínimo:

- identidad de tienda y empleado;
- conjunto exacto de fechas cubiertas por el dataset;
- semántica de día operativo;
- selección del origen de horario;
- semántica del flag manual de `plannedDraft`;
- segmentos de trabajo y sus timestamps;
- horas netas y descansos internos derivados;
- horas contractuales aplicables con la misma resolución vigente;
- ausencias aceptadas, tipo y estado;
- reglas con sus operadores exactos y configuración;
- continuidad entre días, meses y ficheros;
- cobertura de semanas y estados semanales;
- agregados mensuales y fines de semana;
- datasets entregados a Streamlit/HTML/Excel.

## Flujo funcional de referencia

```text
FUENTE ACTUAL
  JSON storeDayTimes
        |
        v
schedule_sources.py
  selecciona/filtra origen
        |
        v
extraction.py + dates.py
  ShiftRow / AbsenceDay / employee_months /
  employee_presence_dates / data_dates
        |
        v
rules/ + summary.py + weekly_hours.py
  incidencias / resumen mensual / control semanal
        |
        v
dataframes.py + excel.py
        |
        +--> Streamlit compuesto dinámicamente
        |
        +--> Excel

HTML autónomo
  mantiene una implementación JavaScript equivalente en payloads propios;
  la paridad debe comprobarse explícitamente.
```

La frontera recomendada para una futura fuente es:

```text
NUEVA FUENTE -> ADAPTADOR -> MODELO CANÓNICO -> MOTOR EXISTENTE
```

No se ha realizado ese refactor en esta fase. Esta documentación describe primero lo que el repositorio hace hoy y separa cualquier propuesta futura.