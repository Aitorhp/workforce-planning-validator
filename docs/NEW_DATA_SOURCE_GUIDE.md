# Guía para integrar una nueva fuente de datos

## 1. Objetivo

La integración correcta debe seguir este principio:

```text
NUEVA FUENTE -> ADAPTADOR -> MODELO CANÓNICO -> MOTOR EXISTENTE
```

El objetivo no es recrear artificialmente el JSON actual, sino producir la misma semántica que hoy extraen `schedule_sources.py`, `extraction.py` y `dates.py`.

## 2. Frontera conceptual `SourceAdapter`

Una interfaz conceptual suficiente sería:

```python
class SourceAdapter:
    def detect_schedule_sources(self) -> ScheduleSourceCapabilities: ...
    def build_canonical_dataset(
        self,
        schedule_source: str,
        manual_edit_filter: str = "all",
    ) -> CanonicalDataset: ...
```

No es una propuesta de API definitiva; representa las responsabilidades que deben separarse.

## 3. Salida requerida del adaptador

Debe proporcionar como mínimo:

```text
CanonicalDataset
├── shifts[]
├── absences[]
├── employee_months
├── employee_presence_dates
├── data_dates
├── schedule_source
└── manual_edit_filter efectivo
```

Ver [CANONICAL_DATA_MODEL.md](CANONICAL_DATA_MODEL.md).

## 4. Responsabilidades del adaptador

### 4.1 Lectura de la fuente

Puede provenir de:

- JSON distinto;
- varios JSON;
- API;
- base de datos;
- CSV/Excel;
- otro modelo estructurado.

La lectura específica no debe escapar hacia reglas o dashboards.

### 4.2 Identidad

Debe mapear:

```text
external_store -> store_id
external_employee -> person_id
```

Los identificadores deben ser estables durante todo el periodo.

### 4.3 Cobertura temporal

Debe producir `data_dates` como conjunto de fechas realmente cubiertas por el origen, **incluidos días sin turnos**.

No derivar `data_dates` únicamente de turnos.

### 4.4 Presencia del empleado

Debe distinguir:

```text
empleado aparece en la fuente ese día
vs
empleado tiene turno ese día
```

La primera condición alimenta `employee_presence_dates`.

### 4.5 Fuentes de horario

Debe mapear semánticamente:

```text
plan publicado -> planned
borrador -> plannedDraft
```

Si la nueva fuente no ofrece ambas versiones, debe declarar únicamente las capacidades existentes; no inventar un fallback.

### 4.6 Edición manual

Para borradores debe preservar estado trivalente:

```text
True / False / missing
```

No convertir `missing` en `False` si se pretende equivalencia exacta.

### 4.7 Segmentos de trabajo

Debe decidir qué registros equivalen a `hourType == WORK` y excluir otros tipos antes de formar turnos.

### 4.8 Construcción de turno

Debe reproducir exactamente:

```text
shift_start = min(inicios de segmentos ordenados)
shift_end = max(fines)
worked_hours = sum(duración de cada segmento)
break_hours = suma de gaps positivos <= max_internal_break_hours
```

Debe mantener la validación `end > start` y el redondeo vigente.

### 4.9 Contrato

Debe proporcionar `applicableWorkingHours` con granularidad suficiente para reconstruir:

- valor del persona-día en ShiftRow;
- último valor observado empleado-mes;
- resolución global actual de `weekly_hours.py`.

Aunque el nuevo origen tenga un modelo contractual más correcto/histórico, **no cambiar la fórmula efectiva durante la fase de equivalencia**.

### 4.10 Ausencias

Debe mapear estados equivalentes a los aceptados actuales (`VALIDATED`, `APPROVED`) o realizar una tabla explícita de equivalencia.

No asumir que cualquier ausencia externa debe entrar en el motor.

## 5. Qué debería poder mantenerse intacto

Si la salida canónica es equivalente, los siguientes módulos no deberían necesitar conocer la nueva fuente:

- `workforce_validator/rules/*`;
- `workforce_validator/summary.py`;
- `workforce_validator/weekly_hours.py`;
- helpers temporales de `workforce_validator/dates.py`;
- `workforce_validator/analytics.py`;
- `workforce_validator/dataframes.py`;
- `workforce_validator/excel.py`.

