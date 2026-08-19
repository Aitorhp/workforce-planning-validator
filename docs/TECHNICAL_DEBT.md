# Deuda arquitectónica, legado y acoplamientos

Este documento separa deliberadamente **ESTADO ACTUAL** y **ARQUITECTURA RECOMENDADA**. Ninguna recomendación debe reinterpretarse como descripción del comportamiento vigente.

## 1. Composición dinámica de Streamlit

### ESTADO ACTUAL

La aplicación productiva se genera aplicando transformaciones textuales sucesivas sobre código Python:

```text
app.py
-> dashboard_patch.py
-> dashboard_patch_v2.py
-> dashboard_patch_v3.py
-> dashboard_extensions.py
-> multi_file_dashboard.py
-> contract_shift_dashboard.py
-> review_iteration_dashboard.py
-> weekend_assignment_integration.py
-> contract_hours_heatmap_dashboard.py
-> workforce_insights_dashboard.py
-> compile/exec
```

Los `dashboard_patch*.py` no son archivos muertos: participan en la construcción vigente.

### Riesgo

- orden de aplicación significativo;
- reemplazos basados en strings/patrones;
- una edición estructural de `app.py` puede hacer que un parche deje de encontrar su marcador;
- dificultad para identificar la fuente efectiva de un renderer;
- código final solo existe en runtime.

`tests/test_dashboard_final_pipeline.py` reduce el riesgo al compilar la fuente final y verificar renderizadores/marcadores.

### RECOMENDACIÓN

Consolidar posteriormente renderizadores en módulos explícitos/importables. No hacerlo durante la migración de fuente.

## 2. Duplicidad de lógica de fines de semana

### ESTADO ACTUAL

Existen al menos tres niveles de semántica:

1. `dates.py::weekend_counts()` para resumen mensual del motor;
2. `dashboard_extensions.py::prepare_weekend_analysis()` basado en cobertura real;
3. `weekend_assignment_dashboard.py` para reglas interactivas y asignación sin reutilizar días.

Además existe una réplica JavaScript en HTML.

### Riesgo

- una frontera mensual sábado/domingo se comporta distinto entre motor y dashboard;
- días no cubiertos pueden parecer libres en el resumen mensual del motor;
- modificar una implementación sin otra rompe paridad.

### RECOMENDACIÓN

Después del Golden Master, definir formalmente qué semánticas deben coexistir y extraerlas a un servicio común o contratos de cálculo explícitos.

## 3. Lógica funcional en capa de presentación

### ESTADO ACTUAL

`weekend_assignment_dashboard.py` contiene reglas configurables que determinan cumplimiento/incumplimiento de descansos. `contract_shift_dashboard.py` recalcula analytics de franjas. `review_iteration_dashboard.py` cambia el scope visible de semanas.

### Riesgo

Un consumidor que use solo `workforce_validator` no obtiene necesariamente toda la experiencia funcional que ve el usuario.

### RECOMENDACIÓN

Distinguir formalmente:

```text
business engine
presentation analytics
presentation-only formatting
```

y mover únicamente los cálculos que deban ser contrato de negocio.

## 4. Contrato semanal reducido globalmente

### ESTADO ACTUAL

`weekly_hours.py` termina usando un único `applicableWorkingHours` por empleado para todas las semanas, normalmente el último valor no vacío disponible tras recorrer turnos.

La UI añade una alerta cuando el contrato cambia entre meses, pero no modifica el cálculo.

### Riesgo

- cargar un segundo mes puede alterar evaluación de semanas anteriores;
- una nueva fuente con contratos efectivos por fecha puede producir resultados distintos si se utiliza esa granularidad “correctamente”.

### DUDA FUNCIONAL

Confirmar intención antes de cualquier corrección.

### RECOMENDACIÓN

Congelar el comportamiento actual en Golden Master; después decidir si el contrato debe versionarse temporalmente.

## 5. Timezone descartado

### ESTADO ACTUAL

`parse_iso_datetime()` elimina `tzinfo` mediante `.replace(tzinfo=None)` sin convertir el instante.

### Riesgo

Fuentes con offsets heterogéneos pueden alterar la interpretación absoluta de descansos.

### RECOMENDACIÓN

No cambiar durante equivalencia. Posteriormente definir una política explícita de zona horaria con migración/test específico.

## 6. Solapamiento de segmentos WORK

### ESTADO ACTUAL

`worked_hours` suma la duración de cada segmento. No fusiona intervalos solapados.

### Riesgo

Si la fuente permite solapes, las horas pueden duplicarse.

### DUDA FUNCIONAL

Confirmar si el contrato de origen garantiza segmentos no solapados.

## 7. Cobertura mensual de fines de semana

### ESTADO ACTUAL

`summary.py` usa calendario completo del mes y `worked_days`, no `data_dates`.

