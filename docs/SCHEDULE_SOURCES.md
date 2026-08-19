# Orígenes de horarios

## 1. Fuentes funcionales reconocidas

La fuente de verdad es `workforce_validator/schedule_sources.py`.

```python
SCHEDULE_SOURCES = {
    "planned": "Plan publicado",
    "plannedDraft": "Borrador del planificador",
}
```

Solo existen **dos orígenes funcionales de horario** para el motor Python:

| Clave | Significado |
|---|---|
| `planned` | Plan publicado. |
| `plannedDraft` | Borrador generado por el planificador. |

`plannedDraftManuallyEdited` **no es un tercer horario**. Es un flag booleano asociado al persona-día y se usa exclusivamente para filtrar `plannedDraft`.

Tests relacionados: `tests/test_schedule_sources.py`, `tests/test_config_and_sources.py`, `tests/test_source_detection_cache.py`.

## 2. Detección de fuentes

`detect_schedule_sources(data)` recorre:

```text
storeDayTimes[] -> people[] -> dayTimes
```

Para cada clave de `SCHEDULE_SOURCES` calcula:

- `person_days`: persona-días cuyo campo existe como lista no vacía;
- `segments`: número total de elementos de esas listas;
- `work_segments`: elementos donde `hourType`, convertido a mayúsculas, es exactamente `WORK`;
- `date_count`;
- `first_date`;
- `last_date`.

Las fechas solo se incorporan a las estadísticas de una fuente cuando en ese persona-día existe al menos un segmento WORK.

### Consecuencia importante

Una fuente puede estar estructuralmente presente y contener segmentos, pero tener `work_segments == 0`. Detectar el campo no equivale a disponer de trabajo válido.

## 3. Qué cuenta como trabajo

El helper `_is_work(segment)` y `extraction.py` comparten la misma semántica:

```python
isinstance(segment, dict) and str(segment.get("hourType", "")).upper() == "WORK"
```

Por tanto:

- `WORK` cuenta;
- `work`, `Work`, etc. cuentan por la conversión a mayúsculas;
- cualquier otro `hourType` se ignora para construir turnos;
- ausencia de `hourType` se ignora;
- un elemento no dict se ignora.

Una nueva fuente debe proporcionar una clasificación equivalente: el adaptador debe decidir qué intervalos representan **trabajo efectivo planificado** y producir únicamente esos intervalos para el modelo canónico.

## 4. Filtro de edición manual del borrador

Filtros válidos:

```python
MANUAL_EDIT_FILTERS = {
    "all": "Todos los borradores",
    "edited": "Solo borradores editados manualmente",
    "not_edited": "Solo borradores no editados manualmente",
}
```

La función `_matches(day_times, manual_filter)` utiliza identidad booleana estricta:

| Filtro | Condición exacta |
|---|---|
| `all` | Siempre coincide. |
| `edited` | `plannedDraftManuallyEdited is True`. |
| `not_edited` | `plannedDraftManuallyEdited is False`. |

### Flag ausente

Si `plannedDraftManuallyEdited` falta o tiene cualquier valor distinto de los booleanos reales:

- entra en `all`;
- **no entra** en `edited`;
- **no entra** en `not_edited`.

`detect_schedule_sources()` contabiliza estos casos como `missing_person_days`.

## 5. Cómo se aplica el filtro

`filter_schedule_data(data, schedule_source, manual_filter)`:

1. valida la fuente;
2. valida el filtro;
3. si la fuente no es `plannedDraft`, fuerza el filtro efectivo a `all`;
4. crea una `deepcopy` de la entrada;
5. para `plannedDraft + edited/not_edited`, recorre cada persona-día;
6. cuando el flag no coincide, sustituye únicamente:

```python
day_times["plannedDraft"] = []
```

No elimina:

- el día operativo;
- la persona;
- sus horas contractuales;
- sus ausencias;
- su presencia en el dataset.

Esto es crucial. Un persona-día excluido del horario por filtro manual puede seguir contribuyendo a `employee_presence_dates`, `employee_months`, ausencias y cobertura del fichero.

## 6. Filtro manual con `planned`

Aunque el llamador solicite, por ejemplo:

```python
run_validation(data, "planned", "edited")
```

el resultado usa:

```text
manual_edit_filter = all
```

El flag manual nunca modifica el plan publicado. `tests/test_schedule_sources.py::test_manual_filter_is_ignored_for_published_plan` lo verifica.

## 7. Fuente solicitada sin segmentos WORK

Si la fuente seleccionada no contiene ningún segmento WORK válido:

- `extract_data()` no crea `ShiftRow` para esos persona-días;
- el empleado puede seguir apareciendo en `employee_months` y `employee_presence_dates`;
- las ausencias aceptadas se siguen extrayendo;
- `data_dates` sigue proveniendo de todos los `operatingDate` del fichero;
- el análisis semanal puede generar filas con `horas_planificadas = 0` si existe contrato y cobertura temporal.

No existe fallback automático de `plannedDraft` a `planned` ni viceversa.

## 8. Semántica que debe ofrecer una nueva fuente

Una nueva fuente no necesita tener campos con estos nombres, pero el adaptador debe poder responder sin ambigüedad:

1. ¿Qué versión del horario representa el **plan publicado**?
2. ¿Qué versión representa el **borrador del planificador**?
3. Para cada empleado y día del borrador, ¿está marcado como **editado manualmente**, **no editado manualmente** o **desconocido/no informado**?
4. ¿Qué intervalos de cada versión son trabajo (`WORK`) y cuáles no?
5. ¿Qué fechas están cubiertas por la fuente aunque no haya trabajo?

Contrato semántico recomendado:

```text
schedule_source ∈ {planned, plannedDraft}
manual_edit_state ∈ {true, false, missing}
work_segments = intervalos de trabajo válidos del origen seleccionado
```

No colapsar `missing` con `false`: el comportamiento actual los distingue cuando el usuario selecciona `not_edited`.

## 9. Casos de equivalencia mínimos

| Caso | Resultado actual que debe preservarse |
|---|---|
| `planned` con WORK | Se extraen esos segmentos. |
| `plannedDraft` con WORK | Se extraen esos segmentos. |
| Draft `True` + `edited` | Incluido. |
| Draft `False` + `edited` | Excluido del horario. |
| Flag ausente + `edited` | Excluido del horario. |
| Draft `False` + `not_edited` | Incluido. |
| Draft `True` + `not_edited` | Excluido. |
| Flag ausente + `not_edited` | Excluido. |
| Cualquier flag + `all` | Incluido si hay WORK. |
| Filtro manual solicitado con `planned` | Ignorado; filtro efectivo `all`. |
| Segmentos sin WORK | No generan turno. |
| Fuente inválida `plannedDraftManuallyEdited` | `ValueError`. |

## 10. COMPORTAMIENTO OBSERVADO / DUDA / RECOMENDACIÓN

### COMPORTAMIENTO OBSERVADO

El filtrado manual se implementa alterando una copia del JSON y vaciando `plannedDraft`; la información contextual del persona-día permanece.

### DUDA FUNCIONAL

El código no demuestra si un flag ausente significa funcionalmente “no editado”, “desconocido” o una versión antigua de la fuente. Operativamente se trata como una tercera condición distinta de `False`.

### RECOMENDACIÓN

El adaptador futuro debería modelar el estado manual como trivalente (`true`, `false`, `missing/unknown`) para reproducir exactamente los filtros actuales.