La orquestación `engine.py` podría necesitar una entrada canónica adicional o un wrapper, pero sus cálculos no deberían reescribirse.

## 6. Qué debe sustituirse o aislarse

| Responsabilidad actual | Módulo actual | Destino futuro |
|---|---|---|
| Parsear JSON | `io.py` | Adaptador específico |
| Detectar `planned`/`plannedDraft` | `schedule_sources.py` | Capabilities del adaptador |
| Filtrar edición manual | `schedule_sources.py` | Adaptador / normalización canónica |
| Navegar `storeDayTimes` | `extraction.py` | Adaptador |
| Extraer contrato | `extraction.py` | Adaptador |
| Extraer ausencias | `extraction.py` | Adaptador |
| Recoger `operatingDate` | `dates.collect_data_dates()` | Cobertura canónica |
| Combinar dos JSON mensuales | `multi_file.py` | Solo necesario para CurrentJsonAdapter |

## 7. Compatibilidad recomendada durante la migración

No sustituir de golpe el pipeline actual. Mantener dos rutas durante la validación:

```text
Ruta A — referencia
JSON actual -> pipeline actual -> resultados referencia

Ruta B — candidata
JSON actual -> CurrentJsonAdapter -> CanonicalDataset -> motor canónico
```

Primero demostrar A == B.

Después:

```text
Nueva fuente -> NewSourceAdapter -> CanonicalDataset -> mismo motor canónico
```

Comparar contra fixtures equivalentes.

## 8. Orden recomendado de implementación futura

1. Congelar Golden Masters del comportamiento actual.
2. Introducir tipos canónicos sin modificar fórmulas.
3. Crear `CurrentJsonAdapter` que reproduzca el comportamiento actual.
4. Ejecutar Golden Master actual vs adaptador actual.
5. Solo cuando sea idéntico, crear `NewSourceAdapter`.
6. Completar `DATA_SOURCE_MAPPING_TEMPLATE.md`.
7. Comparar nueva fuente contra casos equivalentes.
8. Verificar datasets de presentación.
9. Verificar HTML.
10. Solo después considerar refactors/deuda técnica.

## 9. Errores de diseño a evitar

No hacer durante la migración:

- cambiar contratos a resolución semanal “más correcta”;
- convertir timestamps a UTC si hoy no se hace;
- reinterpretar flag manual ausente como `False`;
- contar como cobertura solo días con turno;
- fusionar segmentos solapados si hoy se suman;
- imputar horas de ausencia como trabajo;
- cambiar semántica de fines de semana del motor o dashboard;
- deduplicar registros históricos sin demostrar que son duplicados funcionales;
- aprovechar el cambio de fuente para refactorizar la composición Streamlit.

Cada uno de esos cambios impediría saber si una diferencia procede del adaptador o de una nueva regla.

## 10. Contrato de aceptación

Una nueva fuente será aceptable cuando, para escenarios equivalentes:

```text
turnos normalizados iguales
AND incidencias iguales
AND resumen mensual igual
AND control semanal igual
AND ausencias/contexto iguales
AND fines de semana equivalentes por cada semántica
AND DataFrames de dashboard equivalentes
AND HTML funcionalmente equivalente
```

Las comparaciones exactas y normalizaciones permitidas se detallan en [TESTING_AND_GOLDEN_MASTER.md](TESTING_AND_GOLDEN_MASTER.md).

## 11. Dudas que deben resolverse con el propietario antes de una segunda fase

- ¿El contrato debe ser históricamente variable por semana/mes o conservar la resolución global actual?
- ¿Los offsets horarios de la nueva fuente deben tratarse como hora local descartando offset, exactamente como hoy?
- ¿Un sábado de un mes y domingo del siguiente debe contar funcionalmente como fin completo? La UI y el resumen motor difieren.
- ¿Qué significa funcionalmente `plannedDraftManuallyEdited` ausente?
- ¿La fuente garantiza que segmentos WORK nunca se solapan?
- ¿Las reglas configurables de fines de semana deben migrarse formalmente al motor o permanecer como análisis de UI?

Hasta resolverlas, el comportamiento observado actual es la referencia de equivalencia.