### Riesgo

En datasets parciales puede contar como libre un sábado/domingo nunca presente en la fuente.

La UI actual mitiga esto usando cobertura real, creando divergencia entre superficies/datasets.

## 8. Nombres de columnas con límites embebidos

### ESTADO ACTUAL

Columnas como:

```text
cumple_max_5_dias
turnos_superiores_7_5h
turnos_inferiores_4h
descansos_inferiores_11h
```

incluyen los valores actuales en el nombre aunque los límites sean configurables en `config/rules.json`.

### Riesgo

Cambiar configuración puede dejar nombres engañosos sin cambiar lógica.

### RECOMENDACIÓN

En una versión futura, usar nombres semánticos independientes del límite y exponer el límite como metadato.

## 9. Duplicados de `storeDayTimes`

### ESTADO ACTUAL

`multi_file.py` rechaza fechas solapadas **entre documentos**, pero no detecta duplicados de fecha dentro del mismo documento.

### Riesgo

- cobertura usa set y parece única;
- extracción puede procesar dos veces el mismo día;
- horas/turnos pueden duplicarse.

### RECOMENDACIÓN

Añadir validación de integridad en el adaptador futuro después de congelar el caso actual.

## 10. Fachadas de compatibilidad

### ESTADO ACTUAL

Existen `validator_engine.py` y `schedule_adapter.py`. La app productiva hace monkey-patch de `sys.modules["validator_engine"]` para que imports históricos consuman `schedule_adapter`.

### Riesgo

La API que parece importada por `app.py` no es necesariamente la implementación ejecutada.

### RECOMENDACIÓN

Mantener la fachada durante la migración; simplificar solo después de estabilizar imports directos.

## 11. HTML como segunda implementación

### ESTADO ACTUAL

El HTML contiene una implementación JavaScript propia de cálculos y presentación empaquetada en payloads, además de parches Python que transforman el HTML/JS.

### Riesgo

Paridad basada en disciplina y tests, no en compartir motor.

### RECOMENDACIÓN

Añadir Golden Master numérico Python↔JS antes de modificar la fuente de datos de ambas superficies.

## 12. Matriz de acoplamiento a la fuente actual

| Fichero | Función/área | Campo de origen | Clasificación | Impacto al cambiar fuente |
|---|---|---|---|---|
| `workforce_validator/io.py` | `load_json_bytes` | raíz JSON | ingestión | alto si deja de ser JSON |
| `workforce_validator/schedule_sources.py` | detección/filtro | `storeDayTimes`, `people`, `dayTimes`, planned/draft/flag | ingestión | alto |
| `workforce_validator/extraction.py` | `extract_data` | store/person/contract/schedules/absences | ingestión | **muy alto** |
| `workforce_validator/dates.py` | `collect_data_dates` | `operatingDate` | ingestión temporal | alto |
| `workforce_validator/multi_file.py` | combinación | `store.id`, `storeDayTimes` | compatibilidad | alto solo para multi-JSON |
| `app.py`/parches | selección de fuente/labels | nombres de fuentes expuestos por API | presentación/compatibilidad | medio |
| tests de sources/regression | fixtures | JSON actual | test | deben mantenerse como referencia |
| HTML/JS de referencia | parser interno | estructura actual de entrada | implementación paralela | muy alto para paridad HTML |

Los módulos `rules/`, `summary.py` y `weekly_hours.py` no navegan directamente por `storeDayTimes`; consumen estructuras extraídas. Es la principal oportunidad de desacoplamiento.

## 13. Código histórico y artefactos

### `script_original_referencia.py`

Referencia histórica de gran tamaño. No forma parte del flujo modular productivo identificado.

### `dashboard_patch*.py`

Aunque tengan carácter histórico, **sí siguen activos**. No eliminarlos por considerarlos legado.

### `validador_distribuible.html`

Artefacto generado. Debe regenerarse, no editarse manualmente.

### `__pycache__/*.pyc`

Artefactos de ejecución versionados en el árbol. No son fuente funcional y pueden introducir ruido al inspeccionar el repositorio.

## 14. Prioridades recomendadas después de la documentación

Orden seguro:

1. Golden Master del estado actual.
2. Modelo canónico explícito.
3. `CurrentJsonAdapter` con resultados idénticos.
4. `NewSourceAdapter`.
5. Paridad HTML.
6. Solo después: resolver contrato temporal, timezone, weekends, solapes y consolidación de UI.

## 15. Principio de control de cambios

No combinar en una misma iteración:

```text
cambio de fuente + cambio de fórmula
cambio de fuente + cambio temporal
cambio de fuente + refactor de dashboard
cambio de fuente + reinterpretación de ausencia
```

Cada uno debe poder validarse aisladamente contra una referencia conocida.